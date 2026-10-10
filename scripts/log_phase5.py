"""Resume aggregate-only local tracking using batched writes, never reevaluate."""
import argparse
import json
from pathlib import Path
import time
from mlflow import MlflowClient
from mlflow.entities import Metric, RunTag
from credit_risk.artifacts import file_sha256, write_json

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run-id', required=True)
args = parser.parse_args()
root = Path('.').resolve()
results = json.loads((root / 'reports/phase5/results.json').read_text())
completion = json.loads((root / 'artifacts/runtime/phase5/final_evaluation/completion.json').read_text())
store = root / 'mlruns/phase5'
client = MlflowClient(tracking_uri=store.as_uri())
run = client.get_run(args.run_id)
if run.data.params.get('evaluation_run_id') != completion['evaluation_run_id']:
    raise ValueError('Tracking run belongs to a different evaluation')
prior_status = run.info.status
values = {}
for candidate, row in results['model_metrics'].items():
    for metric, value in row.items():
        if value is not None:
            values['final_test/' + candidate + '/' + metric] = value
for row in results['policy_metrics']:
    for metric in ('accepted_count', 'acceptance_rate', 'accepted_default_rate',
                   'predicted_expected_utility_total', 'benchmark_utility_total',
                   'benchmark_utility_per_customer'):
        if row[metric] is not None:
            values['final_test/' + row['scenario_id'] + '/' + row['policy_id'] + '/' + metric] = row[metric]
values['final_test/scoring_seconds'] = completion['scoring_seconds']
started = time.perf_counter()
stamp = int(time.time() * 1000)
client.log_batch(args.run_id, metrics=[Metric(key, float(value), stamp, 0) for key, value in values.items()],
                 params=[], tags=[RunTag('logging_scope', 'saved aggregate recovery; no evaluator or fits')])
for candidate in results['model_metrics']:
    metadata = root / 'artifacts/models/phase4' / completion['run_id'] / 'accepted_models' / candidate / 'metadata.json'
    if metadata.exists():
        client.log_artifact(args.run_id, str(metadata), artifact_path='resolved_parameters/' + candidate)
client.log_artifacts(args.run_id, str(root / 'reports/phase5'), artifact_path='frozen_reports')
client.log_artifact(args.run_id, str(root / 'reports/phase5_readiness.json'))
client.log_artifact(args.run_id, str(root / 'artifacts/runtime/phase5/final_evaluation/source/requirements.lock'))
client.log_batch(args.run_id, metrics=[Metric('evidence_logging_seconds', time.perf_counter()-started, int(time.time()*1000), 0)], params=[], tags=[])
client.set_terminated(args.run_id, status='FINISHED')
actual = client.get_run(args.run_id)
if actual.info.status != 'FINISHED':
    raise ValueError('Tracking completion failed')
for key, value in values.items():
    if actual.data.metrics.get(key) != float(value):
        raise ValueError('Logged metric does not reconcile: ' + key)
write_json(root / 'reports/phase5/tracking_receipt.json', {
    'run_id': args.run_id, 'status': actual.info.status, 'prior_status': prior_status,
    'tracking_store': str(store), 'evaluation_run_id': completion['evaluation_run_id'],
    'results_sha256': file_sha256(root / 'reports/phase5/results.json'),
    'metric_keys_verified': len(values), 'parameter_keys': len(actual.data.params), 'fits': 0,
    'recovered_existing_run': True, 'scope': 'saved aggregates only; no evaluator rerun'})
print('FINISHED local MLflow run ' + args.run_id + '; metrics verified: ' + str(len(values)))
