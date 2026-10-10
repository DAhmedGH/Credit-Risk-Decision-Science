# Reproduce Phase 3

These are historical phase commands, retained for reproducibility. Run them only
in a separate private historical source/payload copy with its original receipts
and dependency checkpoint. The publication source uses the current pinned lock
and the [standalone scoring workflow](setup.md); it does not ship
all historical execution attachments.

Use the accepted Phase 2 environment and exports. These commands stop at base
selection and development-only refits. Phase 4 is a separate task. Current
execution evidence and remaining blockers are in [phase3.md](../reports/phase3.md).

The original execution environment cannot resolve PyPI and mounts this project read-only. Editor
changes are available; shell-installed dependencies, persistent training outputs
and Git initialization require ordinary WSL. Do not recreate `.venv` or change
other Python/Docker resources. The CPU wheel is published by the XGBoost project:
[3.0.5 distribution](https://pypi.org/project/xgboost-cpu/3.0.5/) and
[versioned API](https://xgboost.readthedocs.io/en/release_3.0.0/python/python_api.html).
This addition is pinned for compatibility checking, rather than tracking latest
releases. `requirements.lock` still represents the accepted Phase 2 environment
until the following bootstrap succeeds.

## Setup and smoke

```bash
set -euo pipefail
cd /path/to/private/credit-risk-historical
export UV_CACHE_DIR=/tmp/credit-risk-phase3-uv
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
bash scripts/bootstrap_phase3.sh
```

Bootstrap resolves the existing exact pins plus `xgboost-cpu==3.0.5`, installs in
the existing Python 3.12 `.venv`, checks dependency consistency, runs synthetic
Phase 2/3 fit/save/load smoke, Ruff and fixture tests. Only then does it archive
the accepted lock as `requirements-phase2.lock` and publish the resolved
`requirements.lock`. `requirements-phase1.lock` is preserved. The synthetic
Phase 3 smoke performs two fits; these do not consume the real search budget.
If this fails, retain the failure and do not claim compatibility or replace a
lock manually. The live PostgreSQL test may skip here; enable it separately below.

## Resume the verified completed searches

**Do not rerun logistic or forest for this continuation.** Recovery verified
both 60-fit searches, all 26 FINISHED MLflow records, all artifacts and saved
OOF metrics. No search was interrupted or is still running. Their IDs are:

- Logistic: `0c41719e0c73482f875a4015477a03c6`.
- Forest: `e055463d1abd40f3bcdd6a2bd47f82a8`.

The original plan has spent 120 of 240 real CV fits. XGBoost's 120 remain;
its separate five-fit profile and two-fit synthetic smoke have not run. Run
the bootstrap above from ordinary WSL first. Preserve/restore the temporary
runtime using the archive instructions below if needed, then synchronize its
lock with the validated project lock:

```bash
phase3_runtime=/tmp/credit-risk-phase3-real-03kpjn82
test -d "$phase3_runtime/provenance/original_code"
.venv/bin/python - <<'PY'
from pathlib import Path
runtime = Path('/tmp/credit-risk-phase3-real-03kpjn82')
validated = Path('requirements.lock').read_bytes()
lock = runtime / 'requirements.lock'
if lock.read_bytes() != validated:
    lock.write_bytes(validated)
PY
PYTHONPATH="$phase3_runtime/src" .venv/bin/python -m credit_risk phase3-verify \
  --runtime-root "$phase3_runtime" --run-id 0c41719e0c73482f875a4015477a03c6
PYTHONPATH="$phase3_runtime/src" .venv/bin/python -m credit_risk phase3-verify \
  --runtime-root "$phase3_runtime" --run-id e055463d1abd40f3bcdd6a2bd47f82a8
PYTHONPATH="$phase3_runtime/src" .venv/bin/python -m credit_risk phase3-profile \
  --runtime-root "$phase3_runtime"
```

Inspect the measured profile before launching the final XGBoost search.
Preserve the existing declared ranges/selection rule for this resume. A changed
plan is a different experiment and cannot silently reuse this declaration.
The profile lives in the runtime's `reports/phase3_profile.json`.

```bash
PYTHONPATH="$phase3_runtime/src" .venv/bin/python -m credit_risk phase3-plan \
  --runtime-root "$phase3_runtime"
PYTHONPATH="$phase3_runtime/src" .venv/bin/python -m credit_risk phase3-search \
  --runtime-root "$phase3_runtime" --family xgboost
```

The expected plan SHA remains
`9927448bbd9535fec4922a39d218ee745b77156e73e42ee071c05f9669d9c88a`.
Substitute the actual new XGBoost parent ID returned above:

```bash
PYTHONPATH="$phase3_runtime/src" .venv/bin/python -m credit_risk phase3-select \
  --runtime-root "$phase3_runtime" --search-runs \
  0c41719e0c73482f875a4015477a03c6 e055463d1abd40f3bcdd6a2bd47f82a8 XGBOOST_RUN_ID
PYTHONPATH="$phase3_runtime/src" .venv/bin/python -m credit_risk phase3-verify \
  --runtime-root "$phase3_runtime" --run-id XGBOOST_RUN_ID
PYTHONPATH="$phase3_runtime/src" .venv/bin/python -m credit_risk phase3-verify \
  --runtime-root "$phase3_runtime" --run-id SELECTION_RUN_ID
```

The per-command `PYTHONPATH` executes the exact source hashed inside that
runtime, including after an archive restores materialized snapshots. Do not
export it globally for project fixture tests. If old runtime source predates
the resume interface, retain `provenance/original_code` and copy the reviewed
current `src/` into that runtime before continuing; never change financial input
or frozen-split bytes. The archive created after this recovery already includes
the resume interface.

Reuse permits only the pinned XGBoost addition and reviewed runner/CLI/lock
changes. It requires unchanged numerical/feature/loader/search code, inputs,
plan/config, Python/platform and every existing distribution version; the new
full lock must match actual installed pins. Original runner snapshots protect
selection, data routing and final-fit statements. A selection receipt records
original search identities, the current refit environment and the exact allowed
differences. Unexpected differences stop selection rather than launch a rerun.

## Fresh reproduction only: profile, declare and search

The following three-family commands reproduce the study from scratch; they
are **not** the continuation procedure for the completed runs above.

```bash
.venv/bin/python -m credit_risk phase3-profile --config configs/phase3.toml
.venv/bin/python -m credit_risk phase3-plan --config configs/phase3.toml
.venv/bin/python -m credit_risk phase3-search --family logistic --config configs/phase3.toml
.venv/bin/python -m credit_risk phase3-search --family random_forest --config configs/phase3.toml
.venv/bin/python -m credit_risk phase3-search --family xgboost --config configs/phase3.toml
```

Inspect `reports/phase3_profile.json` after profiling: five fixed-fold, 30-tree
development fits with measured mean/SD fit and prediction times, serialization
checks, and an approximate linear tree-count runtime estimate. It is not a
guaranteed runtime bound. One worker and one native thread prevent
oversubscription. The proposed final ranges use 100–300 trees and depth 2–4.
If measured runtime requires reducing ranges, edit the bounded config before
running final searches, rerun the matching profile and declaration, then run
all families under that identity. Do not optimize ranges in response to held-out
outcomes. Profiling has its own MLflow run and does not consume final candidates.

The plan pairs each hyperparameter setting across raw/combined predictors ×
unweighted/balanced fit objectives. Three logistic settings produce 12 candidate
configurations; three forest settings produce 12; six XGBoost settings produce
24. These total **60/60/120 final CV fits**, no automatic refits. Feature and
weight variants are included in those totals. Spaces, sampled settings, seed,
selection tolerances and concurrency are saved before fitting in
`artifacts/phase3_plans/<sha256>.json` and copied into each compact run directory.
Core search does not use early stopping or an external eval_set.

Record the three returned parent run IDs. Fresh runs share plan/input/code/lock
identities. Reusing original-runtime results follows the explicit compatibility
procedure above; preserve their original contexts and tracking store. A fresh
reproduction is separate execution evidence, not budget that must be spent
again merely to resume.

## Select and preserve development-fitted models

Substitute the three actual run IDs returned above (hexadecimal, 32 characters):

```bash
.venv/bin/python -m credit_risk phase3-select --config configs/phase3.toml \
  --search-runs LOGISTIC_RUN_ID FOREST_RUN_ID XGBOOST_RUN_ID
```

Selection considers every candidate: AP within 0.01 of the best, then log loss
within 0.001 of the minimum eligible value, then the prespecified simplicity
order recorded in D014/the plan. Neither tolerance is a significance test.
The run stores the full decision and eligible sets in `selection.json`.
Partial, corrupted or scientifically incompatible searches fail before a base
is selected. Narrow additive-XGBoost reuse preserves original provenance and
does not change the selection rule.

The selected base, each family's AP leader and a prior dummy are deduplicated
and explicitly identified. OOF reconstruction and development refits are
separate from search CV fit counts and are reported in the selection manifest.
Each model has `development_pipeline.joblib` plus `metadata.json`, with the
allowlist, encoded feature names, class mapping, parameters, training-ID hash,
input/code/environment hashes and save/load agreement. These are trusted local
artifacts only. The complete calibrated/policy bundle remains unfrozen.

## Verification and local Git

For each search parent and the selection parent, substitute its actual ID:

```bash
.venv/bin/python -m credit_risk phase3-verify --config configs/phase3.toml --run-id RUN_ID
.venv/bin/python scripts/phase2_smoke.py
.venv/bin/python scripts/phase3_smoke.py
.venv/bin/ruff check . --no-cache
.venv/bin/python -m pytest -q -p no:cacheprovider
python3 scripts/dev_db.py up
CREDIT_RISK_SQL_TEST=1 .venv/bin/python -m pytest -q -p no:cacheprovider
```

The project database helper verifies instance ownership; SQL tests use rollback.
Do not report the enabled suite as passed if Docker access or SQL tests fail.
Independent scientific review must inspect actual XGBoost/profile, search,
selection and serialized-model evidence before the Phase 3 gate passes.


## Artifact interpretation and Phase 4 checkpoint

`reports/phase3_runs/<run-id>/` contains compact candidate/fold tables, full
sklearn results, per-candidate MLflow IDs, plans, contexts and hash manifests.
`artifacts/models/phase3/<run-id>/` contains local execution outputs and later
development-fitted bundles. `mlruns/` uses the accepted explicit local FileStore
layout; remote `MLFLOW_TRACKING_URI` cannot redirect it. Fold sample SDs use
`ddof=1`; pooled OOF scores have separate names and do not replace fold means.
Search scoring times include metric computation; measured inference times are
reported separately. Any development-selected scores can be optimistic from
tuning and are not final-test performance.

After the complete Phase 3 gate passes, Phase 4 may load the fixed
development-fitted base and references, fit calibration mappings using only
calibration rows, and select calibration/policy choices on policy validation.
Do not refit the base on those rows. No calibration, policy, SHAP or final-test
evaluation is part of these commands.

## Preserve the original-runtime partial runtime

The real partial run root is `/tmp/credit-risk-phase3-real-03kpjn82`. Compact
results are copied into this repository; customer OOFs and its separate MLflow
store remain temporary. Before cleaning `/tmp`, run from ordinary WSL:

```bash
set -euo pipefail
cd /path/to/private/credit-risk-historical
mkdir -p artifacts/runtime
test ! -e artifacts/runtime/phase3-preserved-03kpjn82.tar.gz
tar --dereference -C /tmp -czf artifacts/runtime/phase3-preserved-03kpjn82.tar.gz \
  credit-risk-phase3-real-03kpjn82
```

The ignored archive snapshots linked source/configs/frozen inputs as well as
outputs, without altering the originals. It preserves this separate FileStore;
do not merge it into the existing `mlruns/`. FileStore artifact URIs retain the
original absolute runtime path. If it has been removed, restore to that same
path before using the historical verification commands:

```bash
test ! -e /tmp/credit-risk-phase3-real-03kpjn82
tar -C /tmp -xzf artifacts/runtime/phase3-preserved-03kpjn82.tar.gz
```

At the historical checkpoint, this archive had **not** been created because project
shell writes are blocked. The archive and restored runtime are local artifacts,
not source-control content or a completed Phase 3 model bundle.
