"""Calibration/policy workflow and resumable, durable pre-test freeze. No test evaluation."""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import time
import tomllib

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from credit_risk.artifacts import file_sha256, json_bytes, sha256_bytes, write_csv, write_json
from credit_risk.config import PROJECT_ROOT
from credit_risk.decisioning.policy import Scenario, freeze_policies, evaluate_policy, sensitivity_analysis
from credit_risk.features import PREDICTORS, feature_contract
from credit_risk.models.bundle import ProbabilityBundle
from credit_risk.models.calibration import fit_mappings, select_mapping, reliability_bins
from credit_risk.models.evaluation import probability_metrics
from credit_risk.models.phase4_inputs import accepted_integrity, log_access, routed_partitions, SELECTED
from credit_risk.models.pipelines import positive_probability
from credit_risk.phase2 import _local_experiment, _mark_failed


def source_context(root):
    paths = sorted({*root.glob('src/**/*.py'), *root.glob('configs/*.toml'),
                    *root.glob('scripts/*phase4*'), root / 'pyproject.toml',
                    root / 'requirements.lock', root / 'requirements-phase4.in'})
    hashes = {str(path.relative_to(root)): file_sha256(path) for path in paths if path.is_file()}
    return {'code_file_hashes': hashes, 'code_tree_sha256': sha256_bytes(json_bytes(hashes)),
            'dependency_lock_sha256': file_sha256(root / 'requirements.lock'), 'git_commit': None}


def report_definitions():
    return {
        'final_test_access': 'Phase 5 only, after independent review PASS and complete freeze verification',
        'model_comparison': 'All five exact raw development pipelines plus selected probability bundle; no reselection',
        'probability_metrics': ['average_precision (AP, positive class 1)', 'roc_auc', 'log_loss', 'brier_score'],
        'reliability': {'bins': [i / 10 for i in range(11)], 'intervals': '[lower, upper), last includes 1',
                        'sparse_count': 100, 'empty_bins': 'N/A'},
        'policies': 'Every saved scenario and all eight saved policy definitions; fixed cutoffs, p < cutoff',
        'detection': 'Abstain is positive high-risk detection; precision, recall, F1, FPR and TP/FP/FN/TN',
        'undefined': 'N/A (JSON null); report undefined bootstrap counts, never coerce to zero',
        'uncertainty': {'repetitions': 1000, 'seed': 42, 'interval': '95% percentile',
                        'resampling': 'fingerprint groups with replacement; retain every row in sampled group',
                        'paired': True, 'conditioning': 'fixed fitted models and policies',
                        'metrics': ['AP', 'ROC-AUC', 'Brier', 'log_loss', 'policy per-customer benchmark utility',
                                    'acceptance rate', 'accepted default rate'],
                        'comparisons': 'selected probability bundle minus each raw reference; empirical minus analytic/all/none per scenario',
                        'invalid_replicates': 'omit only undefined statistic; report number valid/undefined; N/A if none'},
        'diagnostics': 'Frozen .5 detection cases and development-defined slices; do not choose test examples',
        'limitations': 'Historical existing Taiwan accounts; hypothetical unchanged benchmark outcome, no causal/profit/fairness inference',
    }


