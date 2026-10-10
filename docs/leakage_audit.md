# Feature availability and leakage controls

The fixed prediction time is after all released September 2005 histories are available. This is a retrospective availability assumption, not verified operational availability for a deployed lender. Each customer contributes one snapshot. No history month is relabeled as an independent observation. The target's exact operational definition remains limited to UCI's released next-month indicator.

The following audit covers every source input and deterministic predictor. Source availability follows the [official UCI 350 documentation](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients). The field mapping and parsing choices are enforced by workbook/schema tests and recorded in provenance. Repayment values `-2` and `0` have unresolved special-code meanings; raw categories are retained rather than reinterpreted.

| Input or derived predictor | Exact source dependencies | Availability | Transform | Fit scope | Decision and limitation |
| --- | --- | --- | --- | --- | --- |
| `client_id` | `ID` | Snapshot identifier | Integral validation; join key | Structural | Exclude; ID is not a date |
| `default_next_month` | `default payment next month` | After prediction horizon | Binary validation | Integrity/split stratification only | Exclude; outcome cannot enter features |
| `sex` | `SEX` | Snapshot audit field | Preserve code; explicit audit unknown grouping | Row-only | Audit only; not evidence of fairness |
| `age` | `AGE` | Snapshot audit field | Positive integer validation if present | Row-only | Audit only; no learned age bins |
| `education` | `EDUCATION` | Snapshot audit field | Preserve code; undocumented values grouped unknown | Row-only | Audit only; no inferred socioeconomic fields |
| `marriage` | `MARRIAGE` | Snapshot audit field | Preserve code; undocumented values grouped unknown | Row-only | Audit only |
| `limit_bal` | `LIMIT_BAL` | Released snapshot, assumed known | Finite positive validation; no clipping | Row-only | Include; reflects upstream lending policy |
| `pay_status_2005_04` | `PAY_6` | April history before snapshot | Preserve special integer categories | Row-only | Include; category encoding fitted later |
| `pay_status_2005_05` | `PAY_5` | May history before snapshot | Preserve special integer categories | Row-only | Include |
| `pay_status_2005_06` | `PAY_4` | June history before snapshot | Preserve special integer categories | Row-only | Include |
| `pay_status_2005_07` | `PAY_3` | July history before snapshot | Preserve special integer categories | Row-only | Include |
| `pay_status_2005_08` | `PAY_2` | August history before snapshot | Preserve special integer categories | Row-only | Include; irregular source naming tested |
| `pay_status_2005_09` | `PAY_0` | September, assumed available by prediction | Preserve special integer categories | Row-only | Include; timing assumption unresolved operationally |
| `bill_amt_2005_04` | `BILL_AMT6` | April history | Preserve signed amount | Row-only | Include; negatives are not silently removed |
| `bill_amt_2005_05` | `BILL_AMT5` | May history | Preserve signed amount | Row-only | Include |
| `bill_amt_2005_06` | `BILL_AMT4` | June history | Preserve signed amount | Row-only | Include |
| `bill_amt_2005_07` | `BILL_AMT3` | July history | Preserve signed amount | Row-only | Include |
| `bill_amt_2005_08` | `BILL_AMT2` | August history | Preserve signed amount | Row-only | Include |
| `bill_amt_2005_09` | `BILL_AMT1` | September, assumed available by prediction | Preserve signed amount | Row-only | Include |
| `pay_amt_2005_04` | `PAY_AMT6` | April history | Preserve amount and actual zeros | Row-only | Include |
| `pay_amt_2005_05` | `PAY_AMT5` | May history | Preserve amount and actual zeros | Row-only | Include |
| `pay_amt_2005_06` | `PAY_AMT4` | June history | Preserve amount and actual zeros | Row-only | Include |
| `pay_amt_2005_07` | `PAY_AMT3` | July history | Preserve amount and actual zeros | Row-only | Include |
| `pay_amt_2005_08` | `PAY_AMT2` | August history | Preserve amount and actual zeros | Row-only | Include |
| `pay_amt_2005_09` | `PAY_AMT1` | September, assumed available by prediction | Preserve amount and actual zeros | Row-only | Include |
| `recent_delinquency_count` | `PAY_6`, `PAY_5`, `PAY_4`, `PAY_3`, `PAY_2`, `PAY_0` | Histories above | Count positive statuses | Row-only | Include; complete six-month history required |
| `maximum_positive_delay` | Same six repayment fields | Histories above | Maximum positive delay, otherwise zero | Row-only | Include; raw special codes unchanged |
| `recent_history_delay_contrast` | Same six repayment fields | Histories above | Mean positive July–September delay minus April–June | Row-only | Include; fixed chronological order |
| `latest_utilization_proxy` | `BILL_AMT1`, `LIMIT_BAL` | Snapshot histories above | September signed bill / positive limit | Row-only | Include; signed/unclipped proxy |
| `mean_utilization_proxy` | `BILL_AMT6`–`BILL_AMT1`, `LIMIT_BAL` | Histories above | Mean six signed bills / limit | Row-only | Include; missing dependencies propagate |
| `bill_balance_change` | `BILL_AMT1`, `BILL_AMT6`, `LIMIT_BAL` | Histories above | Latest minus oldest / limit | Row-only | Include; no distribution threshold |
| `bill_volatility_proxy` | `BILL_AMT6`–`BILL_AMT1`, `LIMIT_BAL` | Histories above | Population SD / limit | Row-only | Include; no whole-data scaling |
| `mean_payment` | `PAY_AMT6`–`PAY_AMT1` | Histories above | Six-month mean | Row-only | Include; source monetary units |
| `zero_payment_count` | `PAY_AMT6`–`PAY_AMT1` | Histories above | Count actual zeros | Row-only | Include; missing is not zero |
| `payment_to_prior_bill_proxy` | `PAY_AMT1`, `BILL_AMT2` | Histories above | September payment / positive August bill | Row-only | Include; contractual timing unresolved |
| `payment_to_prior_bill_missing` | `PAY_AMT1`, `BILL_AMT2` | Histories above | Missing-proxy indicator | Row-only | Include; no learned filling |
| `aggregate_payment_balance_proxy` | `PAY_AMT6`–`PAY_AMT1`, `BILL_AMT6`–`BILL_AMT1` | Histories above | Sum payments / sum positive bills | Row-only | Include; proxy, not repayment obligation |
| `aggregate_payment_balance_missing` | Same six payment and six bill fields | Histories above | Missing-proxy indicator | Row-only | Include |

