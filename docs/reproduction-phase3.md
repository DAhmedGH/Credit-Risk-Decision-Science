# Model selection — accepted artifacts and historical reproduction

These are historical phase commands, retained for reproducibility. Run them only
in a separate private historical source/payload copy with its original receipts
and dependency checkpoint. The publication source uses the current pinned lock
and the [standalone scoring workflow](setup.md); it does not ship
all historical execution attachments.

This is the historical Phase 3 checkpoint. All five phases subsequently completed,
Git was initialized, and the final bundle is frozen. Its private backup locations
remain historical evidence dependencies; completed-project scoring and core
reproduction use the portable payload in [Setup and reproduction](setup.md).
Source-bound historical commands require the original accepted source after
audit fixes; the guide below preserves their original checkpoint context.

Phase 3 acceptance passes. The selected base is `xgboost_05_engineered_none`,
selection run `6a0725d18b164582938e0b07b2df6b27`. The complete final bundle is
unfrozen. This guide defaults to **read-only verification and loading**, with no
search, calibration, policy or model refit. See [phase3.md](../reports/phase3.md)
for measured results and `docs/phase4-checkpoint.md` (private historical evidence) for the subsequent calibration/policy stage.

## Accepted locations and identities

- Durable root: `/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime`.
- Intact original: `/tmp/credit-risk-phase3-real-03kpjn82`.
- Earlier backup `phase3-20261008-194353` lacks the final selection; retain it as
  history, but use the newer backup for accepted models.
- Bundles: `artifacts/models/phase3/6a0725d18b164582938e0b07b2df6b27/` beneath
  the durable root. This includes selected/reference development pipelines,
  25 fold pipelines, OOF predictions, summaries and metadata.
- Search evidence: `artifacts/models/phase3/<search-id>/`, compact results:
  `reports/phase3_runs/<run-id>/`, tracking: `mlruns/` beneath that same root.
- Compact copies, selection table, acceptance receipt, preservation inventory
  and accepted source overrides are preserved in the project `reports/` tree.

The preserved backup contains 2,682 regular artifact/provenance/tracking files,
131,298,257 bytes, all byte-equivalent to the original at acceptance. The
preservation inventory SHA and every file SHA/size are in
`reports/phase3_acceptance.json` and `reports/phase3_preservation_inventory.csv`.
This inventory covers the accepted output/tracking/provenance trees and profile
receipt; it does not pretend that linked inputs/source are materialized copies.

The accepted runtime uses Python 3.12.11, sklearn 1.7.2, MLflow skinny 3.3.2,
XGBoost CPU 3.0.5 and one worker/native thread. The accepted lock is
`31e7241f3499567f92579f1381892351dcd433faf219fe8b0be70321937e6b57`;
the accepted code tree is
`bcad5c99614b24044c72f904ce1a73c2552d82528b50d90679478cec3f50a44f`.
Keep the existing `.venv`; no environment recreation is needed. If a later
environment needs installation, use the exact accepted lock rather than upgrading
packages or running completed searches. The original Phase 2 lock remains in
`requirements-phase2.lock`; Phase 1 remains in `requirements-phase1.lock`.

## Verify durable preservation without fits or tests

From the project root:

```bash
.venv/bin/python - <<'PY'
import csv
import hashlib
import json
from pathlib import Path
receipt = json.loads(Path('reports/phase3_acceptance.json').read_text())
root = Path(receipt['durable_root'])
inventory = Path(receipt['preservation_inventory']['path'])
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
assert digest(inventory) == receipt['preservation_inventory']['sha256']
with inventory.open(newline='') as stream:
    rows = list(csv.DictReader(stream))
for row in rows:
    path = root / row['relative_path']
    assert path.is_file() and not path.is_symlink(), path
    assert path.stat().st_size == int(row['bytes']), path
    assert digest(path) == row['sha256'], path
assert len(rows) == receipt['preservation_inventory']['files']
print(f'Verified {len(rows)} durable files; no fit or outcome access.')
PY
```

Full label/workbook checksums can be verified as bytes; this does not authorize
held-out outcome interpretation. Acceptance itself used only development OOF
outcomes, development financial values and label-free assignments. Do not use
`phase3-select` merely to verify acceptance: that command performs new fits.

## Load the exact accepted base and references

This code loads trusted local files directly from the durable backup. It needs
no training database, MLflow lookup or fit:

```bash
.venv/bin/python - <<'PY'
import hashlib
import json
from pathlib import Path
import joblib
root = Path('/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime')
run = '6a0725d18b164582938e0b07b2df6b27'
manifest = json.loads((root / 'reports/phase3_runs' / run / 'manifest.json').read_text())
assert manifest['selected_candidate_id'] == 'xgboost_05_engineered_none'
assert manifest['base_selected'] and not manifest['complete_bundle_frozen']
models = {}
for candidate, paths in manifest['bundles'].items():
    model_path, metadata_path = root / paths['pipeline'], root / paths['metadata']
    def digest(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    assert digest(metadata_path) == manifest['artifacts'][paths['metadata']]
    metadata = json.loads(metadata_path.read_text())
    assert digest(model_path) == metadata['pipeline_sha256']
    assert metadata['training_partition'] == 'development'
    assert metadata['training_rows'] == 18000 and metadata['positive_class'] == 1
    assert metadata['save_load_predictions_match']
    models[candidate] = joblib.load(model_path)
base = models[manifest['selected_candidate_id']]
assert list(base.classes_) == [0, 1]
assert len(base.named_steps['features'].columns) == 32
print('Loaded exact accepted base and four references; no fit.')
# In Phase 4, given X with the versioned named financial predictors:
# from credit_risk.models.pipelines import positive_probability
# p_default = positive_probability(base, X)
PY
```

