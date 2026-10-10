# Phase 4 reproduction and durable loading

These are historical phase commands, retained for reproducibility. Run them only
in a separate private historical source/payload copy with its original receipts
and dependency checkpoint. The publication source uses the current pinned lock
and the [standalone scoring workflow](reproduction-phase5.md); it does not ship
all historical execution attachments.

This guide records the Phase 4 acceptance checkpoint. Phase 5 subsequently
completed. Use [Phase 5 reproduction](reproduction-phase5.md) for the completed
project, trusted payload restoration, and exact accepted-source replay after
the audit fixes. The frozen artifacts and no-fit bundle identity below are
unchanged; historical phase/Git/dependency status retains its original context.

**Phase 4 exit gate: PASS.** Run `9ca62eca2665438c9c97b4889413acfa` has a
complete, independently reviewed pre-test freeze. Final-test outcomes remain
unevaluated. Load the saved bundle for reproduction; no retraining or resume
is needed.

## Exact frozen identities

Durable root:
`/mnt/c/Users/Danieal/Desktop/Credit Risk Project/artifacts/models/phase4/9ca62eca2665438c9c97b4889413acfa/`.
The lowercase workspace spelling identifies the same directory. All 106
hashed artifacts are regular local files; loading needs no original `/tmp`
runtime, Phase 3 backup, training database or outcomes.

| Artifact or context | SHA-256 |
| --- | --- |
| Freeze content identity | `89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b` |
| Freeze manifest file | `0cd8c5c63e90ffc159acfa5fb63d10affeda015f885171e3bde9b4c08402e6f1` |
| Probability bundle | `45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd` |
| Original selected pipeline | `265db2cbe02e88ca7c75c29f39b5c0230a29ba40e4735ea808aea08df4a5e83c` |
| Report definitions | `d0fcb5f0b2528dbd281693eedaa1d0b89d937f340ae91d1fff50a56c1fc40e32` |
| Frozen canonical review receipt | `7e8b2e4c2f402ff9dd548128a841d08635b64f584c16fa6796275a6a3c70d29e` |
| Original project review receipt | `829fc9e83f54aa31c62e5777b14bc0c4d2c2874e2d52e9c736747a4385228ff5` |
| Independent review document | `8dcc6160a4d640f8fb8e0ab9078a068e7946c368a21a259f1d8c254029b70afc` |
| Completion source tree | `fe44551d459c780b1ee2cce011aecb35ff1c54601ed2fb198f5be620098f2885` |
| Current requirements lock | `af2037d68e8508c120ff7e70fa2c4d43720f309839230b88db106703479668d8` |
| Archived Phase 3 lock | `31e7241f3499567f92579f1381892351dcd433faf219fe8b0be70321937e6b57` |

All 59 accepted lock pins remain unchanged in the completed 71-pin lock.
SHAP 0.48.0 and Matplotlib 3.10.6 additions passed the reported WSL compatibility
smoke. The existing isolated Python 3.12.11 environment is compatible.
No fresh-container or remote CI execution is claimed.

The original Phase 3 selection is `6a0725d18b164582938e0b07b2df6b27`,
candidate `xgboost_05_engineered_none`. The bundle preserves its
development-fitted preprocessing and 100-tree unweighted XGBoost, raw
identity probability mapping, feature schema, provenance, four accepted
references, policies and sensitivity definitions. Calibration challengers and
each of the five original pipelines/metadata are separately hash-bound.

## Verified no-fit loading command

Run from the project root using the frozen completion source. This loading
pattern passed after finalization. The guard verifies manifest identity,
all 106 file hashes, required artifacts and independent review binding
before unpickling trusted local artifacts. It reads no outcomes and fits nothing.

```bash
cd '/mnt/c/Users/Danieal/Desktop/Credit Risk Project'
phase4_bundle="$PWD/artifacts/models/phase4/9ca62eca2665438c9c97b4889413acfa"
PYTHONPATH="$phase4_bundle/completion_source/src" .venv/bin/python - <<'PY'
import json
from pathlib import Path
from credit_risk.artifacts import file_sha256
from credit_risk.models.bundle import load_frozen_bundle

root = Path('artifacts/models/phase4/9ca62eca2665438c9c97b4889413acfa')
path = root / 'freeze_manifest.json'
assert file_sha256(path) == '0cd8c5c63e90ffc159acfa5fb63d10affeda015f885171e3bde9b4c08402e6f1'
manifest = json.loads(path.read_text())
assert manifest['freeze_sha256'] == '89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b'
bundle = load_frozen_bundle(path)
assert manifest['complete_bundle_frozen']
assert manifest['independent_review_status'] == 'PASS'
assert manifest['status'] == 'FROZEN'
assert len(manifest['artifacts']) == 106
assert file_sha256(root / 'probability_bundle.joblib') == '45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd'
assert bundle.mapping == 'raw'
assert bundle.probability_estimator is bundle.base
assert bundle.model_metadata['positive_class'] == 1
assert bundle.model_metadata['integrity'] == manifest['integrity']
assert set(bundle.references) == {'dummy_prior', 'logistic_00_engineered_none',
    'random_forest_02_engineered_none', 'xgboost_04_engineered_none',
    'xgboost_05_engineered_none'}
print('PASS: complete frozen bundle loaded; no fitting or outcome access.')
PY
```

