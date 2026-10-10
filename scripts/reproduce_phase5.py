"""Fresh-environment frozen delivery reproduction; writes only to a new output directory.

Record the unchanged reproduction exposure in the project log before running.
No searches, selection, model fits, calibrator fits or policy changes occur.
"""
if not __debug__:
    raise SystemExit('Reproduction requires assertions enabled; remove -O/PYTHONOPTIMIZE')

import argparse
import importlib.metadata
import json
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd
from credit_risk.artifacts import file_sha256, write_csv, write_json
from credit_risk.data.workbook import load_workbook
from credit_risk.data.schema import validate_records
from credit_risk.features import build_features, PREDICTORS
from credit_risk.splits.allocation import allocate_records
from credit_risk.phase5 import preflight, summarize, validate_saved
from credit_risk.inference import score_file

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,default=Path('.'))
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
root=args.root.resolve()
args.output.mkdir(parents=True,exist_ok=False)
started=time.perf_counter()
bundle,assignments,evidence=preflight(root)
loaded=load_workbook(root/'data/raw/default of credit card clients.xls')
validated=validate_records(loaded.records)
assert len(loaded.records)==len(validated.accepted)==30000
assert not validated.rejected
rows,summary=allocate_records(validated.accepted,loaded.sha256,seed=42)
write_csv(args.output/'split_manifest.csv',rows,
          ('client_id','partition','fold','fingerprint','seed','source_sha256'))
assert file_sha256(args.output/'split_manifest.csv')==evidence['integrity']['input_hashes']['artifacts/split_manifest.csv']
export=pd.read_csv(root/'data/processed/financial_features_v1.csv').set_index('client_id')
maximum=0.0
for record in validated.accepted:
    generated=build_features(record)
    actual=export.loc[record['client_id']]
    for key in PREDICTORS:
        a,b=generated[key],actual[key]
        if a is None:
            assert pd.isna(b)
        else:
            assert np.isclose(a,b,atol=1e-10,rtol=1e-12)
            maximum=max(maximum,abs(a-b))
runtime=root/'artifacts/runtime/phase5/final_evaluation'
receipt=json.loads((runtime/'completion.json').read_text())
assert file_sha256(runtime/'predictions.csv')==receipt['predictions_sha256']
frame=pd.read_csv(runtime/'predictions.csv',float_precision='round_trip')
validate_saved(frame,pd.read_csv(runtime/'decisions.csv'),assignments,bundle.policy)
result=summarize(frame,bundle.policy)
original=json.loads((root/'reports/phase5/results.json').read_text())
assert result['model_metrics']==original['model_metrics']
assert result['policy_metrics']==original['policy_metrics']
assert result['intervals']==original['intervals']
assert result['bootstrap']==original['bootstrap']
scoring=score_file(root/'artifacts/models/phase4/9ca62eca2665438c9c97b4889413acfa/freeze_manifest.json',
                   root/'examples/scoring_batch.csv',args.output/'score')
expected=pd.read_csv(root/'artifacts/runtime/phase5/example_score/scored.csv',float_precision='round_trip')
actual=pd.read_csv(args.output/'score/scored.csv',float_precision='round_trip')
pd.testing.assert_frame_equal(actual,expected,check_exact=False,atol=1e-12,rtol=0)
write_json(args.output/'reproduction.json',{'status':'PASS','python':sys.version,
           'freeze_sha256':evidence['freeze_sha256'],'bundle_sha256':evidence['bundle_sha256'],
           'source_code_hashes':evidence['code_hashes'],'lock_sha256':evidence['lock_sha256'],
           'source_rows':30000,'split_exact':True,'feature_max_absolute_difference':maximum,
           'feature_tolerance':{'absolute':1e-10,'relative':1e-12},
           'saved_metrics_intervals_exact':True,'bootstrap_plan_hash':result['bootstrap']['resample_indices_sha256'],
           'scoring_absolute_tolerance':1e-12,'batch':scoring,'fits':0,
           'runtime_seconds':time.perf_counter()-started,
           'dependencies':{line.strip().split('==')[0]:importlib.metadata.version(line.strip().split('==')[0])
                           for line in (root/'requirements.lock').read_text().splitlines()
                           if '==' in line and not line.startswith('#')}})
print('PASS: fresh source/features/splits, saved evaluation intervals and isolated batch reproduction')
