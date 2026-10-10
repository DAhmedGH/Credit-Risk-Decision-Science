# Synthetic monitoring

The real-data monitoring run completed successfully with the frozen existing-account risk bundle. Development supplied 18,000 rows and distribution bins; the unchanged policy-validation cohort supplied 3,000 rows. The mix shifts are synthetic resampled population compositions, not observed temporal drift. No model fitting, policy reselection, final-test conversion or evaluation occurred.

## Execution prerequisites

The current monitoring CLI invokes original source-bound preflight. It requires
both the private payload and complete accepted-source/receipt archive; restoring
the payload beside maintained public code is insufficient. Follow
[historical reproduction](setup.md#historical-reproduction), install its pinned
Linux/WSL environment and run from that private project root with a new output:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m credit_risk.phase5 monitor --output reports/monitoring_new
```

This writes scenario reports and runtime records; it is not an installation check.
The original report was written at `2026-10-09T21:30:36.593280+00:00`, exit code 0.
Tests were not rerun for that execution. See
[execution checks](../reports/phase5_monitoring/execution_checks.json).

## Scenario construction

Each mix shift drew **3000** policy-validation rows with replacement, using seed **42** independently. Subgroup rows received weight **3**, other rows weight **1**; draw probability was weight divided by total weight. The financial subgroup was latest utilization proxy ≥ development Q75 **0.83686125**. The delinquency subgroup had any positive repayment delay across April–September 2005. Missing subgroup evidence does not qualify a row. Financial values and labels remained unchanged in sampled rows. Repeated draws are not additional independent customers.

| Scenario | Source subgroup / 3,000 | Sampled subgroup / 3,000 | Unique sampled customers |
| --- | ---: | ---: | ---: |
| financial_mix_shift | 712 | 1457 | 1749 |
| delinquency_mix_shift | 1027 | 1804 | 1738 |

Each corruption scenario separately started from the original policy-validation frame, removed labels, and edited the same seed-42 selection of 300 positions (10%). Edits were a missing September bill, the nonnumeric September bill string `not-a-number`, or unseen September repayment status `10`. Monitoring delegates validation to the scorer’s `inference.validate_batch` with unique per-position record IDs: missing values and unseen integral statuses remain scoreable; invalid nonnumeric values are quarantined. The frozen one-hot encoder ignores unseen status levels, while row-derived delay features still reflect their numeric values. Scoreability does not establish business validity of an unknown status.

Customer-level source IDs, draw order, weights, probabilities, sampling counts and corruption positions are saved only in ignored `artifacts/runtime/monitoring/d2b8c7f3a3de2b1d/`. Compact reports and this document contain aggregate results only.

## Measured labeled metrics

Values below preserve the exact JSON numbers. AP is average precision. These are descriptive benchmark metrics for unchanged histories, conditional on the frozen model. No monitoring confidence intervals were computed.

| Scenario | Scored | AP | ROC-AUC | Log loss | Brier | Risk PSI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| reference | 3000 | 0.5485792515601552 | 0.7762329282884964 | 0.43298871400379296 | 0.1361703025268774 | 0.004042708724205128 |
| financial_mix_shift | 3000 | 0.5860123483389065 | 0.7927554045979885 | 0.43136130528621486 | 0.13583330518266035 | 0.04650091495912625 |
| delinquency_mix_shift | 3000 | 0.5925642664368925 | 0.7806730430221258 | 0.4985676382530739 | 0.16456338350146382 | 0.1875209465944347 |

The delinquency mix shift had higher AP but worse log loss and Brier than the unchanged reference. Composition changes can move ranking and probability-quality metrics differently; this does not establish a changed outcome mechanism.

## Data quality and corruption

| Scenario | Input | Scored | Quarantined | Raw missing cells | Unknown status cells | Risk PSI | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| reference | 3000 | 3000 | 0 | 0 | 0 | 0.004042708724205128 | 0 |
| financial_mix_shift | 3000 | 3000 | 0 | 0 | 0 | 0.04650091495912625 | 1 |
| delinquency_mix_shift | 3000 | 3000 | 0 | 0 | 0 | 0.1875209465944347 | 3 |
| corruption_missing | 3000 | 3000 | 0 | 300 | 0 | 0.009229565306484696 | 6 |
| corruption_nonnumeric | 3000 | 2700 | 300 | 0 | 0 | 1.165866406424884 | 14 |
| corruption_unseen_status | 3000 | 3000 | 0 | 0 | 300 | 0.02049447623583174 | 3 |

Development and the unchanged reference had no raw missing values, nonnumeric/nonfinite values, unknown status levels or quarantine. Missing corruption produced 300 missing `bill_amt_2005_09` cells (rate 0.1), all scoreable. Nonnumeric corruption produced 300 nonnumeric cells in that column and quarantined exactly those rows. Unseen-status corruption produced 300 unknown `pay_status_2005_09` cells (column rate 0.1; overall six-status-cell rate 0.016666666666666666), all scoreable. All record counts reconciled. Corruption performance metrics are **N/A**: original outcomes cannot validate edited financial histories.

## Distribution diagnostics

PSI bins use finite development deciles with duplicate boundaries removed, explicit underflow/overflow outside development minimum/maximum, and a separate missing bin. The last interior interval includes its upper boundary. Each count distribution is normalized; `epsilon=1e-6` is added to every proportion; both distributions are renormalized before computing `sum((current-reference)*log(current/reference))`. Demonstration review thresholds are PSI ≥ **0.2** and raw missingness ≥ **0.05**. Unknown categories and quarantine also trigger warnings.

The design proposed configurable demonstration thresholds. Delivered values are
module constants (`PSI_WARNING_THRESHOLD`, `MISSING_WARNING_THRESHOLD`); the
current CLI/function exposes no threshold-configuration argument. They remain
heuristics rather than operational alarm limits.

Every PSI uses development as its reference. Unscored probabilities enter the missing risk bin. Nonnumeric raw values appear as missing in numeric diagnostic distributions; quarantined rows have no derived features. Thus, nonnumeric-corruption PSI reflects validation/missing-bin behavior as well as the distribution of scored rows. Warnings are heuristic synthetic data/prediction-shift diagnostics, not proof of concept drift or grounds for automatic retraining.

[The risk-distribution plot](../reports/phase5_monitoring/risk_distribution.svg) compares actual normalized counts for development, the unchanged policy-validation reference and both mix shifts on identical development-defined risk bins, including tails/missing. It is not a plot of PSI scores.

| Scenario | Review warnings |
| --- | --- |
| reference | None |
| financial_mix_shift | Review distribution shift: latest_utilization_proxy |
| delinquency_mix_shift | Review distribution shift: recent_delinquency_count; Review distribution shift: maximum_positive_delay; Review distribution shift: recent_history_delay_contrast |
| corruption_missing | Review distribution shift: bill_amt_2005_09; Review distribution shift: latest_utilization_proxy; Review distribution shift: mean_utilization_proxy; Review distribution shift: bill_balance_change; Review distribution shift: bill_volatility_proxy; Review missingness |
| corruption_nonnumeric | Review distribution shift: bill_amt_2005_09; Review distribution shift: recent_delinquency_count; Review distribution shift: maximum_positive_delay; Review distribution shift: recent_history_delay_contrast; Review distribution shift: latest_utilization_proxy; Review distribution shift: mean_utilization_proxy; Review distribution shift: bill_balance_change; Review distribution shift: bill_volatility_proxy; Review distribution shift: mean_payment; Review distribution shift: zero_payment_count; Review distribution shift: payment_to_prior_bill_missing; Review distribution shift: aggregate_payment_balance_missing; Review distribution shift: p_default; Review schema validity or unknown categories |
| corruption_unseen_status | Review distribution shift: pay_status_2005_09; Review distribution shift: maximum_positive_delay; Review schema validity or unknown categories |

Complete feature-level diagnostics comprise 198 distribution rows across six
scenarios. Exact PSI values and all warnings remain in
[monitoring.csv](../reports/phase5_monitoring/monitoring.csv) and
[monitoring.json](../reports/phase5_monitoring/monitoring.json). The compact tables
above show measured outcomes and validation behavior; the underlying evidence
has not been regenerated.

## Provenance and verification

Accepted run: `9ca62eca2665438c9c97b4889413acfa`. Base: `xgboost_05_engineered_none`; probability mapping: raw identity; positive class: 1. Prediction-time availability is the released month-end snapshot for existing accounts. This historical Taiwanese benchmark does not establish contemporary representativeness, new-applicant underwriting validity, causal intervention effects, actual profit or observed temporal drift.

[Artifact identities](setup.md#artifact-identities) and the unchanged
[execution receipt](../reports/phase5_monitoring/execution_checks.json) retain
freeze, source/test, input and readiness hashes. The payload and historical copy
are needed to verify private inputs; those files are not public clone contents.

Post-run checks verified all **48** frozen source/test file hashes unchanged and all **106** accepted artifact hashes unchanged. All six scenario counts and 198 JSON/CSV distribution rows reconcile. Seed-42 draw order, weights/probabilities, source IDs, sampling counts and the 300 corruption positions reproduce exactly. All 52 plotted risk-bin counts/proportions match the report. The command’s built-in preflight also verified freeze/review binding, accepted dependency pins, source/feature contracts, assignments and reference-model identities.

The allowed-partition loader traversed shared CSV row strings for complete identifier/schema integrity and routing; conversion was limited to development and policy-validation values/outcomes. No final-test outcome was converted, evaluated or interpreted. Full-input byte hashing is an integrity check, not outcome analysis. Source/tests, accepted artifacts and shared logs were not edited.

Compact artifacts: [monitoring.json](../reports/phase5_monitoring/monitoring.json), [monitoring.csv](../reports/phase5_monitoring/monitoring.csv), [risk_distribution.svg](../reports/phase5_monitoring/risk_distribution.svg), [execution_checks.json](../reports/phase5_monitoring/execution_checks.json). The execution receipt contains generated-artifact and ignored-runtime receipt hashes.

Final-test evaluation is separate from the monitoring demonstration. Monitoring results do not change the frozen candidate or policy.