def reliability_svg(path, variants):
    """Fixed-bin reliability and counts without requiring a plotting dependency."""
    colors = {'raw': '#1764ab', 'sigmoid': '#bb4411', 'isotonic': '#278044'}
    items = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600" viewBox="0 0 900 600">',
             '<rect width="900" height="600" fill="white"/>',
             '<text x="35" y="30" font-size="20">Policy-validation reliability: fixed equal-width bins</text>',
             '<path d="M80 70 V430 H440 M80 430 L440 70" fill="none" stroke="#888"/>',
             '<text x="150" y="475">Mean predicted probability (0–1)</text>',
             '<text x="85" y="58">Observed default fraction (0–1)</text>',
             '<text x="485" y="58">Bin counts (sparse: fewer than 100)</text>']
    for index in range(11):
        value = index / 10
        items.append(f'<text x="{76+360*value}" y="451" font-size="10">{value:.1f}</text>')
        items.append(f'<text x="45" y="{434-360*value}" font-size="10">{value:.1f}</text>')
    for k, (name, rows) in enumerate(variants.items()):
        color = colors[name]
        items.append(f'<text x="{110+k*120}" y="515" fill="{color}">{name}</text>')
        points = []
        for row in rows:
            if row['count']:
                x = 80 + 360 * row['mean_probability']
                y = 430 - 360 * row['observed_rate']
                points.append(f'{x},{y}')
                fill = 'white' if row['sparse'] else color
                items.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{fill}" stroke="{color}"/>')
            items.append(f'<text x="{485+k*125}" y="{88+row["bin"]*31}" fill="{color}" font-size="12">'
                         f'{row["lower"]:.1f}–{row["upper"]:.1f}: {row["count"]}'
                         f'{" *" if row["sparse"] else ""}</text>')
        items.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}"/>')
    items.extend(['<text x="80" y="555">Hollow points / *: sparse bins. Empty bins have no point.</text>',
                  '<text x="80" y="578">Log loss and Brier assess probability quality; this plot diagnoses calibration.</text>', '</svg>'])
    path.write_text('\n'.join(items))


def _table(path, rows):
    write_csv(path, rows, tuple(rows[0]))


def _checkpoint(output, state):
    state['artifacts'] = {str(path.relative_to(output)): file_sha256(path)
                          for path in sorted(output.rglob('*')) if path.is_file()
                          and path.name not in {'checkpoint.json', 'freeze_manifest.json', 'review.json'}}
    write_json(output / 'checkpoint.json', state)


def _verify_checkpoint(output):
    state = json.loads((output / 'checkpoint.json').read_text())
    for name, digest in state['artifacts'].items():
        if file_sha256(output / name) != digest:
            raise ValueError(f'Phase 4 checkpoint changed: {name}')
    return state


