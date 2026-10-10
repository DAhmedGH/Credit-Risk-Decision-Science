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
training are required. Remote Actions execution has not been observed, so local
evidence does not establish a remote CI pass.

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
No automatic retraining, production deployment or observed remote CI is claimed.
