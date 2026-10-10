# Phase 1 completion and checkpoint

This report records the historical Phase 1 checkpoint. Phase status, Git
state and check counts below describe that execution, not the current publication
checkout. Use [modeling](../docs/modeling.md),
[setup](../docs/setup.md) and [final evaluation](results.md) for the completed
project's methods, execution boundaries and results.

**Phase 1 scientific exit gate: passed. Checkpoint: complete. Phase 2: not started.**
The remaining delivery blocker is Git initialization and committing the prepared
files; this directory is not yet a repository. No unresolved scientific or data
integrity finding remains in the reviewed Phase 1 scope.

## Verification attribution

Recorded WSL execution reports a successful manual WSL reproduction: **30,000 source, curated,
audit, and exported rows; zero rejected; `counts_reconcile=true`; both ingestion
attempts were no-ops; development-only EDA; no predictive training**. Reported WSL verification also records the enabled live database test file: **4 passed in 2.37s**.
These are **reported WSL verification results**, distinct from the saved-artifact
checks below. The exact test execution time and complete console log were not supplied.
Both no-ops demonstrate stability against already-ingested data, rather than a
fresh-empty-database load in that reproduction.

The checkpoint inspected the saved canonical reports and export/split receipts,
which corroborate the row counts, no-ops, reader, feature parity, and scope.
The database test timing is reported evidence. The structured receipt is
`reports/phase1_checkpoint.json` (private historical evidence).

Recorded checks in this checkpoint: the Python 3.12.11 import/feature-serialization
smoke check passed with xlrd 2.0.2 and psycopg 3.2.3; all 11 installed package
versions matched `requirements.lock`; seven source/split/contract/lock/export
file hashes matched the canonical evidence. No source labels were decoded for
this checkpoint; CSV hashes were checked without outcome analysis. PostgreSQL and
predictive fitting were not run here.

Prior recorded verification in [lint-resolution.json](lint-resolution.json): Ruff
passed for the repository, with Git ignores disabled, and for explicit maintained
paths; all 24 maintained Python files remained covered. Fixture pytest passed
**47 tests**, with the live SQL test explicitly skipped in that fixture run. The
later reported enabled database run supplies the live evidence separately; these
counts must not be combined into an invented single suite run.

## Phase 1 requirements and evidence

| Requirement | Disposition and evidence |
| --- | --- |
| Isolated environment, package, configuration, dependency lock, ignores | Implemented in `pyproject.toml`, `requirements.lock`, `.python-version`, `.gitignore`, `.env.example`, `configs/base.toml`, and bootstrap scripts. Python 3.12 import/serialization and exact installed pins verified. Other project environments are preserved. |
| Existing workbook and official UCI 350 compatibility | Preserved original bytes; attribution, unknown acquisition details, sheet/header/schema interpretation in `artifacts/source_manifest.json`. Canonical xlrd parsing in `reports/source_validation.json` confirms the same 30,000 × 25 numeric records. No ZIP or substitute download was required. |
| Validation and cleaning | Canonical report confirms unique/non-null IDs, binary/non-null target, 30,000 accepted and zero rejected. Tests cover numeric/finiteness constraints, category codes, signed balances, month mapping, and storage/arithmetic bounds. |
| Dedicated PostgreSQL, idempotency, reconciliation | `compose.yaml`, owned-service runner, and `sql/001_schema.sql`–`003_feature_export.sql`; reported WSL counts and no-ops corroborated by `reports/phase1_run.json` and `reports/database_reconciliation.json`. Enabled database passes are reported WSL evidence. |
| Row-only features and predictor allowlist | `financial-row-v1.1`: 19 raw plus 13 engineered financial predictors. ID, target, sex, age, education, and marriage are excluded from the predictor matrix. Labels and audit attributes are exported separately. `artifacts/phase1_export_manifest.json` records SQL/Python agreement for every exported row. |
| Frozen partitions and five development folds | Seed 42; unchanged `artifacts/split_manifest.csv`; canonical xlrd revalidation receipt in `artifacts/split_checks/`. Complete unique assignment, group disjointness, development-only folds, and class-presence checks all true. |
| EDA, contract, leakage audit, tests, scientific review | `reports/development_eda.json` covers only 18,000 development rows; no learned whole-data transforms. `docs/data_contracts.md`, `docs/leakage_audit.md`, tests, decision/exposure logs, and two independent reviews exist. Review closeout is described below. |
| Committed provenance and project files | Prepared but **not committed**: Git initialization remains outstanding. Hashes provide current artifact identity but do not substitute for a commit. |

