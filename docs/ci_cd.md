# Testing and CI

Testing protects data contracts, split isolation, frozen-model integrity and
public-command behavior. Fixture checks are available from a fresh public clone;
SQL integration and historical scientific reproduction have separate dependencies.
The configured workflow does not deploy a service.

## Workflow boundaries

The [GitHub Actions workflow](../.github/workflows/ci.yml) runs on pushes and pull
requests. Its single job uses Ubuntu and Python 3.12, with an isolated
PostgreSQL 16 service on port 55432 and explicit fixture credentials.

| Step | Validation | Execution boundary |
| --- | --- | --- |
| Locked environment | Install `requirements.lock` and local package without dependency resolution | Downloads dependencies; no real dataset |
| Import/serialization smoke | `scripts/environment_smoke.py` | Synthetic/structural setup evidence |
| Modeling smoke | `scripts/phase2_smoke.py` | Tiny synthetic fit/save/load and temporary local MLflow |
| Explanation smoke | `scripts/phase4_smoke.py` | Synthetic calibration, TreeSHAP, plot and save/load |
| Ruff and pytest | Maintained code and fixture behavior | No real-data searches or final-test evaluation |
| Isolated SQL fixtures | Set project/lifecycle identity; enable `tests/test_database.py` | Writes synthetic fixture rows in rollback transactions |

