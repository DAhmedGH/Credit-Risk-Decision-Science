"""Verify accepted Phase 3 bytes before permitting Phase 4 outcome interpretation."""

import csv
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from credit_risk.artifacts import file_sha256, json_bytes, sha256_bytes, write_json
from credit_risk.features import PREDICTORS, feature_contract
from credit_risk.models.inputs import _selected_csv, verify_assignments
from credit_risk.models.calibration import verify_fit_scope
from credit_risk.splits.allocation import financial_fingerprint

SELECTION_RUN = "6a0725d18b164582938e0b07b2df6b27"
SELECTED = "xgboost_05_engineered_none"
DURABLE_ROOT = Path('/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime')
EXPECTED_MODELS = {SELECTED, 'dummy_prior', 'logistic_00_engineered_none',
                   'random_forest_02_engineered_none', 'xgboost_04_engineered_none'}


def accepted_integrity(root, model_root=DURABLE_ROOT):
    root, model_root = Path(root), Path(model_root)
    manifest_path = model_root / 'reports/phase3_runs' / SELECTION_RUN / 'manifest.json'
    receipt = json.loads((root / 'reports/phase3_acceptance.json').read_text())
    inventory = root / receipt['preservation_inventory']['path']
    if file_sha256(inventory) != receipt['preservation_inventory']['sha256']:
        raise ValueError('Accepted preservation inventory changed')
    with inventory.open(newline='') as stream:
        inventory_rows = list(csv.DictReader(stream))
    inventory_manifest = next(row for row in inventory_rows
                              if row['relative_path'] == str(manifest_path.relative_to(model_root)))
    if file_sha256(manifest_path) != inventory_manifest['sha256']:
        raise ValueError('Accepted selection manifest changed')
    manifest = json.loads(manifest_path.read_text())
    if (manifest['selected_candidate_id'] != SELECTED or set(manifest['bundles']) != EXPECTED_MODELS
            or not manifest['base_selected'] or manifest['complete_bundle_frozen']):
        raise ValueError('Accepted Phase 3 identity differs')
    for name, version in manifest['dependencies'].items():
        if importlib.metadata.version(name) != version:
            raise ValueError(f'Accepted dependency changed: {name}')
    for name, digest in manifest['code_file_hashes'].items():
        override = {'src/credit_risk/phase3.py': 'phase3.py',
                    'src/credit_risk/__main__.py': '__main__.py',
                    'requirements.lock': 'requirements.lock'}.get(name)
        archived = (root / 'reports/phase3_source_snapshots/accepted' / override if override else
                    model_root / 'provenance/original_code' / name)
        if file_sha256(archived) != digest:
            raise ValueError(f'Accepted source archive changed: {name}')
        if name.startswith('src/') and not override and file_sha256(root / name) != digest:
            raise ValueError(f'Accepted pipeline source changed: {name}')
    if sha256_bytes(json_bytes(manifest['code_file_hashes'])) != manifest['code_tree_sha256']:
        raise ValueError('Accepted source tree differs')
    hashes = dict(manifest['input_hashes'])
    export = json.loads((root / 'artifacts/phase1_export_manifest.json').read_text())
    hashes['data/processed/audit_attributes.csv'] = export['audit_export_sha256']
    for name, digest in hashes.items():
        if file_sha256(root / name) != digest:
            raise ValueError(f'Accepted input changed: {name}')
    if json.loads((root / 'artifacts/feature_contract_v1_1.json').read_text()) != feature_contract():
        raise ValueError('Feature formulas changed')
    with (root / 'artifacts/split_manifest.csv').open(newline='') as stream:
        assignments = list(csv.DictReader(stream))
    source = export['source_sha256']
    verify_assignments(assignments, source)
    ids = {partition: [int(row['client_id']) for row in assignments if row['partition'] == partition]
           for partition in ('development', 'calibration', 'policy_validation', 'final_test')}
    verify_fit_scope(*ids.values())
    if [len(x) for x in ids.values()] != [18000, 4500, 3000, 4500]:
        raise ValueError('Accepted partition sizes changed')
    models, metadata = {}, {}
    for candidate, paths in manifest['bundles'].items():
        model_path, metadata_path = model_root / paths['pipeline'], model_root / paths['metadata']
        if file_sha256(metadata_path) != manifest['artifacts'][paths['metadata']]:
            raise ValueError('Model metadata hash differs')
        meta = json.loads(metadata_path.read_text())
        if (file_sha256(model_path) != meta['pipeline_sha256']
                or meta['training_partition'] != 'development' or meta['training_rows'] != 18000
                or meta['positive_class'] != 1 or not meta['save_load_predictions_match']):
            raise ValueError('Accepted fitted identity differs')
        models[candidate] = joblib.load(model_path)
        if list(models[candidate].classes_) != [0, 1]:
            raise ValueError('Positive class mapping changed')
        metadata[candidate] = meta
    return models, metadata, assignments, {'input_hashes': hashes,
            'accepted_selection_manifest_sha256': file_sha256(manifest_path),
            'accepted_code_tree_sha256': manifest['code_tree_sha256'],
            'accepted_lock_sha256': manifest['dependency_lock_sha256'],
            'model_sha256': {key: meta['pipeline_sha256'] for key, meta in metadata.items()},
            'partition_sizes': {key: len(value) for key, value in ids.items()},
            'selection_run': SELECTION_RUN, 'selected_candidate': SELECTED,
            'durable_model_root': str(model_root)}


