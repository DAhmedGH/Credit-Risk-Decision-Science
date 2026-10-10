# Independent Phase 1 source and feature review

This technical summary preserves recorded findings and checks. Original review
documents and hash-bound receipts are retained privately. These checks were
performed at the dated checkpoint, not repeated for presentation cleanup.

Reviewed on October 6, 2026 (America/Toronto). Scope: workbook interpretation,
normalized validation, deterministic features, SQL definitions, and related
tests. The split implementation was outside this source-review scope. No production source/feature/SQL code
was changed during this review.

## Findings requiring correction

| Severity / status | Affected paths | Evidence and scientific consequence | Concrete correction |
| --- | --- | --- | --- |
| Medium / corrected by inspection and Python checks; live SQL verification pending | `src/credit_risk/data/schema.py`, `src/credit_risk/features/__init__.py`, `sql/001_schema.sql`, `sql/002_curated.sql` | Initially a synthetic bill balance of `1e200` passed raw validation, then volatility squaring raised `OverflowError`; a positive limit of `1e-308` returned infinite ratios. These are now explicitly quarantined. A follow-up sentinel found that six equal bills of `1e308` were finite in Python integer arithmetic but overflowed the former SQL double sum. Financial SQL columns now use unconstrained `numeric`, adapted with `Decimal(str(value))`; the inspected SQL uses numeric arithmetic. A high-precision Decimal probe of that sentinel remains finite and agrees with Python. | The versioned `uci350-v1.1` / `financial-row-v1.1` contract requires finite Python predictor results, records arithmetic-range quarantine reasons, and preserves financial values with numeric SQL storage. No clipping, imputation, or learned cutoff was introduced. Live SQL/Python parity still requires the dedicated PostgreSQL instance. |
| Medium / resolved and rechecked: accepted integer values exceed SQL storage | `src/credit_risk/data/schema.py`, `sql/001_schema.sql` | Initially synthetic `client_id`, `age`, and `education` values of `10**20` passed validation despite `bigint`/`integer` storage. The validator now rejects oversized IDs structurally and quarantines oversized demographic values with explicit reasons. The exact signed 64-bit ID and signed 32-bit demographic maxima were checked and remain accepted. | Positive signed 64-bit IDs and signed 32-bit demographic representation limits are implemented. Regression checks pass. These are storage constraints, not population-derived cutoffs. |

These findings concern software integrity, not evidence about a held-out outcome
distribution. They must be resolved or explicitly retained as failing phase
checks. No arbitrary financial-amount cutoff is recommended.

## Source inspection evidence

The supplied workbook was read without modifying its original bytes or mtime.
Its SHA-256 is
`30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`.
The bounded diagnostic found one `Data` sheet, declared dimensions 30,002 rows
and 25 columns, the variable aliases in row 1, and the exact expected header in
row 2. It decoded exactly 750,000 numeric data cells, corresponding to 30,000
complete customer records. Duplicate cells, missing numeric cells, formulas,
text data cells, error cells, and unsupported worksheet records were rejected.
All data cells in this particular file were covered by the numeric-cell checks.

The independent diagnostic was a temporary standard-library OLE/BIFF reader,
not the production ingestion route. It explicitly accepted only recognized
numeric records and worksheet metadata. [Microsoft's BIFF record
index](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-xls/43684742-8fcd-4fcd-92df-157d8d7241f9)
and [cell-table grammar](https://learn.microsoft.com/nl-be/openspecs/office_file_formats/ms-xls/a1b3d8b4-7442-41fd-9c57-bbd2a6394082)
were consulted to distinguish numeric cells from page-layout/phonetic metadata.
The ignored diagnostic records and metadata are at
`data/processed/inspection_records.jsonl` and
`data/processed/inspection_metadata.json`. The records-file SHA-256 is
`3d6f072a5a3c20391482853f344255f03f35643033acf4a1cef921f67d9d5507`.

An early diagnostic rejected an unsupported printed-header record before any
numeric data decoding. A second attempt decoded numeric cells, then rejected a
page-layout metadata record. The successful attempt recorded its first outcome
cell decoding at `2026-10-07T01:53:54.395389+00:00`; this is not the historical
first access. The earliest actual decoding occurred between
`2026-10-07T01:53:18+00:00` and that timestamp; its exact time was not captured.
These accesses support source integrity and subsequent stratification only.
No source outcome counts, prevalence, comparative results, charts, or example
records were computed or emitted by the diagnostic. The authoritative exposure log records these accesses.

Canonical `xlrd` reading and agreement with this diagnostic remain pending
dependency availability. This diagnostic does not establish original download
time, archive checksum, or byte identity with an absent official ZIP.

## Inspection and checks actually performed

- Read the exact source-to-normalized mapping, including `PAY_0` for September
  and `PAY_2` for August. The three histories are consistently ordered April to
  September in the predictor contract.
- Inspected the allowlist and feature result construction: IDs, targets, and
  all four audit attributes remain outside predictors; unlabeled inputs work.
- Inspected special repayment codes, signed balances, undefined denominators,
  and missing-input propagation. No whole-data imputation, scaling, fitted
  vocabulary, learned cutoff, or population-based feature operation exists.
- Inspected SQL null guards and the explicit export columns. Their intended
  formulas match the Python contract; executing PostgreSQL and testing actual
  SQL/Python agreement remain pending the Docker/dependency environment.
- Ran `PYTHONPATH=src:tests python3 -m unittest discover -s tests -p test_data.py -v`:
  16 tests passed.
- Ran `PYTHONPATH=src:tests python3 -m unittest discover -s tests -p test_features.py -v`:
  10 tests passed.
- Ran separate synthetic finite-arithmetic and SQL-integer-range sentinels,
  reproducing both findings above. These fixtures contain no real observations
  and provide no modeling results.
- Re-read the first corrections and reran the two suites: 17 data tests and 11
  feature tests passed. Storage boundary probes passed. The constant-huge-bills
  probe reproduced the remaining Python-integer versus SQL-double arithmetic
  mismatch without accessing real data or claiming PostgreSQL execution.
- Re-read the subsequent numeric-storage correction, Decimal adaptation, and
  persisted raw/predictor/label/audit equality checks. Re-ran the suites: 17 data
  tests and 11 feature tests passed. A 350-digit Decimal sentinel reproduced a
  finite constant-huge-bills mean and its agreement with Python. PostgreSQL's
  documented [`numeric` storage and exact arithmetic](https://www.postgresql.org/docs/16/datatype-numeric.html)
  support this design correction; this remains inspection and a Python probe,
  not a claim that the live database check has passed.

Both implementation findings have been corrected and rechecked within the
available Python/inspection scope. The overall Phase 1 exit gate remains
pending canonical workbook and real PostgreSQL/SQL-parity/idempotency evidence.
No predictive model was trained.