def run(root=PROJECT_ROOT):
    from mlflow import MlflowClient
    root = Path(root).resolve()
    config = tomllib.loads((root / 'configs/phase4.toml').read_text())
    if config['calibration_tolerance'] != .005 or config['seed'] != 42 or config['threads'] != 1:
        raise ValueError('Phase 4 fixed settings changed')
    models, metadata, assignments, integrity = accepted_integrity(root, config['model_root'])
    access = log_access(root, integrity, 'calibration and policy simulation')
    tracking = (root / config['tracking_dir']).resolve()
    client = MlflowClient(tracking_uri=tracking.as_uri())
    experiment = _local_experiment(client, 'credit-risk-phase4-fixed-base', tracking)
    run_id = client.create_run(experiment, tags={'mlflow.runName': 'phase4-calibration-policy',
                                               'partition': 'calibration,policy_validation'}).info.run_id
    output = root / config['output_dir'] / run_id
    output.mkdir(parents=True, exist_ok=False)
    compact = root / 'reports/phase4_runs' / run_id
    compact.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        state = {'run_id': run_id, 'output_dir': str(output), 'phase': 4, 'integrity': integrity,
                 'access': access, 'context': source_context(root), 'config': config,
                 'complete_bundle_frozen': False, 'independent_review_status': 'PENDING'}
        write_json(output / 'execution_context.json', state)
        # Snapshot the exact code used by future resumed explanations/loading.
        for name in state['context']['code_file_hashes']:
            target = output / 'source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, target)
        parts = routed_partitions(root, assignments)
        dev, cal, policy = (parts[key] for key in ('development', 'calibration', 'policy_validation'))
        Xcal, Xpolicy = cal[list(PREDICTORS)], policy[list(PREDICTORS)]
        base = models[SELECTED]
        before_state = joblib.hash(base)
        before = {key: positive_probability(base, part[list(PREDICTORS)]) for key, part in parts.items()}
        with threadpool_limits(limits=1):
            variants = fit_mappings(base, Xcal, cal.default_next_month, partition='calibration',
                                    calibration_ids=cal.client_id.tolist(), development_ids=dev.client_id.tolist())
        probabilities = {key: positive_probability(estimator, Xpolicy) for key, estimator in variants.items()}
        metrics = {key: probability_metrics(policy.default_next_month, p) for key, p in probabilities.items()}
        chosen = select_mapping(metrics)
        rows = [{'variant': key, 'selected': key == chosen, **value} for key, value in metrics.items()]
        _table(compact / 'calibration_comparison.csv', rows)
        bins = {key: reliability_bins(policy.default_next_month, p) for key, p in probabilities.items()}
        _table(compact / 'reliability_bins.csv', [{'variant': key, **row} for key, data in bins.items() for row in data])
        reliability_svg(compact / 'reliability.svg', bins)
        p = probabilities[chosen]
        policies = freeze_policies(p, policy.default_next_month, Scenario())
        results = [evaluate_policy(p, policy.default_next_month, definition, Scenario()) for definition in policies]
        _table(compact / 'base_policy_results.csv', results)
        sensitivity = sensitivity_analysis(p, policy.default_next_month)
        write_json(compact / 'sensitivity.json', sensitivity)
        sensitivity_rows = [{**item['scenario'], **row} for item in sensitivity['scenarios'] for row in item['results']]
        _table(compact / 'sensitivity.csv', sensitivity_rows)
        decisions = {'selected_mapping': chosen, 'selection_partition': 'policy_validation',
                     'log_loss_tolerance': .005, 'simplicity_order': ['raw', 'sigmoid', 'isotonic'],
                     'base_policies': [definition.to_dict() for definition in policies], 'sensitivity': sensitivity,
                     'payoff_units': 'synthetic dimensionless utility units; historical limits/bills are not exposure'}
        write_json(output / 'policy.json', decisions)
        write_json(output / 'feature_schema.json', feature_contract())
        write_json(output / 'report_definitions.json', report_definitions())
        fit_evidence = {'calibration_ids_sha256': sha256_bytes(json_bytes(cal.client_id.tolist())),
                        'development_ids_sha256': sha256_bytes(json_bytes(dev.client_id.tolist())),
                        'policy_ids_sha256': sha256_bytes(json_bytes(policy.client_id.tolist())),
                        'calibration_rows': len(cal), 'policy_rows': len(policy),
                        'api': 'CalibratedClassifierCV(FrozenEstimator(base), ensemble=False)',
                        'base_joblib_hash_before': before_state, 'base_joblib_hash_after': joblib.hash(base),
                        'base_predictions_unchanged': all(np.array_equal(before[key], positive_probability(base, part[list(PREDICTORS)]))
                                                          for key, part in parts.items()),
                        'base_fits': 0, 'mapping_fits': 2}
        if not fit_evidence['base_predictions_unchanged'] or before_state != joblib.hash(base):
            raise ValueError('Base changed during calibration')
        write_json(output / 'calibration_fit_evidence.json', fit_evidence)
        # Exact original fitted pipeline bytes and metadata remain separately loadable.
        for candidate, paths in json.loads((Path(config['model_root']) / 'reports/phase3_runs' /
                                            config['selection_run'] / 'manifest.json').read_text())['bundles'].items():
            target = output / 'accepted_models' / candidate
            target.mkdir(parents=True)
            for key in ('pipeline', 'metadata'):
                source = Path(config['model_root']) / paths[key]
                shutil.copyfile(source, target / source.name)
        bundle = ProbabilityBundle(base, variants[chosen], chosen, feature_contract(),
                                   {'selected_candidate': SELECTED, 'reference_metadata': metadata,
                                    'integrity': integrity, 'positive_class': 1}, decisions, models)
        joblib.dump(variants, output / 'calibration_variants.joblib')
        joblib.dump(bundle, output / 'probability_bundle.joblib')
        restored = joblib.load(output / 'probability_bundle.joblib')
        after = restored.predict_probability(Xpolicy)
        if not np.array_equal(p, after):
            raise ValueError('Save/load predictions differ')
        if not np.allclose(after[:4], np.array([restored.predict_probability(Xpolicy.iloc[[i]])[0] for i in range(4)]), atol=1e-12, rtol=0):
            raise ValueError('Single/batch agreement failed')
        write_json(output / 'serialization_evidence.json', {'save_load_exact': True, 'batch_single_atol': 1e-12})
        np.savez_compressed(output / 'policy_predictions.npz', client_id=policy.client_id.to_numpy(),
                            y=policy.default_next_month.to_numpy(), **probabilities)
        for key, value in {'selected_mapping': chosen, 'calibration_rows': len(cal), 'policy_rows': len(policy),
                           'base_fits': 0, 'mapping_fits': 2, 'selection_run': config['selection_run'],
                           'source_sha256': integrity['input_hashes']['data/raw/default of credit card clients.xls'],
                           'split_sha256': integrity['input_hashes']['artifacts/split_manifest.csv'],
                           'code_tree_sha256': state['context']['code_tree_sha256'],
                           'dependency_lock_sha256': state['context']['dependency_lock_sha256'],
                           'git_commit': 'unavailable'}.items():
            client.log_param(run_id, key, value)
        for variant, data in metrics.items():
            for name, value in data.items():
                client.log_metric(run_id, f'policy_validation_{variant}_{name}', value)
        for result in results:
            for name, value in result.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    client.log_metric(run_id, f'policy_validation_{result["policy_id"]}_{name}', value)
        state.update({'selected_mapping': chosen, 'metrics': metrics,
                      'base_policy_results': results, 'runtime_seconds': time.perf_counter() - started,
                      'compact_dir': str(compact), 'core_complete': True})
        _checkpoint(output, state)
        result = explanations_and_freeze(root, output, parts=parts, models=models, state=state)
        client.log_metric(run_id, 'phase4_runtime_seconds', time.perf_counter() - started)
        client.log_artifacts(run_id, str(compact), 'compact')
        client.log_artifacts(run_id, str(output), 'bundle')
        client.set_tag(run_id, 'complete_bundle_frozen', str(result['complete_bundle_frozen']))
        client.set_terminated(run_id, 'FINISHED')
        return result
    except Exception as error:
        _mark_failed(client, run_id, error)
        raise


