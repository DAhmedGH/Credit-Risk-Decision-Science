# Dataset, validation and feature contracts

The observation is one existing credit-card customer at the released month-end snapshot. Prediction is assumed to occur after all released September 2005 histories are available. The outcome is the source's next-month default indicator, normalized to `default_next_month`, with positive class `1`. The release does not establish a regulatory default definition, lifetime risk, new-applicant outcomes, or behavior under additional lending.

The study uses the supplied workbook from [UCI Default of Credit Card Clients, dataset 350](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients), credited to I-Cheng Yeh (2009), [DOI 10.24432/C55S3H](https://doi.org/10.24432/C55S3H), CC BY 4.0. Its bytes were subsequently verified against the official archive. The original local `.xls` bytes are immutable. Filesystem timestamps do not establish the original download date.

The plan specified an official ZIP/workbook acquisition with recorded retrieval
time and both checksums. The delivered study retained an existing workbook under
the recorded D002 provenance qualification; no original ZIP or acquisition record
was available. The original download chain, retrieval date and archive checksum
remain unknown.

The supplied workbook was subsequently verified byte-for-byte against the official
UCI archive retrieved at `2026-10-10T18:00:23.006402Z`. The recorded accepted hash,
independently measured local hash and official workbook member hash all equal
`30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`;
both workbooks contain 5,539,328 bytes. The new archive contains 5,539,494 bytes,
SHA-256 `56c885f84457f6680f8438f02bfcdac9579323d8a94465ee5f26e32baa727602`.
The [verification receipt](../reports/provenance/uci350-official-comparison-20261010T180023Z.json)
records the confirmed page link, requested/final URLs, UTC retrieval time, member
name and available HTTP metadata. The page currently uses literal `+` characters
in the ZIP path, equivalent to the previously observed `%2B` spelling.

Verification used certificate-verified HTTPS and an isolated temporary download.
The unique workbook member was read directly from the ZIP without filesystem
extraction or cell decoding; hashes and full bytes were compared. The archive
response supplied Date and Server, but no Content-Length, Content-Type, ETag or
Last-Modified. Its byte length was measured from the received body. Response
metadata is not evidence of the original acquisition date. This new comparison
does not reconstruct the original download chain or alter historical manifests.

The [source manifest](../artifacts/source_manifest.json) preserves initial
reader/diagnostic states marked pending. Later [canonical validation](../reports/source_validation.json)
records xlrd 2.0.2, 30,000 accepted rows and zero rejections; the
[export manifest](../artifacts/phase1_export_manifest.json) records all-row
SQL/Python agreement. Historical pending fields are not the current reader status.

## Workbook and normalization

The loader requires the `Data` sheet, 25 columns, an initial variable-code row (`X1`–`X23`, `Y`, with a blank identifier cell), and the exact source header in Excel row 2. Records start at Excel row 3. `xlrd` preserves numeric values and converts only integral numeric representations to Python integers during validation. Blank cells become missing values. Text, Excel date, boolean, and error cells cannot silently become numeric training data.

| Source fields | Normalized fields | Role |
| --- | --- | --- |
| `ID` | `client_id` | Positive integer join key; excluded from predictors |
| `LIMIT_BAL` | `limit_bal` | Required finite positive credit limit, in released monetary units |
| `SEX`, `AGE`, `EDUCATION`, `MARRIAGE` | `sex`, `age`, `education`, `marriage` | Audit attributes only |
| `PAY_6`, `PAY_5`, `PAY_4`, `PAY_3`, `PAY_2`, `PAY_0` | `pay_status_2005_04` through `pay_status_2005_09` | April through September repayment categories |
| `BILL_AMT6` through `BILL_AMT1` | `bill_amt_2005_04` through `bill_amt_2005_09` | April through September signed bill balances |
| `PAY_AMT6` through `PAY_AMT1` | `pay_amt_2005_04` through `pay_amt_2005_09` | April through September payments |
| `default payment next month` | `default_next_month` | Required binary training outcome; excluded from predictor contract |

The `PAY_0` / `PAY_2` naming gap is intentional: September is `PAY_0` and August is `PAY_2`. These six histories are one customer's inputs, not six separately labeled observations. ID provides no supported chronological ordering.

## Validation and cleaning

Schema mismatch, invalid/null identifiers, and duplicate identifiers abort ingestion. Other row-level failures are quarantined with the original normalized record, record index, client ID, and explicit reason codes. No row is silently removed. Source, accepted, rejected, curated, and exported counts must reconcile.

Numeric values must be finite; booleans and numeric-looking strings are rejected. Repayment categories must be integers in `-2`, `-1`, `0` through `9`. The special values `-2`, `-1`, and `0` remain separate raw categories. Published descriptions do not resolve every special-code meaning, so no behavior is invented for undocumented values. Demographic categories must be integers when present. Undocumented demographic codes are preserved, with explicit `unknown` audit groups; they do not enter prediction. Positive integer age is required when present. Signed financial amounts are preserved without clipping or unsupported amount cutoffs.

Credit limit and target are mandatory. Missing financial histories and audit values remain missing; they are counted rather than filled. This leaves imputation to training-fold fitting without learning a whole-data statistic during ingestion. All canonical cleaning rules are row-level or structural. A change to source bytes or cleaning rules requires a new version and provenance.

Identifiers must fit positive PostgreSQL `bigint`; demographic integers must fit
PostgreSQL `integer`. These are storage limits rather than population cutoffs.
Rows whose versioned engineered arithmetic overflows or returns a nonfinite
value are quarantined as `engineered_features:arithmetic_range`. Raw signed
amounts are otherwise preserved; no distribution-based magnitude cutoff is used.

## Predictors and deterministic features

The versioned allowlist contains 19 raw financial predictors: credit limit, six repayment statuses, six signed bill balances, and six payments, all histories in April-to-September order. The engineered contract adds 13 variables (11 formulas and two missingness flags). `client_id`, `default_next_month`, sex, age, education, and marriage cannot enter the feature matrix. The feature builder accepts unlabeled financial records and never returns extra input fields.

| Engineered field | Definition and missingness rule |
| --- | --- |
| `recent_delinquency_count` | Count statuses greater than zero over all six months |
| `maximum_positive_delay` | Maximum `max(status, 0)` over six months, zero when all are nonpositive |
| `recent_history_delay_contrast` | Mean positive delay in July–September minus April–June |
| `latest_utilization_proxy` | September bill divided by positive credit limit; signed and unclipped |
| `mean_utilization_proxy` | Mean of six signed bills divided by positive limit |
| `bill_balance_change` | (September bill − April bill) divided by limit |
| `bill_volatility_proxy` | Population standard deviation of six signed bills divided by limit |
| `mean_payment` | Mean of six payments, in released monetary units |
| `zero_payment_count` | Count actual zero payments over six months; missing is not zero |
| `payment_to_prior_bill_proxy` | September payment / August bill if bill is positive; otherwise missing |
| `payment_to_prior_bill_missing` | `1` when the preceding proxy is missing, otherwise `0` |
| `aggregate_payment_balance_proxy` | Total six payments / sum of positive six bill balances; missing for zero denominator |
| `aggregate_payment_balance_missing` | `1` when the preceding proxy is missing, otherwise `0` |

Missing required inputs propagate into their dependent formula. For example, a missing April bill prevents mean utilization, but does not prevent the September/August payment proxy. A missing middle bill does not prevent the latest-minus-oldest change. These formulas contain no learned cutoff, vocabulary, scaling, or imputation. The positive-delay transform defines summaries only; it does not collapse the raw repayment categories.

Payment/balance ratios are proxies. The release does not fully specify contractual due amounts or timing, so they are not repayment fractions or debt-to-income measures. Credit limit also reflects a prior lending policy. Removing demographics does not demonstrate fairness or remove correlated proxies.

## Dataset use

After structural validation, exact 19-field financial profiles are fingerprinted without labels or demographics. Identical profiles stay together in all partitions and development folds; different customers are retained. The fixed targets are development 60%, calibration 15%, policy validation 10%, and final test 15%, seed 42, with five development folds. The split artifacts record actual allocations and deviations. Labels are used only for allocation/integrity; held-out outcomes do not guide EDA or feature decisions.

EDA is restricted to development IDs after the split manifest is frozen. Imputation, scaling, category vocabularies and any learned feature selection or resampling belong inside the relevant fit scope. Monitoring distribution thresholds are fitted on development only. Synthetic fixtures test software behavior only and supply no portfolio results.

## Storage and reconciliation

| Object or file | Grain and key | Contract |
| --- | --- | --- |
| `raw.credit_clients`, `curated.credit_clients` | One source/customer record; `(source_sha256, client_id)` | Raw values, acceptance/rejection reasons and curated cleaning flags; transactional, idempotent ingestion |
| `curated.model_features_v1` | One source/customer; `(source_sha256, client_id)` | Explicit financial allowlist and deterministic SQL row features |
| `curated.audit_attributes` | One source/customer; `(source_sha256, client_id)` | Demographics are retained separately for descriptive analysis |
| `data/processed/financial_features_v1.csv` | One customer; `client_id` | 32 financial predictors, with labels and audits exported separately |
| `artifacts/split_manifest.csv` | One customer assignment | Partition, development fold, raw financial fingerprint, seed and source hash |
| Batch input/output | One unlabeled input record; `record_id` | Raw financial schema, preserved identities, scored/quarantined counts |

Recorded source, curated, audit and exported counts are each 30,000, with zero
rejections. SQL/Python agreement is recorded in the
[export manifest](../artifacts/phase1_export_manifest.json) and
[database reconciliation](../reports/database_reconciliation.json).
Reingestion checks preserve already loaded records; the two recorded ingestion
no-ops are not evidence of a fresh-empty-database load in that execution.

The canonical XLS reader requires `xlrd`, PostgreSQL requires `psycopg`, and
modeling uses the pinned NumPy/pandas/scikit-learn environment. Training requires
valid positive limits and binary targets; inference permits missing financial
cells for frozen preprocessing while rejecting supplied nonpositive limits.
The training and inference validators have distinct contracts:

| Input condition | Canonical source validation | Batch inference |
| --- | --- | --- |
| Missing credit limit | Reject the row | Permit frozen imputation; supplied nonpositive values still quarantine |
| Repayment status | Integral released range `-2`, `-1`, `0..9` | Permit unseen integral categories with unknown-safe encoding |
| Payment amount | Preserve finite signed source amounts | Quarantine negative payments |
| Numeric representation | Accept numeric Excel cells; reject numeric-looking text | Parse numeric CSV text; reject booleans, nonnumeric and nonfinite values |

These differences describe delivered validation, not interchangeable schemas.
A record accepted by source ingestion is not guaranteed to pass the public scorer.
No business validity is established for an unseen status.
See [batch scoring](batch_scoring.md), [leakage and availability](leakage_audit.md),
and [modeling and partition isolation](modeling.md).
