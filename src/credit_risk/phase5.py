"""Frozen final evaluation: preflight, one exposure, evidence-only reporting and delivery."""
import argparse
import csv
from datetime import datetime, timezone
import importlib.metadata
import json
import shutil
from pathlib import Path
import time
import uuid

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score, log_loss, brier_score_loss
from threadpoolctl import threadpool_limits

from credit_risk.artifacts import file_sha256, write_json
from credit_risk.features import PREDICTORS, feature_contract
from credit_risk.models.bundle import verify_freeze, load_frozen_bundle
from credit_risk.models.inputs import verify_assignments, _selected_csv
from credit_risk.models.pipelines import positive_probability
from credit_risk.decisioning.policy import Scenario, FrozenPolicy, evaluate_policy
from credit_risk.splits.allocation import financial_fingerprint

RUN = '9ca62eca2665438c9c97b4889413acfa'
FREEZE = '89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b'
BUNDLE = '45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd'
MANIFEST = Path('artifacts/models/phase4') / RUN / 'freeze_manifest.json'
METRICS = ('average_precision', 'roc_auc', 'log_loss', 'brier_score')
POLICY_METRICS = ('benchmark_utility_per_customer', 'acceptance_rate', 'accepted_default_rate')


def utc():
    return datetime.now(timezone.utc).isoformat()


def code_hashes(root):
    return {str(p.relative_to(root)): file_sha256(p)
            for folder in ('src', 'tests') for p in sorted((root / folder).rglob('*.py'))}


def preflight(root):
    root = Path(root)
    path = root / MANIFEST
    m = verify_freeze(path)
    if json.loads(path.read_text())['freeze_sha256'] != FREEZE or m['run_id'] != RUN:
        raise ValueError('Unexpected accepted freeze identity')
    if file_sha256(path.parent / 'probability_bundle.joblib') != BUNDLE:
        raise ValueError('Unexpected bundle identity')
    project_review = json.loads((root / 'reports/phase4_review_receipt.json').read_text())
    if project_review != json.loads((path.parent / 'review.json').read_text()):
        raise ValueError('Project and frozen review receipt differ')
    for relative, digest in m['integrity']['input_hashes'].items():
        if file_sha256(root / relative) != digest:
            raise ValueError(f'Accepted input changed: {relative}')
    if json.loads((path.parent / 'feature_schema.json').read_text()) != feature_contract():
        raise ValueError('Feature contract changed')
    # Preserve the exact pipeline/formula/loading source; new Phase 5 modules are additive.
    for p in (path.parent / 'completion_source/src').rglob('*.py'):
        relative = p.relative_to(path.parent / 'completion_source')
        if file_sha256(root / relative) != file_sha256(p):
            raise ValueError(f'Accepted source changed: {relative}')
    lock = path.parent / 'completion_source/requirements.lock'
    for line in lock.read_text().splitlines():
        if '==' in line and not line.startswith('#'):
            name, version = line.strip().split('==')
            if importlib.metadata.version(name) != version:
                raise ValueError(f'Accepted dependency changed: {name}')
    with (root / 'artifacts/split_manifest.csv').open(newline='') as stream:
        assignments = list(csv.DictReader(stream))
    export = json.loads((root / 'artifacts/phase1_export_manifest.json').read_text())
    verify_assignments(assignments, export['source_sha256'])
    sizes = {name: sum(x['partition'] == name for x in assignments)
             for name in m['integrity']['partition_sizes']}
    if sizes != m['integrity']['partition_sizes']:
        raise ValueError('Partition sizes changed')
    bundle = load_frozen_bundle(path)
    policy = json.loads((path.parent / 'policy.json').read_text())
    if (bundle.mapping != 'raw' or bundle.probability_estimator is not bundle.base
            or bundle.policy != policy or bundle.feature_schema != feature_contract()
            or bundle.model_metadata['integrity'] != m['integrity']):
        raise ValueError('Loaded bundle contract differs')
    for candidate, digest in m['integrity']['model_sha256'].items():
        if file_sha256(path.parent / f'accepted_models/{candidate}/development_pipeline.joblib') != digest:
            raise ValueError('Reference identity changed')
    definitions = json.loads((path.parent / 'report_definitions.json').read_text())
    if definitions['uncertainty']['seed'] != 42 or definitions['uncertainty']['repetitions'] != 1000:
        raise ValueError('Reporting plan changed')
    return bundle, assignments, {'utc': utc(), 'freeze_sha256': FREEZE, 'bundle_sha256': BUNDLE,
            'run_id': RUN, 'artifact_count': len(m['artifacts']), 'integrity': m['integrity'],
            'report_definitions': definitions, 'code_hashes': code_hashes(root),
            'lock_sha256': file_sha256(root / 'requirements.lock'),
            'test_outcomes_accessed': False}