The SQL step sets `credit_risk.project='credit-risk-decision-science'` and
`credit_risk.lifecycle='disposable-development'` on its own database before tests.
Default local pytest skips live SQL unless explicitly enabled. CI's preliminary
pytest and separate SQL file are distinct invocations; their counts are not one
combined run. No external credentials, routine dataset acquisition or scientific
training are required. The Phase 4 smoke's historical receipt dependency was
repaired, and successful remote runs were subsequently observed for the pushed
repair and the following README update. See [observed status](#observed-github-status).

## Observed GitHub status

GitHub's public API was checked over certificate-verified HTTPS on
`2026-10-11T05:08:56Z`. The
[repository](https://github.com/DAhmedGH/Credit-Risk-Decision-Science) is public.
The following `credit-risk-fixtures` runs were observed as completed with
conclusion `success`:

| Revision | Actions run | Observed result |
| --- | --- | --- |
| CI repair `412dd680c842061663fdfc5223ccd28fd5433221` | [38112715548](https://github.com/DAhmedGH/Credit-Risk-Decision-Science/actions/runs/38112715548) | SUCCESS; all three smokes, Ruff, pytest and separate SQL fixtures succeeded |
| Subsequent README update `b037c814dc5d70057d20c612b42815f91179fdf5`, then remote `main` | [38113711472](https://github.com/DAhmedGH/Credit-Risk-Decision-Science/actions/runs/38113711472) | SUCCESS |

The repair run's job and step results were inspected; remote numerical test
counts are not asserted. These observed remote results are separate from the
local executions recorded below and do not rewrite their receipts.

The scoring archive, checksum and manifest sidecars were also retrieved from
the public repository at `b037c814dc5d70057d20c612b42815f91179fdf5` and compared
byte-for-byte with the local delivery files. All three match. The archive remains
29,213 bytes with SHA-256
`d2fb60ca57f3b8b39fc271b62a2f0386db35842a8389d3444a4e6d6af6ce1349`.
Cloning the repository supplies this package; no separate release asset is needed.
This documentation check did not repeat installation, restoration or scoring
from a fresh GitHub clone, or rerun tests or scientific evaluation.

## Local source-only checks

After [environment setup](setup.md#public-clone-checks), run from the project root:

```bash
.venv/bin/python -m pip check
.venv/bin/ruff check . --no-cache
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m pytest -q -p no:cacheprovider
```

Some fixtures fit small synthetic estimators. They do not refresh portfolio
metrics. The fixture container uses the pinned Python 3.12.11 base image and
lock; its default command is pytest with caching disabled. Network-disabled
container tests require the image to have been built first. Raw data, historical
model stores, environments and credentials are excluded from its build context.
The public scoring package and unlabeled synthetic example are included.

For optional SQL fixtures, Docker must be available and integrated with WSL.
The project service runner creates/reuses only its verified disposable development
instance, with generated credentials in ignored `.env`:

```bash
python3 scripts/dev_db.py up
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CREDIT_RISK_SQL_TEST=1 \
  .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_database.py
python3 scripts/dev_db.py stop
```

Service startup and enabled SQL fixtures are mutating local operations, not
documentation checks. The tests use an outer rollback transaction. Scoring needs
neither this service nor its credentials.

## Recorded verification provenance

| Evidence scope | Recorded result | Meaning and limits |
| --- | --- | --- |
| Original scientific delivery | 207 SQL-enabled passes, zero skips, 87.89s; focused 24 passes, 32.60s | Historical checks of the accepted delivery |
| Original container fixtures | 206 passes, one expected SQL skip, 54.31s | Network disabled; separate from live SQL evidence |
| Original core reproduction | 114.778s; zero fits; identical split/folds, saved metrics/341 intervals/plan; scoring within 1e-12 | Exact historical source/payload; not a retrained search |
| Subsequent software audit | 231 SQL-enabled passes, zero skips, 82.04s | Malformed-batch/routing/monitoring/command corrections; accepted results unchanged |
| Separately reported rebuilt audit container | 230 passes, one SQL skip, 48.75s | Reported WSL execution; no raw terminal log supplied |
| Publication packaging | 17 focused parser/command passes, 14.10s; Ruff, syntax and links; 174 payload hashes; byte-exact synthetic scoring | Separate source-distribution/restoration checks, with zero fits/evaluation |
| Earlier documentation-only update | Links, anchors, figure paths, command interfaces, evidence transcription and Git diff | No scientific or mutating reproduction commands executed in that task |
| Public frozen-scoring delivery | 55 focused passes, 5.60s; rebuilt container 268 passes, one expected SQL skip, 50.45s; Ruff passed | Offline restoration/scoring, exact synthetic example, all 88 policies; full fixture suite may fit synthetic estimators, with no accepted-model fitting or scientific evaluation |
| Public CI smoke repair | All three CI smokes and Ruff passed; exact `pytest -q`: 270 passes, one expected SQL skip, 51.50s; separate SQL file: four passes, 0.24s | Local execution with tracked public files only, isolated container and new disposable database; subsequent remote status recorded above |

Historical results are not newly executed checks. Full commands, tolerances and
recorded failures remain in [delivery results](../reports/phase5.md),
[software findings](../reports/project-audit.md) and selected public receipts.
Publication prose does not replace original hash-bound receipts.
The new [public delivery evidence](../reports/public-scoring-delivery.json) records
the image identity, commands and isolation checks. Its
[focused review](../reports/public-scoring-review.md) covers the package and public
interfaces rather than repeating the original project audit.

## Coverage and remaining limits

Tests include idempotency/count reconciliation, month order, special codes,
signed balances and denominators; group/fold disjointness and sentinel-safe
preprocessing; target/ID/audit exclusion; fixed-base calibration and class-1
mapping; payoff signs/ties/all/none; serialization, malformed input, quarantine,
unknown categories, monitoring output preservation and CLI failures before access.

Passing fixture tests does not establish complete platform coverage, source
authentication, temporal/external validation, fairness or real lending impact.
Successful remote fixture CI does not establish historical scientific replay.
No automatic retraining or production deployment is claimed.

## Public smoke repair

The reported fresh-checkout failure was `FileNotFoundError` for
`reports/phase3_acceptance.json`. The Phase 4 synthetic smoke incorrectly called
`accepted_integrity(PROJECT_ROOT)` before creating its fixture. That guard requires
the original Phase 3 acceptance receipt, preservation inventory, source attachments,
customer exports and accepted model store; those are historical reproduction inputs.

The smoke now tests only compatibility on 120 generated rows: a five-tree
fixture model fits 60 rows; raw/sigmoid/isotonic mappings use 40 separate rows;
TreeSHAP checks raw-margin additivity on the remaining 20. Plotting and exact
joblib save/load probability agreement remain active. The existing version checks
remain. No missing receipt is ignored or fabricated. `accepted_integrity`, real
Phase 4 commands and the historical bootstrap's integrity step are unchanged.

The environment smoke checks imports/schema serialization; the Phase 2 smoke
fits tiny synthetic references and uses a temporary explicit local MLflow store.
Neither requires historical files. SQL tests use synthetic records and verify
the database's project/lifecycle identity before DDL, inside rollback transactions.
The workflow commands and dependency lock remain unchanged.

Running the actual bare `pytest -q` command also exposed a fixture import in
`test_phase5_monitoring.py`: `tests.fixtures` required a `tests` package that this
checkout does not define. It now imports `fixtures.records`, matching the other
tests. Earlier `python -m pytest` container checks supplied a different import
path and did not expose this collection failure. The repair verification uses
the workflow's exact `pytest` entry point rather than substituting that invocation.

Regression tests run the actual Phase 4 script with only public runtime code,
no reports/data/artifact directories and unusable database/tracking settings.
A separate test confirms the historical guard still rejects a missing receipt.
The [new repair evidence](../reports/public-ci-smoke-fix.json) records isolated
local checks; previous delivery receipts retain their earlier execution scope.
The pinned Python 3.12.11 container was rebuilt from a tracked-files-only export.
The full public export was copied into a new container without host mounts;
all workflow install/smoke/Ruff/pytest commands used its editable installation
with `PYTHONPATH` removed. The test container shared only the network namespace
of a new PostgreSQL 16 container whose network was disabled. SQL identity settings
were applied to that disposable service, and the enabled SQL file passed separately.
The original project and private payload were inaccessible. The distribution
archive, checksum and manifest sidecars retain their accepted delivery hashes.
