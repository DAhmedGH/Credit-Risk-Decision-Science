# Data contract: UCI 350, financial-row-v1.1

The observation is one existing credit-card customer at the released month-end snapshot. Prediction is assumed to occur after all released September 2005 histories are available. The outcome is the source's next-month default indicator, normalized to `default_next_month`, with positive class `1`. The release does not establish a regulatory default definition, lifetime risk, new-applicant outcomes, or behavior under additional lending.

The source is [UCI Default of Credit Card Clients, dataset 350](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients), credited to I-Cheng Yeh (2009), [DOI 10.24432/C55S3H](https://doi.org/10.24432/C55S3H), CC BY 4.0. The original local `.xls` bytes are immutable. The provenance manifest records the checksum and observations that can be established; filesystem timestamps do not establish a download date. No ZIP acquisition is implied by the presence of an extracted workbook.

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

Credit limit and target are mandatory. Missing financial histories and audit values remain missing; they are counted rather than filled. This supports future training-fold imputation without learning a whole-data statistic. All canonical cleaning rules are row-level or structural. A change to source bytes or cleaning rules requires a new version and provenance.

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

EDA is restricted to development IDs after the split manifest is frozen. Future imputation, scaling, category vocabularies, feature selection, resampling, and distribution thresholds must be fitted inside the relevant training fold. Synthetic fixtures test software behavior only and supply no portfolio results.

Phase 1 transformations and fixture tests use the Python standard library; `xlrd` is needed only for the real XLS loader, and `psycopg` for PostgreSQL. Pandas/NumPy and learned preprocessing are deferred until needed in Phase 2. The explicit Phase 1 restriction on predictive training also defers the design's tiny model fit/serialization environment check; no model was fitted as a setup check.