def partition(root, assignments, name):
    root = Path(root)
    selected = [r for r in assignments if r['partition'] == name]
    ids = {int(r['client_id']) for r in selected}
    def features(row):
        return {k: float(row[k]) if row[k] else None for k in PREDICTORS}
    def outcome(row):
        if row['default_next_month'] not in {'0', '1'}:
            raise ValueError('Invalid binary outcome')
        return int(row['default_next_month'])
    values, feature_ids = _selected_csv(root / 'data/processed/financial_features_v1.csv',
                                      ('client_id', *PREDICTORS), ids, features)
    # Verify row features before interpreting labels.
    for r in selected:
        if financial_fingerprint(values[int(r['client_id'])]) != r['fingerprint']:
            raise ValueError('Fingerprint changed')
    labels, label_ids = _selected_csv(root / 'data/processed/labels.csv',
                                     ('client_id', 'default_next_month'), ids, outcome)
    if feature_ids != label_ids or feature_ids != {int(r['client_id']) for r in assignments}:
        raise ValueError('ID reconciliation failed')
    return pd.DataFrame([{'client_id': int(r['client_id']), 'fingerprint': r['fingerprint'],
                          'default_next_month': labels[int(r['client_id'])],
                          **values[int(r['client_id'])]} for r in selected]).sort_values(
                              'client_id').reset_index(drop=True)


def metrics(y, p):
    y, p = np.asarray(y), np.asarray(p, dtype=float)
    if (not len(y) or p.shape != y.shape or not np.isin(y, [0, 1]).all()
            or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any()):
        raise ValueError('Invalid evaluation vectors')
    two = len(np.unique(y)) == 2
    return {'average_precision': float(average_precision_score(y, p)) if two else None,
            'roc_auc': float(roc_auc_score(y, p)) if two else None,
            'log_loss': float(log_loss(y, np.column_stack((1-p, p)), labels=[0, 1])),
            'brier_score': float(brier_score_loss(y, p, pos_label=1))}


def scenarios(policy):
    return [{'scenario': Scenario().to_dict(), 'policies': policy['base_policies']},
            *policy['sensitivity']['scenarios']]


def group_resamples(groups, repetitions=1000, seed=42):
    groups = np.asarray(groups)
    if groups.ndim != 1 or not len(groups):
        raise ValueError('Nonempty group vector required')
    unique, inverse = np.unique(groups, return_inverse=True)
    members = [np.flatnonzero(inverse == k) for k in range(len(unique))]
    rng = np.random.default_rng(seed)
    for _ in range(repetitions):
        sampled = rng.integers(0, len(unique), len(unique))
        yield np.concatenate([members[k] for k in sampled])


def interval(values, estimate):
    valid = [float(x) for x in values if x is not None and np.isfinite(x)]
    bounds = np.percentile(valid, [2.5, 97.5]).tolist() if valid else [None, None]
    return {'estimate': estimate, 'lower': bounds[0], 'upper': bounds[1],
            'valid_repetitions': len(valid), 'undefined_repetitions': len(values)-len(valid)}


