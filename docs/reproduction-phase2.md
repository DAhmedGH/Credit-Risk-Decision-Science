# Reproduce Phase 2

These are historical phase commands, retained for reproducibility. Run them only
in a separate private historical source/payload copy with its original receipts
and dependency checkpoint. The publication source uses the current pinned lock
and the [standalone scoring workflow](reproduction-phase5.md); it does not ship
all historical execution attachments.

This guide records the historical Phase 2 checkpoint. Its 58-pin lock is now
`requirements-phase2.lock`; the maintained completed-project lock has 72 pins.
Use [Phase 5 reproduction](reproduction-phase5.md) for current scoring and exact
accepted-source replay. Git and later-phase status below describe this checkpoint.

Phase 2 acceptance is complete. The measured parent run is
`49c7344ca89440e9a458fa2849d9122d`; all nine children are FINISHED. The user ran
bootstrap, input validation, real baselines and the enabled full suite
(**79 passed in 39.26s; no skips**) from ordinary WSL. Acceptance then inspected
saved artifacts and rescored trusted pipelines without refitting. See
[the measured report](../reports/phase2.md),
[acceptance receipt](../reports/phase2_acceptance.json) and
[independent review](validation-phase2-acceptance.md).

Completed experiments need not be rerun to use this checkpoint. The commands below
are reproduction/manual verification instructions, not additional execution
claims. They stop within Phase 2.

## Existing environment and locked dependencies

Use the existing project-local Python 3.12 `.venv`. The validated
`requirements.lock` contains **58 installed pins**, including scikit-learn 1.7.2
and mlflow-skinny 3.3.2. The original 11-pin Phase 1 lock is preserved as
`requirements-phase1.lock`. Original dependency DNS failures are historical;
the reported WSL bootstrap resolved and verified the expanded closure.

For installation into an already prepared project Python 3.12 environment,
reuse the accepted lock rather than resolving new versions:

```bash
set -euo pipefail
cd '/mnt/c/users/danieal/desktop/credit risk project'
export UV_CACHE_DIR="$PWD/.cache/uv"
.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12)'
.tools/bin/uv pip install --python .venv/bin/python -r requirements.lock
.tools/bin/uv pip install --python .venv/bin/python --no-deps --no-build-isolation -e .
.tools/bin/uv pip check --python .venv/bin/python
.venv/bin/python scripts/environment_smoke.py
.venv/bin/python scripts/phase2_smoke.py
```

The tiny synthetic smoke exercises import/fit/save/load and explicit local
tracking; it does not read customer data or establish predictive quality. It is
separate from the real baseline experiment. Do not recreate `.venv`, touch other
Python installations, or overwrite `requirements-phase1.lock`.

The originally requested complete bootstrap remains available:

```bash
bash scripts/bootstrap_phase2.sh
```

It resolves a temporary closure, installs only in `.venv`, runs smoke/lint/tests,
and only then archives the original lock if absent and writes the validated
expanded lock. It verifies that the archive retains the original Phase 1 hash.
The completed current environment does not need another bootstrap for acceptance.
Any future deliberate dependency change must retain compatibility checks and
record changed pins; historical Phase 1 receipts keep their original lock hash.

## Exact development workflow

The existing Phase 1 exports are sufficient; do not rerun Phase 1 `reproduce`
for acceptance. Its historical evidence overwrite guard can reject the expanded
lock identity; preserve canonical reports (see the Phase 1 guide).
No database service, download,
workbook decoding or split regeneration is needed for these two commands:

```bash
set -euo pipefail
cd '/mnt/c/users/danieal/desktop/credit risk project'
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
.venv/bin/python -m credit_risk baseline-inputs --config configs/phase2.toml
.venv/bin/python -m credit_risk baselines --config configs/phase2.toml
```

`baseline-inputs` verifies evidence hashes, exact development coverage,
financial-profile fingerprints and frozen fold integrity. It reports 18,000
rows, five folds of 3,600, no predictive fit and no held-out outcome
interpretation. The loader streams CSV row strings for ID routing and converts
only development financial/outcome values; audit attributes are not opened.
The workbook is byte-hashed without decoding. Label routing is recorded in the
exposure log before loading.

`baselines` performs the nine declared comparisons and **45 sequential fits**,
with seed 42, one forest worker and one BLAS/OpenMP thread. It uses no search,
resampling, calibration, all-development refit or champion selection. Repeated
executions create new run IDs and preserve earlier outputs. Expect different
wall times and recorded code hashes if maintained code/configuration changes.
The accepted run took 204.68 seconds locally; that is not a runtime promise.

The CLI returns the parent ID, nine child IDs, compact report path,
`runtime_validation_passed` and `champion_frozen=false`. Nonconverged logistic
folds cause a nonzero exit after preserving their results; inspect their warnings
before making a bounded, documented correction. The accepted run had no warnings
and all 20 logistic fits converged in 67–131 of at most 2,000 iterations.

