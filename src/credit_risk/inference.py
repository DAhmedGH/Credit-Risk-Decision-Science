"""Unlabeled, database-independent scoring with the immutable accepted bundle."""
import csv
from pathlib import Path
import numpy as np
import pandas as pd
from credit_risk.data.schema import RAW_PREDICTORS, STATUS_COLUMNS, PAYMENT_COLUMNS
from credit_risk.features import PREDICTORS, build_features, feature_contract
from credit_risk.decisioning.policy import FrozenPolicy, Scenario, expected_utility
from credit_risk.models.bundle import load_frozen_bundle


def read_batch(path):
    path = Path(path)
    if path.suffix.lower() == '.parquet':
        return pd.read_parquet(path)
    if path.suffix.lower() != '.csv':
        raise ValueError('Input must be CSV or Parquet')
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.reader(stream, strict=True)
        try:
            header = next(reader, [])
            if not header:
                raise ValueError('CSV input must contain a header')
            if any('\x00' in field for field in header):
                raise ValueError('CSV input contains a NUL byte')
            if len(header) != len(set(header)):
                raise ValueError('Duplicate column names')
            for row in reader:
                # Match pandas' handling of truly empty lines, while preserving
                # quoted empty fields and multiline records as actual records.
                if not row:
                    continue
                if any('\x00' in field for field in row):
                    raise ValueError(f'CSV record ending at line {reader.line_num} '
                                     'contains a NUL byte')
                if len(row) != len(header):
                    raise ValueError(f'CSV record ending at line {reader.line_num} has '
                                     f'{len(row)} fields; expected {len(header)}')
        except csv.Error as exc:
            raise ValueError(f'Malformed CSV at line {reader.line_num}: {exc}') from exc
        # Width validation prevents pandas from silently treating record_id as
        # an implicit index and shifting every financial field on wide records.
        stream.seek(0)
        return pd.read_csv(stream, dtype={'record_id': str}, keep_default_na=False)


def validate_batch(frame):
    required = {'record_id', *RAW_PREDICTORS}
    if not frame.columns.is_unique or set(frame.columns) != required:
        raise ValueError('Schema must contain record_id and exactly the raw financial allowlist; '
                         'target, audit, ID aliases and engineered inputs are forbidden')
    identifiers = frame.record_id
    if identifiers.isna().any() or identifiers.astype(str).str.strip().eq('').any():
        raise ValueError('Record IDs must be nonempty')
    if identifiers.astype(str).str.contains('\x00', regex=False).any():
        raise ValueError('Record IDs must not contain NUL bytes')
    if identifiers.astype(str).duplicated().any():
        raise ValueError('Record IDs must be unique')
    valid, rejected, positions = [], [], []
    for position, (_, row) in enumerate(frame.iterrows()):
        try:
            raw = {}
            for name in RAW_PREDICTORS:
                value = row[name]
                if value is None or pd.isna(value) or value == '':
                    raw[name] = None
                    continue
                if isinstance(value, (bool, np.bool_)):
                    raise ValueError(f'{name}: boolean is not numeric')
                number = float(value)
                if not np.isfinite(number):
                    raise ValueError(f'{name}: nonfinite input')
                if name in STATUS_COLUMNS and number != int(number):
                    raise ValueError(f'{name}: categorical status must be integral')
                if name in PAYMENT_COLUMNS and number < 0:
                    raise ValueError(f'{name}: payment must be nonnegative')
                raw[name] = number
            features = build_features(raw)
            valid.append(features)
            positions.append(position)
        except (ValueError, TypeError, OverflowError) as exc:
            rejected.append({'record_id': str(row.record_id), 'input_position': position,
                             'validation_status': 'quarantined', 'reason': str(exc)})
    return pd.DataFrame(valid, columns=PREDICTORS, dtype=float), positions, rejected


def score_frame(bundle, frame, *, scenario_id='base', policy_id='empirical', model_version='frozen'):
    scenario_definitions = [{'scenario': Scenario().to_dict(),
                             'policies': bundle.policy['base_policies']}]
    scenario_definitions += bundle.policy['sensitivity']['scenarios']
    selected = next((x for x in scenario_definitions
                     if x['scenario']['scenario_id'] == scenario_id), None)
    if selected is None:
        raise ValueError('Unknown frozen scenario')
    definition = next((x for x in selected['policies'] if x['policy_id'] == policy_id), None)
    if definition is None:
        raise ValueError('Unknown frozen policy')
    scenario = Scenario.from_dict(selected['scenario'])
    policy = FrozenPolicy.from_dict(definition)
    X, positions, rejected = validate_batch(frame)
    columns = ['record_id', 'p_default', 'decision_simulated', 'expected_utility',
               'model_version', 'scenario_id', 'policy_id', 'validation_status']
    if len(X):
        p = bundle.predict_probability(X)
        accepted = policy.accept(p)
        scored = pd.DataFrame({'record_id': frame.iloc[positions].record_id.astype(str).to_numpy(),
                              'p_default': p,
                              'decision_simulated': np.where(accepted, 'accept_simulated',
                                                            'abstain_simulated'),
                              'expected_utility': np.where(accepted, expected_utility(p, scenario), 0),
                              'model_version': model_version, 'scenario_id': scenario_id,
                              'policy_id': policy_id, 'validation_status': 'valid'})
    else:
        scored = pd.DataFrame(columns=columns)
    quarantine = pd.DataFrame(rejected, columns=['record_id', 'input_position',
                                               'validation_status', 'reason'])
    receipt = {'input_count': len(frame), 'scored_count': len(scored),
               'quarantined_count': len(quarantine), 'counts_reconcile':
               len(frame) == len(scored) + len(quarantine), 'fitting': False,
               'database_access': False, 'expected_utility': 'chosen action; abstention zero'}
    return scored, quarantine, receipt


def score_file(manifest, input_path, output_dir, *, scenario_id='base', policy_id='empirical'):
    from credit_risk.artifacts import write_json, file_sha256
    bundle = load_frozen_bundle(manifest)
    if bundle.feature_schema != feature_contract():
        raise ValueError('Scoring feature formulas differ from frozen schema')
    import importlib
    for module_name, relative in (
        ('credit_risk.features', 'src/credit_risk/features/__init__.py'),
        ('credit_risk.models.pipelines', 'src/credit_risk/models/pipelines.py'),
        ('credit_risk.data.schema', 'src/credit_risk/data/schema.py'),
    ):
        live = Path(importlib.import_module(module_name).__file__)
        frozen = Path(manifest).parent / 'completion_source' / relative
        if file_sha256(live) != file_sha256(frozen):
            raise ValueError('Scoring transformation source differs from accepted source')
    version = file_sha256(Path(manifest).parent / 'probability_bundle.joblib')
    scored, rejected, receipt = score_frame(bundle, read_batch(input_path), scenario_id=scenario_id,
                                          policy_id=policy_id, model_version=version)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    scored.to_csv(output / 'scored.csv', index=False)
    rejected.to_csv(output / 'quarantined.csv', index=False)
    receipt.update({'input_sha256': file_sha256(input_path), 'bundle_sha256': version,
                    'manifest_sha256': file_sha256(manifest), 'scenario_id': scenario_id,
                    'policy_id': policy_id})
    write_json(output / 'receipt.json', receipt)
    return receipt