def summarize(frame, policy, repetitions=1000, seed=42):
    y = frame.default_next_month.to_numpy(dtype=int)
    predictions = {c: frame[c].to_numpy(dtype=float) for c in frame.columns
                   if c not in {'client_id', 'fingerprint', 'default_next_month'}}
    model_values = {name: metrics(y, p) for name, p in predictions.items()}
    specs, policy_values = {}, {}
    for cell in scenarios(policy):
        scenario = Scenario.from_dict(cell['scenario'])
        for definition in cell['policies']:
            definition = FrozenPolicy.from_dict(definition)
            key = scenario.scenario_id + '/' + definition.policy_id
            specs[key] = (scenario, definition)
            policy_values[key] = evaluate_policy(predictions['selected_bundle'], y, definition, scenario)
    samples = {f'model/{name}/{metric}': [] for name in predictions for metric in METRICS}
    samples.update({f'policy/{key}/{metric}': [] for key in specs for metric in POLICY_METRICS})
    model_pairs = {f'model_difference/selected_bundle-minus-{name}/{metric}': []
                   for name in predictions if name != 'selected_bundle' for metric in METRICS}
    policy_pairs = {}
    for cell in scenarios(policy):
        sid = cell['scenario']['scenario_id']
        for reference in ('analytic', 'accept_all', 'abstain_all'):
            policy_pairs[f'policy_difference/{sid}/empirical-minus-{reference}'] = []
    plan_hash = __import__('hashlib').sha256()
    for indices in group_resamples(frame.fingerprint, repetitions, seed):
        plan_hash.update(np.asarray(indices, dtype='<i8').tobytes())
        yy = y[indices]
        values = {name: metrics(yy, p[indices]) for name, p in predictions.items()}
        for name, row in values.items():
            for metric in METRICS:
                samples[f'model/{name}/{metric}'].append(row[metric])
        for name in predictions:
            if name == 'selected_bundle':
                continue
            for metric in METRICS:
                a, b = values['selected_bundle'][metric], values[name][metric]
                model_pairs[f'model_difference/selected_bundle-minus-{name}/{metric}'].append(
                    a-b if a is not None and b is not None else None)
        # Count-based policy arithmetic; same resamples as probability comparisons.
        outcomes = {}
        for key, (scenario, definition) in specs.items():
            accepted = definition.accept(predictions['selected_bundle'][indices])
            n = int(accepted.sum())
            defaults = int(yy[accepted].sum())
            u = ((n-defaults)*scenario.gain-defaults*scenario.loss-n*scenario.cost)/len(indices)
            row = {'benchmark_utility_per_customer': u, 'acceptance_rate': n/len(indices),
                   'accepted_default_rate': defaults/n if n else None}
            outcomes[key] = u
            for metric in POLICY_METRICS:
                samples[f'policy/{key}/{metric}'].append(row[metric])
        for key in policy_pairs:
            _, sid, contrast = key.split('/')
            ref = contrast.removeprefix('empirical-minus-')
            policy_pairs[key].append(outcomes[sid+'/empirical']-outcomes[sid+'/'+ref])
    estimates = {f'model/{name}/{metric}': row[metric] for name,row in model_values.items()
                 for metric in METRICS}
    estimates.update({f'policy/{key}/{metric}': row[metric] for key,row in policy_values.items()
                      for metric in POLICY_METRICS})
    for name in predictions:
        if name != 'selected_bundle':
            for metric in METRICS:
                a, b = model_values['selected_bundle'][metric], model_values[name][metric]
                estimates[f'model_difference/selected_bundle-minus-{name}/{metric}'] = (
                    a-b if a is not None and b is not None else None)
    for key in policy_pairs:
        _,sid,contrast = key.split('/')
        ref = contrast.removeprefix('empirical-minus-')
        estimates[key] = (policy_values[sid+'/empirical']['benchmark_utility_per_customer']
                          - policy_values[sid+'/'+ref]['benchmark_utility_per_customer'])
    all_samples = samples | model_pairs | policy_pairs
    return {'model_metrics': model_values, 'policy_metrics': list(policy_values.values()),
            'intervals': {k: interval(v, estimates[k]) for k,v in all_samples.items()},
            'bootstrap': {'repetitions': repetitions, 'seed': seed, 'unit': 'fingerprint group',
                          'paired': True, 'interval': '95% percentile',
                          'resample_indices_sha256': plan_hash.hexdigest(),
                          'groups': int(frame.fingerprint.nunique()),
                          'one_class': 'AP/ROC-AUC undefined; log loss/Brier remain defined',
                          'empty_acceptance': 'accepted default rate null (N/A)',
                          'conditioning': 'fixed fitted models/policies; sample uncertainty only'}}