SQL and Python calculate only fixed row formulas before splitting. No whole-data
category vocabulary, winsorization cutoff, imputation statistic, feature selection
or resampling is permitted. The row-feature builder has no fitted state and cannot
use other rows. Recorded sentinel tests verify that other records and changes to
labels, IDs or audit fields cannot change financial predictors. Fold-fitted
preprocessing separately preserves fit-only medians, scales and vocabularies.
[Modeling](modeling.md) describes the pipeline and
[testing and CI](ci_cd.md) distinguishes verification scopes.

Fingerprinting uses all 19 raw financial predictors, excludes label/ID/audits, and retains exact-profile customer groups in one partition and one development fold. Target access needed for stratified allocation is logged separately; it is not held-out outcome EDA. EDA must load development IDs through the frozen manifest and fail if given a held-out scope. The partition/fold report is the authority for actual allocation and group-integrity evidence.

Remaining limits are the released target's operational definition, exact within-month billing/payment timing, special repayment-code semantics, and representativeness beyond historical Taiwanese existing accounts. None is repaired by fabricating dates, financial fields, or behavioral meanings.
## Learned transforms and isolation

Modeling uses the unchanged financial-row-v1.1 feature contract. The selector
retains only the raw/combined allowlist before any learned operation; IDs,
outcomes and audit demographics remain excluded. Source availability retains
the historical month-end assumption described above.

| Operation | Source dependencies | Fit scope | Inclusion and limitation |
| --- | --- | --- | --- |
| Numeric median imputation | Allowlisted numeric predictors | Each frozen development fold's fit rows | Keep entirely missing columns with deterministic zero fallback; no global median |
| Numeric scaling (logistic) | Imputed numeric predictors | Same fold fit rows | Mean/scale saved with pipeline; tree inputs unscaled |
| Categorical mode imputation | Six repayment-status columns | Same fold fit rows | Keep distinct special codes; all-empty fallback zero is explicit |
| One-hot vocabulary | Imputed repayment-status columns | Same fold fit rows | Unknown categories encode all zeros; names/order saved per fold |
| Balanced class weights | Binary outcomes of current fit rows | Same fold fit rows | n_fit/(2*n_class); no held-out prevalence or bootstrap-local weighting |
| Prior dummy probabilities | Outcomes of current fit rows | Same fold fit rows | Separate from majority hard classification reference |
| Development error diagnostics | Frozen-fold OOF predictions and development outcomes | Development only | 0.5 diagnostic threshold and largest squared-error examples; no policy tuning |

Export hashes cover complete files without analyzing outcomes. CSV streaming
routes rows by ID before numeric/outcome conversion; held-out strings are
traversed but not interpreted. Entry points log this traversal before loading.
No calibration/policy/final-test outcome distribution guides these operations.
Learned-transform and sentinel checks passed in their recorded executions;
[verification provenance](ci_cd.md#recorded-verification-provenance) keeps original
delivery, subsequent software checks and publication checks separate. Accepted
transformation source and fitted identities remain hash-bound. Original detailed
execution records remain private historical evidence.

## Frozen evaluation and delivery

Readiness checks inspected source/tests and all 106 accepted artifacts before
final-test access. Feature formulas, fitted preprocessing, model, mapping,
scenarios, cutoffs and tie rules remained fixed. Seed-42 fingerprint-group draws
(1,000 repetitions) pair comparisons and retain complete clusters. Reports verify
saved IDs, fingerprints, models and decision masks against frozen identities.
Final outcomes were evaluated once; subsequent reporting and reproduction use
saved evidence with access recorded in the [exposure log](test-exposure-log.md).

[Standalone scoring](batch_scoring.md) rejects labels, audit fields and extra
schema fields, using only frozen transformations. [Monitoring](monitoring.md)
fits bins on development; labeled synthetic mixes retain unchanged histories,
while corruption removes labels. The assumed September month-end availability
and unknown original official-download identity remain limitations.