def explanations_and_freeze(root, output, *, parts=None, models=None, state=None):
    from credit_risk.explanations import run_descriptive_analysis, run_explanations
    if (output / 'freeze_manifest.json').exists():
        existing = json.loads((output / 'freeze_manifest.json').read_text())
        if existing.get('complete_bundle_frozen'):
            raise ValueError('Cannot resume or alter a completed frozen bundle')
    state = state or _verify_checkpoint(output)
    state['completion_context'] = source_context(Path(root))
    for name in state['completion_context']['code_file_hashes']:
        target = output / 'completion_source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(root) / name, target)
    current_models, _, assignments, integrity = accepted_integrity(root, state['config']['model_root'])
    if integrity != state['integrity']:
        raise ValueError('Accepted identities changed since core execution')
    if parts is None:
        log_access(root, integrity, 'resume explanations (zero mapping/base fits)')
        parts = routed_partitions(root, assignments)
    models = models or current_models
    policy, dev = parts['policy_validation'], parts['development']
    bundle = joblib.load(output / 'probability_bundle.joblib')
    chosen_p = bundle.predict_probability(policy[list(PREDICTORS)])
    explanation_dir = output / 'explanations'
    explanation_dir.mkdir(exist_ok=True)
    missing = [name for name in ('shap', 'matplotlib') if importlib.util.find_spec(name) is None]
    if missing:
        descriptions = run_descriptive_analysis(models['logistic_00_engineered_none'], dev, policy,
                                                chosen_p, explanation_dir,
                                                reference_identity=state['integrity']['model_sha256']['logistic_00_engineered_none'])
        state.update({'explanations_complete': False, 'blockers': ['Missing plotting/SHAP dependencies: ' + ', '.join(missing)],
                      'descriptive_analysis': descriptions, 'complete_bundle_frozen': False})
    else:
        descriptions = run_explanations(models[SELECTED], models['logistic_00_engineered_none'],
                                        dev, policy, chosen_p, explanation_dir,
                                        selected_model_identity=state['integrity']['model_sha256'][SELECTED],
                                        reference_identity=state['integrity']['model_sha256']['logistic_00_engineered_none'])
        state.update({'explanations_complete': True, 'blockers': [], 'explanations': descriptions})
    compact = Path(state['compact_dir'])
    for path in explanation_dir.iterdir():
        if path.suffix in {'.csv', '.json', '.svg', '.png'} and path.name != 'shap_settings.json':
            # Customer examples/IDs are local artifacts, not portfolio aggregate copies.
            if 'case' not in path.name and 'local' not in path.name:
                shutil.copyfile(path, compact / path.name)
    write_json(output / 'model_metadata.json', {'mapping': state['selected_mapping'], 'integrity': integrity,
               'positive_class': 1, 'base_fitted_partition': 'development', 'calibration_partition': 'calibration',
               'selection_partition': 'policy_validation', 'final_test_evaluated': False})
    (output / 'model_card.md').write_text(
        '# Existing-account next-month risk bundle\n\n'
        'Official UCI 350 historical Taiwan card accounts. All released September histories are assumed '
        'available at snapshot time. No validated new-loan underwriting or contemporary Canadian representativeness.\n\n'
        'Fixed development-trained XGBoost; mappings fit on calibration only; selection and hypothetical policies '
        'use policy validation. Final test has not been evaluated. Utility is synthetic, not observed profit or causal impact. '
        'Demographic exclusion does not establish fairness. SHAP explains raw tree log odds, not causal effects or automatically calibrated probabilities.\n')
    _checkpoint(output, state)
    freeze = {'version': 'pre-test-v1', 'run_id': state['run_id'], 'bundle_path': 'probability_bundle.joblib',
              'selected_mapping': state['selected_mapping'], 'integrity': integrity,
              'explanations_complete': state['explanations_complete'], 'complete_bundle_frozen': False,
              'independent_review_status': 'PENDING', 'artifacts': state['artifacts'],
              'report_definitions_sha256': file_sha256(output / 'report_definitions.json'),
              'status': 'BLOCKED' if missing else 'AWAITING_INDEPENDENT_REVIEW', 'blockers': state['blockers']}
    freeze['freeze_sha256'] = sha256_bytes(json_bytes(freeze))
    write_json(output / 'freeze_manifest.json', freeze)
    write_json(compact / 'manifest.json', {**state, 'freeze_manifest': str(output / 'freeze_manifest.json'),
                                         'freeze_sha256': freeze['freeze_sha256']})
    write_json(Path(root) / 'reports/phase4_latest.json', {'run_id': state['run_id'], 'output_dir': str(output),
               'compact_dir': str(compact), 'complete_bundle_frozen': False,
               'freeze_sha256': freeze['freeze_sha256'], 'blockers': state['blockers']})
    return {'run_id': state['run_id'], 'output_dir': str(output), 'selected_mapping': state['selected_mapping'],
            'core_complete': True, 'complete_bundle_frozen': False, 'blockers': state['blockers']}