def evaluate(root, readiness):
    root = Path(root)
    bundle, assignments, evidence = preflight(root)
    receipt = json.loads(Path(readiness).read_text())
    if (receipt.get('disposition') != 'PASS' or receipt.get('code_hashes') != evidence['code_hashes']
            or receipt.get('freeze_sha256') != FREEZE or not receipt.get('fixture_checks_passed')):
        raise ValueError('Missing/stale Phase 5 reviewed fixture readiness receipt')
    # One durable run; no routine rerun. Failed runs remain preserved.
    output = root / 'artifacts/runtime/phase5' / 'final_evaluation'
    output.mkdir(parents=True, exist_ok=False)
    exposure = {'utc': utc(), 'evaluation_run_id': uuid.uuid4().hex, 'status': 'STARTED',
                'purpose': 'authorized frozen final evaluation', **evidence,
                'readiness_sha256': file_sha256(readiness), 'partition': 'final_test'}
    # Durable review/code/test snapshot precedes any label decoding.
    shutil.copy2(readiness, output / 'readiness.json')
    snapshot = {}
    for folder in ('src', 'tests'):
        for source in sorted((root / folder).rglob('*.py')):
            relative = source.relative_to(root)
            target = output / 'source' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            snapshot[str(relative)] = file_sha256(target)
    shutil.copy2(root / 'requirements.lock', output / 'source/requirements.lock')
    exposure['snapshot_hashes'] = snapshot
    exposure['snapshot_lock_sha256'] = file_sha256(output / 'source/requirements.lock')
    write_json(output / 'exposure.json', exposure, frozen=True)
    with (root / 'docs/test-exposure-log.md').open('a') as stream:
        stream.write('\n### Phase 5 frozen final-test access '+exposure['utc']+'\n\n'
                     + 'Run `'+exposure['evaluation_run_id']+'`; freeze `'+FREEZE+'`. '
                     'Readiness PASS. Outcomes will be read once for frozen evaluation; '
                     'subsequent reporting uses saved evidence. Receipt: '
                     '`artifacts/runtime/phase5/final_evaluation/exposure.json`.\n')
    try:
        started = time.perf_counter()
        frame = partition(root, assignments, 'final_test')
        saved = frame[['client_id', 'fingerprint', 'default_next_month']].copy()
        X = frame[list(PREDICTORS)]
        with threadpool_limits(limits=1):
            for name, estimator in bundle.references.items():
                saved[name] = positive_probability(estimator, X)
            saved['selected_bundle'] = bundle.predict_probability(X)
        if not np.array_equal(saved['selected_bundle'], saved['xgboost_05_engineered_none']):
            raise ValueError('Identity mapping/reference probabilities disagree')
        saved.to_csv(output / 'predictions.csv', index=False, float_format='%.17g')
        decisions = []
        for cell in scenarios(bundle.policy):
            scenario = Scenario.from_dict(cell['scenario'])
            for definition in cell['policies']:
                policy = FrozenPolicy.from_dict(definition)
                accept = policy.accept(saved.selected_bundle)
                decisions.append(pd.DataFrame({'client_id': saved.client_id,
                                                'scenario_id': scenario.scenario_id,
                                                'policy_id': policy.policy_id, 'accepted': accept}))
        pd.concat(decisions).to_csv(output / 'decisions.csv', index=False)
        exposure.update({'status': 'COMPLETE', 'test_outcomes_accessed': True,
                         'exposure_sha256': file_sha256(output / 'exposure.json'), 'rows': len(frame),
                         'predictions_sha256': file_sha256(output / 'predictions.csv'),
                         'decisions_sha256': file_sha256(output / 'decisions.csv'),
                         'scoring_seconds': time.perf_counter()-started})
        write_json(output / 'completion.json', exposure, frozen=True)
        return exposure
    except Exception as exc:
        failure = {'utc': utc(), 'status': 'FAILED', 'outcome_access_attempted': True,
                   'error_type': type(exc).__name__, 'error': str(exc),
                   'evaluation_run_id': exposure['evaluation_run_id']}
        write_json(output / 'failure.json', failure, frozen=True)
        with (root / 'docs/test-exposure-log.md').open('a') as stream:
            stream.write('\nFrozen evaluation attempt FAILED; original evidence preserved. '
                         'See `artifacts/runtime/phase5/final_evaluation/failure.json`. '
                         'Outcome access was attempted; no reselection is permitted.\n')
        raise