## Exact manual lint and integration checks

To verify the MLflow correction first, then lint and the complete enabled suite:

```bash
set -euo pipefail
cd '/mnt/c/users/danieal/desktop/credit risk project'
.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_baseline_tracking.py::test_real_local_mlflow_tracks_fixture_runs_and_ignores_remote_environment
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_baseline_tracking.py
.venv/bin/ruff check . --no-cache
python3 scripts/dev_db.py up
CREDIT_RISK_SQL_TEST=1 .venv/bin/python -m pytest -q -p no:cacheprovider
```

The project-only PostgreSQL helper verifies instance ownership and uses ignored
`.env`; the user reports 127.0.0.1:55432 for the current instance. No credentials
should be printed or committed. SQL fixture tests use rollback to preserve real
project records. Services and enabled tests were not rerun during acceptance.
Without the service, the fixture-only command is
`.venv/bin/python -m pytest -q -p no:cacheprovider`; its live SQL skip must be
reported rather than described as a complete enabled run.

The real focused tracking test executes the synthetic workflow **twice against
the same local store**, retrieves parent/child runs, downloads artifacts and
checks FINISHED statuses with a remote `MLFLOW_TRACKING_URI` present. Additional
real-store tests verify legacy preservation, ordinary FAILED statuses and
retention of the original exception if cleanup also fails. No real customer
outcomes are analyzed by these synthetic tests.

## MLflow layout and legacy recovery

Installed/pinned MLflow skinny 3.3.2 can discover top-level directories as
experiments. The old custom `mlruns/artifacts/<run-id>/artifacts` root therefore
created a second run-ID directory without run metadata, which could shadow
`mlruns/<experiment-id>/<run-id>/meta.yaml` during termination/retrieval.
New experiments use MLflow's default layout, with run metadata and its sibling
`artifacts/` directory under `mlruns/<experiment-id>/<run-id>/`. Every client
receives the explicit local URI, so a remote tracking environment cannot redirect
logging.

Changing the experiment-creation call cannot change an existing experiment's
stored artifact location. The fixed workflow refuses a nondefault location
before creating new runs. Preserve every old run and artifact. Copy
`configs/phase2.toml` to `configs/phase2-layout-v2.toml` and choose an unused
experiment name in the copy, for example:

```toml
experiment = "credit-risk-phase2-development-baselines-layout-v2"
```

Then, only when another Phase 2 execution is actually needed:

```bash
.venv/bin/python -m credit_risk baselines --config configs/phase2-layout-v2.toml
```

The new experiment can coexist with preserved legacy data. Historical discovery
can still fail, and malformed-directory warnings may persist. Inspect old files
in place; this correction neither migrates paths nor fabricates metadata/statuses.
A historical-store migration would be a separate recovery operation. Failure
receipt/status cleanup is best effort: cleanup errors attach notes to the
original exception rather than masking it; an unmodifiable run can remain RUNNING.
The accepted run above uses the supported layout and is fully FINISHED.

## Artifacts and interpretation

| Location | Contents |
| --- | --- |
| `mlruns/` | Ignored local metadata and logged parent/child artifacts |
| `artifacts/models/phase2/<parent-run-id>/` | Ignored execution context, OOF CSVs, 45 fold pipelines, names/parameters/weights/warnings and customer-level development errors |
| `reports/phase2_runs/<parent-run-id>/` | Compact comparison, fold metrics, controlled differences, majority hard reference, aggregate diagnostics, report and provenance manifest |
| `reports/phase2_acceptance.json` | Read-only numerical/fitted-state acceptance evidence for the accepted run |

Each variant's `oof_predictions.csv` preserves customer ID, frozen fold,
fingerprint, development outcome and class-1 probability. The workflow reloads
OOFs to verify exact once-only coverage and metric agreement at 1e-12 tolerance.
Fold means/sample SDs (`ddof=1`) and pooled OOF metrics are explicitly distinct.
Pooled AP/ROC-AUC need not equal their fold means. The 0.5 diagnostic threshold
is not a lending policy; majority hard predictions are a separate reference.

The manifest records all hashes, resolved configuration/parameters, dependencies,
seed, timings and run IDs. Git is unavailable in the original workspace, so commit
is explicitly null and maintained code/configuration has a content hash. No
remote CI run is claimed. Initialize/inspect/commit from ordinary WSL when
available, preserving ignores for raw/customer data, runtime stores and secrets.
Only trusted local serialized pipelines should be loaded; these CV fold models
are not a frozen champion bundle.

Phase 2 is accepted. Future XGBoost, bounded tuning and champion selection belong
to the subsequent **Phase 3** modeling stage; none was implemented or executed for acceptance.
