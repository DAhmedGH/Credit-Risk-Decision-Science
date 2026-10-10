"""Exercise the shipped scoring route in an isolated, offline publication container."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from types import ModuleType

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from credit_risk.inference import read_batch, score_frame
from credit_risk.models.pipelines import FinancialPredictorSelector, FoldLocalXGBClassifier
from credit_risk.scoring import load_public_bundle, score_public_file
from credit_risk.scoring_package import MEMBERS, ORIGIN, digest, restore_package, verify_package


def require(condition, message):
    if not condition:
        raise ValueError(message)


def forbidden(*args, **kwargs):
    raise AssertionError('Public scoring attempted fitting, networking or a private workflow')


class ForbiddenModule(ModuleType):
    def __getattr__(self, name):
        forbidden()


def main():
    root = Path(__file__).resolve().parents[1]
    require(not (root / 'data/raw').exists(), 'Isolation contains raw data')
    require(not (root / 'artifacts/models').exists(), 'Isolation contains historical artifacts')
    require(not (root / '.env').exists(), 'Isolation contains private environment settings')
    for cls in (Pipeline, ColumnTransformer, SimpleImputer, OneHotEncoder, StandardScaler,
                FinancialPredictorSelector, FoldLocalXGBClassifier, XGBClassifier):
        cls.fit = forbidden
    socket.create_connection = forbidden
    socket.socket.connect = forbidden
    for name in ('mlflow', 'psycopg', 'credit_risk.phase5'):
        sys.modules[name] = ForbiddenModule(name)
    os.environ.update({'POSTGRES_DB': 'unusable_database', 'POSTGRES_USER': 'unusable_role',
                       'POSTGRES_HOST_PORT': '1', 'POSTGRES_PASSWORD': 'unusable_fixture_setting',
                       'MLFLOW_TRACKING_URI': 'http://unusable.invalid:1'})
    archive = root / 'bundles/credit-risk-scoring-v1.tar.gz'
    archive_sha = (root / 'bundles/credit-risk-scoring-v1.sha256').read_text().split()[0]
    with tempfile.TemporaryDirectory(prefix='public-scoring-') as temporary:
        tmp = Path(temporary)
        installed = tmp / 'chosen-artifact-location'
        restoration = restore_package(archive, installed, expected_sha256=archive_sha)
        manifest = verify_package(installed)
        require({p.name for p in installed.iterdir()} == MEMBERS, 'Unexpected installation inventory')
        output = tmp / 'example-output'
        receipt = score_public_file(installed, root / 'examples/scoring_batch.csv', output,
                                    trust_artifacts=True)
        expected = (root / 'examples/scoring_output.csv').read_bytes()
        require((output / 'scored.csv').read_bytes() == expected, 'Accepted example bytes differ')
        require([receipt[k] for k in ('input_count', 'scored_count', 'quarantined_count')] == [12, 12, 0],
                'Example counts differ')
        command = [sys.executable, '-m', 'credit_risk.scoring', 'score', '--trust-artifacts',
                   '--artifacts', str(installed), '--input', str(root / 'examples/scoring_batch.csv'),
                   '--output', str(tmp / 'cli-output')]
        result = subprocess.run(command, cwd=tmp, capture_output=True, text=True)
        require(result.returncode == 0, result.stderr)
        require((tmp / 'cli-output/scored.csv').read_bytes() == expected, 'CWD-independent CLI differs')
        bundle, _ = load_public_bundle(installed, trust_artifacts=True)
        before = joblib.hash(bundle.base)
        frame = read_batch(root / 'examples/scoring_batch.csv').astype(object)
        frame['record_id'] = [f'{index:04}' for index in range(12)]
        frame.loc[1, 'limit_bal'] = 0
        frame.loc[3, 'pay_amt_2005_09'] = -1
        frame.loc[5, 'pay_status_2005_04'] = 999
        frame.loc[6, 'bill_amt_2005_04'] = -100
        frame.loc[7, 'bill_amt_2005_04'] = None
        scored, rejected, counts = score_frame(bundle, frame)
        require(counts['scored_count'] == 10 and counts['quarantined_count'] == 2,
                'Validation/quarantine counts differ')
        require(scored.record_id.tolist() == [f'{i:04}' for i in range(12) if i not in (1, 3)],
                'Scored identity/order differs')
        require(rejected.record_id.tolist() == ['0001', '0003'] and rejected.input_position.tolist() == [1, 3],
                'Quarantine identity/order differs')
        one, _, _ = score_frame(bundle, frame.iloc[[0]])
        require(one.p_default.iloc[0] == scored.p_default.iloc[0], 'Single-row/batch probability differs')
        empty_input = tmp / 'empty.csv'
        frame.iloc[:0].to_csv(empty_input, index=False)
        empty_receipt = score_public_file(installed, empty_input, tmp / 'empty-output', trust_artifacts=True)
        require([empty_receipt[k] for k in ('input_count', 'scored_count', 'quarantined_count')] == [0, 0, 0],
                'Empty-batch counts differ')
        checked = 0
        for cell in [{'scenario': manifest['base_scenario'], 'policies': bundle.policy['base_policies']},
                     *bundle.policy['sensitivity']['scenarios']]:
            scenario = cell['scenario']
            for policy in cell['policies']:
                values, _, _ = score_frame(bundle, frame, scenario_id=scenario['scenario_id'],
                                           policy_id=policy['policy_id'])
                p = values.p_default.to_numpy()
                accept = np.ones(len(p), bool) if policy['kind'] == 'all' else (
                    np.zeros(len(p), bool) if policy['kind'] == 'none' else p < policy['cutoff'])
                require(values.decision_simulated.tolist() == np.where(
                    accept, 'accept_simulated', 'abstain_simulated').tolist(), 'Frozen action differs')
                utility = np.where(accept, (1-p)*scenario['gain'] - p*scenario['loss'] - scenario['cost'], 0)
                require(np.array_equal(values.expected_utility, utility), 'Frozen expected utility differs')
                checked += 1
        require(checked == 88 and joblib.hash(bundle.base) == before, 'Model changed or policies omitted')
        report = {'verification_utc': datetime.now(timezone.utc).isoformat(),
                  'scope': 'Isolated publication image; no host bind mounts; network disabled by Docker',
                  'archive_sha256': archive_sha, 'archive_bytes': archive.stat().st_size,
                  'restoration': restoration, 'original_model': ORIGIN,
                  'example_counts': [12, 12, 0], 'example_byte_identical': True,
                  'example_output_sha256': digest(expected), 'cwd_independent_cli': True,
                  'quarantine_counts': [12, 10, 2], 'empty_counts': [0, 0, 0],
                  'record_identity_and_order': True, 'single_row_batch_agreement': True,
                  'frozen_policy_definitions_checked': checked, 'expected_utility_exact': True,
                  'invalid_database_and_tracking_settings': True,
                  'fit_methods_blocked': True, 'model_state_unchanged': True,
                  'final_test_evaluation': False, 'historical_artifacts_available': False,
                  'disposition': 'PASS'}
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