def validate_saved(frame, decisions, assignments, policy):
    expected = sorted((int(r['client_id']), r['fingerprint']) for r in assignments
                      if r['partition'] == 'final_test')
    model_names = {'dummy_prior', 'logistic_00_engineered_none',
                   'random_forest_02_engineered_none', 'xgboost_04_engineered_none',
                   'xgboost_05_engineered_none', 'selected_bundle'}
    if (set(frame.columns) != {'client_id', 'fingerprint', 'default_next_month', *model_names}
            or not frame.client_id.is_unique
            or list(zip(frame.client_id, frame.fingerprint)) != expected):
        raise ValueError('Saved evaluation IDs/fingerprints/model columns differ from freeze')
    if not np.array_equal(frame.selected_bundle, frame.xgboost_05_engineered_none):
        raise ValueError('Saved raw/selected probabilities differ')
    for name in model_names:
        metrics(frame.default_next_month, frame[name])
    if set(decisions.columns) != {'client_id', 'scenario_id', 'policy_id', 'accepted'}:
        raise ValueError('Saved decision schema differs')
    expected_cells = set()
    for cell in scenarios(policy):
        sid = cell['scenario']['scenario_id']
        for definition in cell['policies']:
            definition = FrozenPolicy.from_dict(definition)
            expected_cells.add((sid, definition.policy_id))
            rows = decisions[(decisions.scenario_id == sid)
                             & (decisions.policy_id == definition.policy_id)]
            if (rows.client_id.tolist() != frame.client_id.tolist()
                    or not np.array_equal(rows.accepted.to_numpy(),
                                          definition.accept(frame.selected_bundle))):
                raise ValueError('Saved decisions differ from frozen masks/coverage')
    if set(zip(decisions.scenario_id, decisions.policy_id)) != expected_cells:
        raise ValueError('Unexpected saved decision cells')