The source is `data/raw/default of credit card clients.xls`, **5,539,328 bytes**,
SHA-256 `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`.
Canonical parsing uses the `Data` sheet, variable aliases in Excel row 1,
headers in row 2, and records from row 3. Repayment month mapping preserves the
irregular `PAY_0` September / `PAY_2` August names through `PAY_6` April 2005.
Negative bill balances and special repayment codes remain intact. Undefined
ratios stay missing with explicit flags; no whole-population imputation,
scaling, category vocabulary, clipping, or distribution threshold is fitted.
The original ZIP is absent; its checksum and the original download date remain
unknown. Attribution is to I-Cheng Yeh, UCI dataset 350, DOI 10.24432/C55S3H,
CC BY 4.0. No claims of observed profit or new-loan underwriting are supported.

## Frozen allocation

| Partition | Rows | Profile groups | Requested share | Row deviation |
| --- | ---: | ---: | ---: | ---: |
| Development | 18,000 | 17,508 | 60% | 0 |
| Calibration | 4,500 | 4,378 | 15% | 0 |
| Policy validation | 3,000 | 2,919 | 10% | 0 |
| Final test | 4,500 | 4,378 | 15% | 0 |

Five development folds each contain **3,600 rows**, with profile-group counts
3,499 / 3,503 / 3,503 / 3,502 / 3,501 and zero row-count deviations. There are
29,183 financial-profile groups; 134 repeated groups contain 951 customers,
with a maximum group size of 63. Fingerprints use only the 19 raw financial
predictors, without labels or demographics. Customers sharing profiles remain
retained and grouped across partitions and folds. Tests establish reproducible
assignment and input-order invariance. No claim of globally optimal class
balance is made; held-out outcome distributions are not published.

Frozen manifest SHA-256:
`775f9862fb5b97095c81fdae440d4acb7fd52f692a216b6284e879db5e4d5e4c`.
Current feature contract SHA-256:
`4adb6745e582e551239b9e999d0128649fdaff0b1f63deebfea6f538ecc2eeae`.
Lock SHA-256:
`8ca35948b60fc22ce665588864982a468ef7bf362dd5fa61e9fd604d08eb4624`.

The original split summary and source manifest retain historical diagnostic-reader
qualifications. They are preserved evidence, not instructions to rerun allocation.
The authoritative canonical revalidation is
`artifacts/split_checks/840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537.json`;
it binds the unchanged split to the current feature contract and canonical xlrd
reader. Current source/export/EDA reports supersede earlier diagnostic-only
reports. Full-source label access recorded in `docs/test-exposure-log.md` was
limited to integrity and stratification; development EDA and predictive final-test
evaluation are separate, and no final-test evaluation has occurred.

## Review closeout and remaining limitations

Independent reviews are in `docs/validation-source.md` and
`docs/validation-data-features.md`. Their code findings were corrected: numeric range
and exact SQL storage, persisted source/label/audit comparison, export guards,
and EDA provenance. Their then-pending canonical-reader, live SQL, runtime, and
lint verification dependencies now have the evidence listed above. This is a
technical closeout of existing reviews, not a claim of a new independent review
or a separately repeated live database test.

The 3,337-error Ruff failure came entirely from installed code in `.tools/`
(2,697) and `.cache/` (640). Explicit installed/generated-path exclusions now
preserve all selected rules and maintained-code coverage. No blanket unsafe
fixes or source behavior changes were made. The original environment's cache-write
restriction is avoided with `--no-cache`.

Historical Phase 1 evidence used content hashes before Git initialization.
No remote CI or fresh-volume/container rebuild was claimed at that checkpoint.

## Reproduce Phase 1

Run from the ordinary WSL terminal; the existing workbook and frozen manifest
must remain unchanged:

```bash
cd '/mnt/c/Users/Danieal/Desktop/Credit Risk Project'
bash scripts/bootstrap.sh
python3 scripts/dev_db.py up
.venv/bin/python -m credit_risk reproduce --config configs/base.toml
.venv/bin/ruff check . --no-cache
.venv/bin/python -m pytest -q -p no:cacheprovider
CREDIT_RISK_SQL_TEST=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_database.py
```

These are reproduction instructions; they were not all rerun during this
checkpoint. The smoke command verified here was
`.venv/bin/python scripts/environment_smoke.py`.
See `docs/reproduction.md` for ownership/port checks and service/Git lifecycle.

## Subsequent modeling stage

The versioned financial contract, frozen development IDs and five folds feed the
[Phase 2 baseline comparison](phase2.md). ID is a join key only; demographic
attributes remain audit-only. No predictive training occurred in Phase 1.