def finalize(root, output, review_receipt):
    """Seal only independently reviewed complete artifact content; never evaluate test."""
    from credit_risk.models.bundle import verify_freeze
    output, root = Path(output), Path(root)
    state = _verify_checkpoint(output)
    if not state.get('explanations_complete') or state.get('blockers'):
        raise ValueError('SHAP and all Phase 4 requirements must complete before sealing')
    receipt = json.loads(Path(review_receipt).read_text())
    artifact_identity = sha256_bytes(json_bytes(state['artifacts']))
    if (receipt.get('run_id') != state['run_id'] or receipt.get('disposition') != 'PASS'
            or receipt.get('reviewed_artifacts_sha256') != artifact_identity):
        raise ValueError('Independent PASS review must bind this exact completed artifact inventory')
    review_path = Path(receipt['review_path'])
    if not review_path.is_absolute():
        review_path = root / review_path
    if file_sha256(review_path) != receipt['review_sha256']:
        raise ValueError('Independent review document changed')
    # Runtime code must match the code independently reviewed for completion.
    if source_context(root) != state['completion_context']:
        raise ValueError('Completion code/environment changed after independent review; resume then review again')
    _, _, _, integrity = accepted_integrity(root, state['config']['model_root'])
    if integrity != state['integrity']:
        raise ValueError('Accepted scientific inputs changed after review')
    frozen_path = output / 'freeze_manifest.json'
    manifest = json.loads(frozen_path.read_text())
    existing_identity = manifest.pop('freeze_sha256')
    if sha256_bytes(json_bytes(manifest)) != existing_identity:
        raise ValueError('Existing freeze manifest content identity changed')
    if any(manifest[key] != state[key] for key in ('run_id', 'selected_mapping', 'integrity')):
        raise ValueError('Freeze scientific identity differs from reviewed checkpoint')
    if manifest['artifacts'] != state['artifacts']:
        raise ValueError('Freeze inventory differs from reviewed checkpoint')
    write_json(output / 'review.json', receipt)
    shutil.copyfile(review_path, output / 'review.md')
    manifest['artifacts'].update({'review.json': file_sha256(output / 'review.json'),
                                  'review.md': file_sha256(output / 'review.md')})
    manifest.update({'complete_bundle_frozen': True, 'independent_review_status': 'PASS',
                     'status': 'FROZEN', 'blockers': [], 'completion_context': state['completion_context']})
    manifest['freeze_sha256'] = sha256_bytes(json_bytes(manifest))
    # Validate candidate in place before making it the official final manifest.
    candidate = output / 'freeze_candidate.json'
    write_json(candidate, manifest)
    verify_freeze(candidate)
    write_json(frozen_path, manifest, frozen=False)
    candidate.unlink()
    latest = {'run_id': state['run_id'], 'output_dir': str(output),
              'compact_dir': state['compact_dir'], 'complete_bundle_frozen': True,
              'freeze_sha256': manifest['freeze_sha256'], 'blockers': []}
    write_json(root / 'reports/phase4_latest.json', latest)
    write_json(Path(state['compact_dir']) / 'freeze_manifest.json', manifest)
    return latest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['integrity', 'run', 'resume', 'finalize'])
    parser.add_argument('--run-id')
    parser.add_argument('--review-receipt')
    args = parser.parse_args(argv)
    if args.stage == 'integrity':
        from credit_risk.models.phase4_inputs import preflight
        result = preflight(PROJECT_ROOT)
    elif args.stage == 'run':
        result = run()
    else:
        if not args.run_id or len(args.run_id) != 32 or any(c not in '0123456789abcdef' for c in args.run_id):
            raise ValueError('resume requires a saved 32-character --run-id')
        output = PROJECT_ROOT / 'artifacts/models/phase4' / args.run_id
        if args.stage == 'finalize':
            if not args.review_receipt:
                raise ValueError('finalize requires --review-receipt from independent scientific review')
            result = finalize(PROJECT_ROOT, output, args.review_receipt)
        else:
            result = explanations_and_freeze(PROJECT_ROOT, output)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