def report(root):
    root = Path(root)
    bundle, assignments, evidence = preflight(root)
    runtime = root / 'artifacts/runtime/phase5/final_evaluation'
    receipt = json.loads((runtime / 'completion.json').read_text())
    if receipt['freeze_sha256'] != FREEZE or receipt['status'] != 'COMPLETE':
        raise ValueError('Invalid evaluation receipt')
    exposure = json.loads((runtime / 'exposure.json').read_text())
    readiness = json.loads((runtime / 'readiness.json').read_text())
    if (receipt['code_hashes'] != evidence['code_hashes']
            or readiness['code_hashes'] != evidence['code_hashes']
            or receipt['exposure_sha256'] != file_sha256(runtime / 'exposure.json')
            or receipt['readiness_sha256'] != file_sha256(runtime / 'readiness.json')
            or receipt['evaluation_run_id'] != exposure['evaluation_run_id']
            or readiness.get('disposition') != 'PASS'):
        raise ValueError('Reporting source/review/exposure differs from reviewed execution')
    for relative, digest in receipt['snapshot_hashes'].items():
        if file_sha256(runtime / 'source' / relative) != digest:
            raise ValueError('Archived evaluation source/test changed')
    for name in ('predictions', 'decisions'):
        if file_sha256(runtime / (name+'.csv')) != receipt[name+'_sha256']:
            raise ValueError('Saved evaluation evidence changed')
    frame = pd.read_csv(runtime / 'predictions.csv', float_precision='round_trip')
    validate_saved(frame, pd.read_csv(runtime / 'decisions.csv'), assignments, bundle.policy)
    output = root / 'reports/phase5'
    output.mkdir(parents=True, exist_ok=False)
    summary = summarize(frame, bundle.policy)
    summary['provenance'] = {'evaluation_run_id': receipt['evaluation_run_id'],
                             'freeze_sha256': FREEZE, 'bundle_sha256': BUNDLE,
                             'predictions_sha256': receipt['predictions_sha256'],
                             'report_code_hashes': evidence['code_hashes']}
    write_json(output / 'results.json', summary, frozen=True)
    pd.DataFrame(summary['model_metrics']).T.rename_axis('candidate').to_csv(output/'models.csv')
    pd.DataFrame(summary['policy_metrics']).to_csv(output/'policies.csv',index=False)
    pd.DataFrame([{'statistic': k, **v} for k,v in summary['intervals'].items()]).to_csv(
        output/'intervals.csv',index=False)
    write_json(output / 'test_exposure_receipt.json', receipt, frozen=True)
    figures(frame, summary, bundle.policy, output)
    return summary['model_metrics']['selected_bundle']