def log_access(root, integrity, stage):
    event = {'utc': datetime.now(timezone.utc).isoformat(), 'stage': stage,
             'permitted': {'development': 'background/explanations; base never fitted',
                           'calibration': 'fit mappings only',
                           'policy_validation': 'mapping/policy selection and descriptions',
                           'final_test': 'assignment IDs and byte hashes only'},
             'routing': 'Full CSV row strings traversed; route by ID before numeric/outcome conversion',
             'final_test_outcomes_interpreted': False, **integrity}
    log = Path(root) / 'docs/partition-access-log.md'
    with log.open('a') as stream:
        stream.write('\n```json\n' + json.dumps(event, indent=2) + '\n```\n')
    with (Path(root) / 'docs/test-exposure-log.md').open('a') as stream:
        stream.write(f"\n| {event['utc']} — Phase 4 {stage} | Full CSV row strings routed by ID; "
                     'only development/calibration/policy-validation values interpreted | '
                     f"split `{integrity['input_hashes']['artifacts/split_manifest.csv']}` | "
                     'Final-test outcome strings not converted, summarized, fitted or evaluated |\n')
    return event


def routed_partitions(root, assignments):
    root = Path(root)
    allowed = {int(row['client_id']) for row in assignments if row['partition'] != 'final_test'}
    policy_ids = {int(row['client_id']) for row in assignments
                  if row['partition'] == 'policy_validation'}
    all_ids = {int(row['client_id']) for row in assignments}

    def features(row):
        # Fingerprints use None as their missing-value marker. Keep that marker
        # until the profile is verified; the pipeline then converts missing
        # financial values to NaN for its fitted imputers.
        result = {name: float(row[name]) if row[name] else None for name in PREDICTORS}
        if any(value is not None and not np.isfinite(value) for value in result.values()):
            raise ValueError('Nonfinite financial value')
        return result

    def labels(row):
        if row['default_next_month'] not in {'0', '1'}:
            raise ValueError('Outcome must be binary')
        return int(row['default_next_month'])

    financial, feature_ids = _selected_csv(root / 'data/processed/financial_features_v1.csv',
                                          ('client_id', *PREDICTORS), allowed, features)
    outcomes, label_ids = _selected_csv(root / 'data/processed/labels.csv',
                                      ('client_id', 'default_next_month'), allowed, labels)
    columns = ('client_id', 'sex', 'age', 'education', 'marriage',
               'sex_group', 'education_group', 'marriage_group')
    audits, audit_ids = _selected_csv(root / 'data/processed/audit_attributes.csv', columns,
                                    policy_ids, lambda row: {name: int(row[name]) if row[name] else None
                                                            for name in columns[1:5]})
    if any(ids != all_ids for ids in (feature_ids, label_ids, audit_ids)):
        raise ValueError('Source/export/assignment ID coverage differs')
    parts = {key: [] for key in ('development', 'calibration', 'policy_validation')}
    for row in assignments:
        if row['partition'] == 'final_test':
            continue
        identifier = int(row['client_id'])
        if financial_fingerprint(financial[identifier]) != row['fingerprint']:
            raise ValueError('Financial fingerprint differs from frozen assignment')
        parts[row['partition']].append({'client_id': identifier, 'fingerprint': row['fingerprint'],
                                       'default_next_month': outcomes[identifier],
                                       **financial[identifier], **audits.get(identifier, {})})
    return {key: pd.DataFrame(rows).sort_values('client_id').reset_index(drop=True)
            for key, rows in parts.items()}


def preflight(root):
    _, _, _, evidence = accepted_integrity(root)
    write_json(Path(root) / 'reports/phase4_integrity.json', evidence)
    return evidence