The selected binary SHA is
`265db2cbe02e88ca7c75c29f39b5c0230a29ba40e4735ea808aea08df4a5e83c`;
metadata SHA is
`1afe8fa4ce63a14e761ebc01d3fa82f5ee269d91d4220ea1b8309a6b915bcd3e`.
Preserve model classes/preprocessing and the `financial-row-v1.1` input formulas.
The references are `dummy_prior`, `logistic_00_engineered_none`,
`random_forest_02_engineered_none` and `xgboost_04_engineered_none`.
All five are already fitted on development only. The model receives named
financial features; IDs and audit fields stay outside predictor matrices.

## Historical MLflow paths and safe restoration

The backup preserves original tracking records. Run and experiment artifact
URIs still point to `/tmp/credit-risk-phase3-real-03kpjn82/mlruns/...`.
A client pointed at the backup can read tracking metrics, but artifact downloads
follow those original absolute URIs. **Do not rewrite metadata or merge stores.**
Direct model loading above works independently of those URIs.

While the original remains intact, its no-fit verification commands are:

```bash
phase3_runtime=/tmp/credit-risk-phase3-real-03kpjn82
for phase3_id in \
  0c41719e0c73482f875a4015477a03c6 \
  e055463d1abd40f3bcdd6a2bd47f82a8 \
  6c2fee1f9e5e4bfeab64e9bcda9ffed6 \
  6a0725d18b164582938e0b07b2df6b27
do
  PYTHONPATH="$phase3_runtime/src" .venv/bin/python -m credit_risk phase3-verify \
    --runtime-root "$phase3_runtime" --run-id "$phase3_id"
done
```

If `/tmp` was cleaned and historical MLflow artifact APIs are needed, from
ordinary WSL restore **only if that original path is absent**:

```bash
.venv/bin/python - <<'PY'
import shutil
from pathlib import Path
backup = Path('/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime')
runtime = Path('/tmp/credit-risk-phase3-real-03kpjn82')
# copytree raises FileExistsError before copying into any existing destination.
shutil.copytree(backup, runtime, symlinks=True)
PY
```

Keep both backup directories. Never copy into an existing runtime or replace
records. The copy retains source/input links to the project, whose hashes must
still agree. Use durable direct loads for Phase 4 rather than depending on a
restored training runtime. Restoration is documented, not performed here.

## Reconstruct immutable accepted source

Backup `src/`, `scripts/`, configuration, lock and data inputs include symlinks
to the project; future project edits can change those links' contents. Exact
accepted source is nevertheless preserved by 36 original materialized files in
backup `provenance/original_code/`, with only three accepted replacements in
project `reports/phase3_source_snapshots/accepted/`. Their reconstruction matches
the accepted 36-file hash manifest and code-tree hash exactly.

If an isolated copy is needed, from the project root:

```bash
.venv/bin/python - <<'PY'
import hashlib
import json
import shutil
from pathlib import Path
from credit_risk.artifacts import json_bytes, sha256_bytes
root = Path('/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime')
manifest = json.loads((root / 'reports/phase3_runs/6a0725d18b164582938e0b07b2df6b27/manifest.json').read_text())
source = Path('/tmp/credit-risk-phase3-accepted-source')
# This must succeed before any override is copied; existing destinations fail.
shutil.copytree(root / 'provenance/original_code', source)
overrides = Path('reports/phase3_source_snapshots/accepted')
for saved, target in [('phase3.py', 'src/credit_risk/phase3.py'),
                      ('__main__.py', 'src/credit_risk/__main__.py'),
                      ('requirements.lock', 'requirements.lock')]:
    shutil.copyfile(overrides / saved, source / target)
actual = {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
          for name in manifest['code_file_hashes']}
assert actual == manifest['code_file_hashes']
assert sha256_bytes(json_bytes(actual)) == manifest['code_tree_sha256']
print('Exact accepted source reconstructed; no fit.')
PY
```

`PYTHONPATH="/tmp/credit-risk-phase3-accepted-source/src" .venv/bin/python ...` can load accepted custom
pipeline classes independently of later project source edits. Do not change
frozen data/split hashes or reinterpret held-out outcomes while checking copies.
The binary/metadata/inventory remain the accepted identities; no reconstruction
changes original records.

## Recorded execution and verification history

The content-addressed plan declares 12 logistic, 12 forest and 24 XGBoost
configurations, including all feature/weight choices, with five frozen folds:
60/60/120 CV fits. The prior LR/forest code/lock identities are deliberately
retained; saved selection `search_reuse_proofs` verifies only the pinned additive
XGBoost dependency and reviewed runner/CLI/lock changes. Original numerical,
feature, loader, preprocessing and CV code remained identical. No duplicate
search was run for the environment transition.

Reported WSL ordinary-WSL commands completed bootstrap, profile, XGBoost search,
selection and verification. The final enabled suite was:

```bash
CREDIT_RISK_SQL_TEST=1 .venv/bin/python -m pytest -q -p no:cacheprovider
```

Result **111 passed in 49.88s, no skips**; PostgreSQL ready at 127.0.0.1:55432.
Bootstrap passed 110 tests with SQL disabled, validated import/fit/save/load and
updated the lock. These tests were not repeated during acceptance. Independent
review reloaded/re-scored saved models without fitting; measured evidence and
limits are in [validation-phase3-acceptance.md](validation-phase3-acceptance.md).

Historical blocked-runtime instructions remain in
[reproduction-phase3-history.md](reproduction-phase3-history.md).
They are history, not a request to rerun completed searches. A fresh scientific
reproduction requires a separate explicit task and separate output identities.
Historical Phase 3 training records have null Git commits; content hashes
supply their provenance. No Git history, Docker resources or environments were
replaced for acceptance.