def figures(frame, summary, policy, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.metrics import precision_recall_curve
    y = frame.default_next_month.to_numpy()
    fig, ax = plt.subplots()
    for name in summary['model_metrics']:
        if name == 'selected_bundle':
            continue
        precision, recall, _ = precision_recall_curve(y, frame[name])
        ax.plot(recall, precision, label=name)
    ax.set(xlabel='Recall (default)', ylabel='Precision', title='Frozen final-test candidates')
    ax.legend(fontsize=6)
    fig.savefig(output/'precision_recall.png',dpi=150,bbox_inches='tight')
    plt.close(fig)
    bins = []
    fig, ax = plt.subplots()
    for name in summary['model_metrics']:
        p = frame[name].to_numpy()
        row = []
        for index in range(10):
            take = (p >= index/10) & ((p < (index+1)/10) if index<9 else (p <= 1))
            n = int(take.sum())
            row.append({'candidate': name, 'lower': index/10, 'upper': (index+1)/10,
                        'count': n, 'mean_probability': float(p[take].mean()) if n else None,
                        'observed_rate': float(y[take].mean()) if n else None, 'sparse': n<100})
        bins.extend(row)
        if name == 'selected_bundle':
            nonempty = [r for r in row if r['count']]
            ax.plot([r['mean_probability'] for r in nonempty],
                    [r['observed_rate'] for r in nonempty], marker='o')
            for r in nonempty:
                ax.annotate(str(r['count'])+('*' if r['sparse'] else ''),
                            (r['mean_probability'],r['observed_rate']),fontsize=7)
    ax.plot([0,1],[0,1],linestyle='--')
    ax.set(xlabel='Mean predicted risk',ylabel='Observed default rate',
           title='Final-test selected bundle; bin counts (* n<100)')
    fig.savefig(output/'reliability.png',dpi=150,bbox_inches='tight')
    plt.close(fig)
    pd.DataFrame(bins).to_csv(output/'reliability_bins.csv',index=False)
    base = [r for r in summary['policy_metrics'] if r['scenario_id']=='base']
    empirical = next(r for r in base if r['policy_id']=='empirical')
    matrix = [[empirical['detection_true_negative'],empirical['detection_false_positive']],
              [empirical['detection_false_negative'],empirical['detection_true_positive']]]
    fig,ax=plt.subplots()
    ax.imshow(matrix,cmap='Blues')
    for i in range(2):
        for j in range(2):
            ax.text(j,i,str(matrix[i][j]),ha='center')
    ax.set(xticks=[0,1],xticklabels=['accept','abstain'],yticks=[0,1],
           yticklabels=['nondefault','default'],title='Frozen empirical cutoff 0.085; test')
    fig.savefig(output/'confusion.png',dpi=150,bbox_inches='tight')
    plt.close(fig)
    fig,ax=plt.subplots()
    ax.scatter([r['acceptance_rate'] for r in base],
               [r['benchmark_utility_per_customer'] for r in base],label='Final test')
    path=output.parents[0]/'phase4_runs'/RUN/'base_policy_results.csv'
    validation=pd.read_csv(path)
    ax.scatter(validation.acceptance_rate,validation.benchmark_utility_per_customer,
               marker='x',label='Policy validation (selection sample)')
    for r in base:
        ax.annotate(r['policy_id'],(r['acceptance_rate'],r['benchmark_utility_per_customer']),fontsize=6)
    ax.set(xlabel='Acceptance rate',ylabel='Synthetic utility units per customer',
           title='Base G=50 L=500 C=0; fixed policies')
    ax.legend()
    fig.savefig(output/'policy_utility.png',dpi=150,bbox_inches='tight')
    plt.close(fig)
    matrix=[[next(r['benchmark_utility_per_customer'] for r in summary['policy_metrics']
                  if r['scenario_id']==f'g{g}_l{loss}_c0' and r['policy_id']=='empirical')
             for loss in (250,500,750)] for g in (25,50,100)]
    fig,ax=plt.subplots()
    im=ax.imshow(matrix,cmap='RdYlGn')
    for i in range(3):
        for j in range(3):
            ax.text(j,i,f'{matrix[i][j]:.2f}',ha='center')
    ax.set(xticks=range(3),xticklabels=[250,500,750],yticks=range(3),yticklabels=[25,50,100],
           xlabel='Synthetic default loss',ylabel='Synthetic nondefault gain',
           title='Frozen empirical policies; final-test utility/customer')
    fig.colorbar(im,ax=ax)
    fig.savefig(output/'sensitivity.png',dpi=150,bbox_inches='tight')
    plt.close(fig)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['preflight','evaluate','report','score','monitor'])
    parser.add_argument('--root',default='.')
    parser.add_argument('--readiness',default='reports/phase5_readiness.json')
    parser.add_argument('--input')
    parser.add_argument('--output')
    parser.add_argument('--scenario',default='base')
    parser.add_argument('--policy',default='empirical')
    args=parser.parse_args(argv)
    if args.command == 'score' and (args.input is None or args.output is None):
        parser.error('score requires --input and --output')
    if args.command == 'monitor' and args.output is None:
        parser.error('monitor requires --output')
    root=Path(args.root).resolve()
    if args.command=='preflight':
        _,_,evidence=preflight(root)
        write_json(root/'reports/phase5_preflight.json',evidence)
        print('PASS: accepted identities; no test outcomes accessed')
    elif args.command=='evaluate':
        readiness = Path(args.readiness)
        if not readiness.is_absolute():
            readiness = root / readiness
        print(json.dumps(evaluate(root,readiness),indent=2))
    elif args.command=='report':
        print(json.dumps(report(root),indent=2))
    elif args.command=='score':
        from credit_risk.inference import score_file
        print(json.dumps(score_file(root/MANIFEST,args.input,args.output,
                                    scenario_id=args.scenario,policy_id=args.policy),indent=2))
    else:
        from credit_risk.monitoring import monitoring_report
        bundle, assignments, _ = preflight(root)
        development=partition(root,assignments,'development')
        validation=partition(root,assignments,'policy_validation')
        print(json.dumps(monitoring_report(bundle,development,validation,Path(args.output)),indent=2))


if __name__=='__main__':
    main()