All original reference binaries also loaded successfully in acceptance.
Their paths are `accepted_models/<candidate>/development_pipeline.joblib`.
[Phase 3 exact loading](reproduction-phase3.md#load-the-exact-accepted-base-and-references)
remains available. Bundle and standalone model metadata have complementary
schemas: shared integrity/positive-class fields agree; the bundle records
candidate/reference identities, while the standalone file records mapping
and partition scopes. Whole-dictionary equality is not their contract.

## Durable layout and authoritative status

```text
artifacts/models/phase4/9ca62eca2665438c9c97b4889413acfa/
  probability_bundle.joblib
  calibration_variants.joblib
  accepted_models/<candidate>/development_pipeline.joblib
  accepted_models/<candidate>/metadata.json
  feature_schema.json
  policy.json
  model_metadata.json
  model_card.md
  calibration_fit_evidence.json
  serialization_evidence.json
  report_definitions.json
  policy_predictions.npz
  explanations/
  source/                         # original core execution snapshot
  completion_source/              # reviewed completion snapshot
  checkpoint.json                 # historical pre-seal state
  review.json
  review.md
  freeze_manifest.json            # complete, authoritative freeze
```

`reports/phase4_latest.json` records complete_bundle_frozen=true and no
blockers. Its identity matches runtime and compact final freeze manifests.
Aggregate tables/reliability/global/dependence figures are under
`reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/`. Local cases remain
in the durable explanation directory. The historical checkpoint, compact
`manifest.json` and original MLflow core evidence retain pre-seal flags;
final status comes from `freeze_manifest.json` and the latest receipt.
Do not resume or finalize the completed run again.

## Execution attribution and completed finalization

These commands/results were reported from WSL execution. Acceptance did not
re-execute them as verification or claim their execution:

```bash
bash scripts/bootstrap_phase4.sh
.venv/bin/python -m credit_risk.phase4 resume --run-id 9ca62eca2665438c9c97b4889413acfa
python3 scripts/dev_db.py up
CREDIT_RISK_SQL_TEST=1 .venv/bin/python -m pytest -q -p no:cacheprovider
.venv/bin/ruff check . --no-cache
```

Bootstrap passed synthetic calibration/TreeSHAP/plot/save-load smoke and
182 tests with one SQL skip. Resume completed real explanations without
new base/mapping fits. Project PostgreSQL started at 127.0.0.1:55432.
The SQL-enabled suite passed **183 tests in 54.31s with zero skips**;
Ruff passed. Exact invocation timestamps were not supplied.
[User evidence](../reports/phase4_user_verification.json) preserves attribution.
Prior DNS/SQL failures remain in D019,
[historical review](validation-phase4-blocked.md) and archived reports; actual
user execution and completed artifacts resolve them.

Acceptance checked identities, installed/locked pins, actual artifacts and
figures, and obtained [independent review](validation-phase4-complete.md).
The receipt binds the exact 104-artifact inventory
`4de2c397ec4ad8659b6da9a4dd7cda9d58a9c57474ecd3c743dc0a5411ea4e2a`.
Review independently reproduced all 88 policy rows, probability metrics,
all 1,000 margins and 14 exact SHAP rows. No fitting or full suite was repeated.

The unchanged guarded finalizer ran successfully:

```bash
PYTHONPATH='/mnt/c/users/danieal/desktop/credit risk project/src' \
  .venv/bin/python -m credit_risk.phase4 finalize \
  --run-id 9ca62eca2665438c9c97b4889413acfa \
  --review-receipt reports/phase4_review_receipt.json
```

The lowercase source path and equivalent checkpoint.compact_dir alias were
used because that workspace spelling was writable in the acceptance shell.
Same-file checks passed; only the un-hashed operational directory path changed.
The original checkpoint was archived, and all reviewed hashes and completion
context remained unchanged. D020 records the correction. No model, mapping,
cutoff, source code or guard changed.

Finalization added hashed review receipt/document, producing 106 frozen files.
Separate post-seal guard/load checks passed.
[Acceptance evidence](../reports/phase4_acceptance.json) records identities.
The finalizer serializes the receipt as canonical sorted JSON: source and runtime
receipt values agree exactly, but their file hashes differ with formatting.
The source review document is copied byte-for-byte into the frozen runtime.
Scratch verification mistakes and the stopped documentation-shell incident
are disclosed in D022; they produced no scientific artifact change.

Phase 4 is complete. `docs/phase5-checkpoint.md` (private historical evidence) describes later
work. Final evaluation, intervals, batch delivery and monitoring remain unstarted.
