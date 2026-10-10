# Synthetic monitoring report

The real-data monitoring run completed successfully with the frozen existing-account risk bundle. Development supplied 18,000 rows and distribution bins; the unchanged policy-validation cohort supplied 3,000 rows. The mix shifts are synthetic resampled population compositions, not observed temporal drift. No model fitting, policy reselection, final-test conversion or evaluation occurred.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m credit_risk.phase5 monitor --output reports/phase5_monitoring
```

Report written UTC: `2026-10-09T21:30:36.593280+00:00`. Command exit code: **0**. Tests were not rerun for this execution. Post-run checks are recorded in [execution_checks.json](../reports/phase5_monitoring/execution_checks.json).

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

### Exact PSI: reference and mix shifts

| Feature | reference | financial_mix_shift | delinquency_mix_shift |
| --- | ---: | ---: | ---: |
| limit_bal | 0.004968617125382423 | 0.03750082291290911 | 0.026656400771805512 |
| pay_status_2005_04 | 0.0009746208303680197 | 0.029259073758783866 | 0.06040657080212318 |
| pay_status_2005_05 | 0.0006271520551203332 | 0.029727749804724302 | 0.005900096447069977 |
| pay_status_2005_06 | 0.0017167491412237253 | 0.04362189858442961 | 0.03477006538625453 |
| pay_status_2005_07 | 0.0009460603364606355 | 0.04517196765157812 | 0.07222354761238065 |
| pay_status_2005_08 | 0.0011285359361109652 | 0.04271684779504015 | 0.09067957704836191 |
| pay_status_2005_09 | 0.0009493934123302463 | 0.04025226217926423 | 0.16368059171036559 |
| bill_amt_2005_04 | 0.004466438167275372 | 0.047319310333083044 | 0.004898867684736041 |
| bill_amt_2005_05 | 0.007458210014157814 | 0.049616242646954356 | 0.009224198533743054 |
| bill_amt_2005_06 | 0.0032600634056510146 | 0.05772343979637112 | 0.00506656597938578 |
| bill_amt_2005_07 | 0.0017894905086618526 | 0.06647215592904615 | 0.003628051560109461 |
| bill_amt_2005_08 | 0.001474016058173352 | 0.08653635030094627 | 0.006512676775271539 |
| bill_amt_2005_09 | 0.0025951973086447986 | 0.09162473579528355 | 0.02432380421015542 |
| pay_amt_2005_04 | 0.00266056023242104 | 0.002752757746623524 | 0.008356728368081401 |
| pay_amt_2005_05 | 0.005012211174804422 | 0.007312405250760174 | 0.012291217705436244 |
| pay_amt_2005_06 | 0.005027327948893493 | 0.021123635308385368 | 0.022210286719026823 |
| pay_amt_2005_07 | 0.0019792864727251635 | 0.010018087706391522 | 0.010663403539203524 |
| pay_amt_2005_08 | 0.00032139266713630604 | 0.016249473170269972 | 0.02576751047479889 |
| pay_amt_2005_09 | 0.0036489096739935746 | 0.02034890295899703 | 0.03230861215848661 |
| recent_delinquency_count | 0.00016725525622854394 | 0.001323559688622028 | 0.2831383283925325 |
| maximum_positive_delay | 0.00038767049451706863 | 0.009811909610028178 | 0.283050161884148 |
| recent_history_delay_contrast | 0.0007789881247403365 | 0.010982610329576595 | 0.23126907339628827 |
| latest_utilization_proxy | 0.0031493735608227676 | 0.2103611512666674 | 0.02901211838405035 |
| mean_utilization_proxy | 0.0026487078338149218 | 0.1462297167424607 | 0.01377959934672165 |
| bill_balance_change | 0.0053574165105383115 | 0.07946043672428338 | 0.019946706415576984 |
| bill_volatility_proxy | 0.003170182595731217 | 0.06421019585782425 | 0.015177812302302042 |
| mean_payment | 0.0026111438656749196 | 0.010735105748302045 | 0.020515743925077448 |
| zero_payment_count | 0.003116273306351433 | 0.0092174044674031 | 0.0772641242984899 |
| payment_to_prior_bill_proxy | 0.0018527631122389723 | 0.07102485888949603 | 0.055313572082802624 |
| payment_to_prior_bill_missing | 0.0 | 0.0 | 0.0 |
| aggregate_payment_balance_proxy | 0.0016071744002185016 | 0.08643793381342199 | 0.015958053259317016 |
| aggregate_payment_balance_missing | 0.0 | 0.0 | 0.0 |
| p_default | 0.004042708724205128 | 0.04650091495912625 | 0.1875209465944347 |

### Exact PSI: unlabeled corruption

| Feature | corruption_missing | corruption_nonnumeric | corruption_unseen_status |
| --- | ---: | ---: | ---: |
| limit_bal | 0.004968617125382423 | 0.004968617125382423 | 0.004968617125382423 |
| pay_status_2005_04 | 0.0009746208303680197 | 0.0009746208303680197 | 0.0009746208303680197 |
| pay_status_2005_05 | 0.0006271520551203332 | 0.0006271520551203332 | 0.0006271520551203332 |
| pay_status_2005_06 | 0.0017167491412237253 | 0.0017167491412237253 | 0.0017167491412237253 |
| pay_status_2005_07 | 0.0009460603364606355 | 0.0009460603364606355 | 0.0009460603364606355 |
| pay_status_2005_08 | 0.0011285359361109652 | 0.0011285359361109652 | 0.0011285359361109652 |
| pay_status_2005_09 | 0.0009493934123302463 | 0.0009493934123302463 | 1.1625150995274083 |
| bill_amt_2005_04 | 0.004466438167275372 | 0.004466438167275372 | 0.004466438167275372 |
| bill_amt_2005_05 | 0.007458210014157814 | 0.007458210014157814 | 0.007458210014157814 |
| bill_amt_2005_06 | 0.0032600634056510146 | 0.0032600634056510146 | 0.0032600634056510146 |
| bill_amt_2005_07 | 0.0017894905086618526 | 0.0017894905086618526 | 0.0017894905086618526 |
| bill_amt_2005_08 | 0.001474016058173352 | 0.001474016058173352 | 0.001474016058173352 |
| bill_amt_2005_09 | 1.1649958443858146 | 1.1649958443858146 | 0.0025951973086447986 |
| pay_amt_2005_04 | 0.00266056023242104 | 0.00266056023242104 | 0.00266056023242104 |
| pay_amt_2005_05 | 0.005012211174804422 | 0.005012211174804422 | 0.005012211174804422 |
| pay_amt_2005_06 | 0.005027327948893493 | 0.005027327948893493 | 0.005027327948893493 |
| pay_amt_2005_07 | 0.0019792864727251635 | 0.0019792864727251635 | 0.0019792864727251635 |
| pay_amt_2005_08 | 0.00032139266713630604 | 0.00032139266713630604 | 0.00032139266713630604 |
| pay_amt_2005_09 | 0.0036489096739935746 | 0.0036489096739935746 | 0.0036489096739935746 |
| recent_delinquency_count | 0.00016725525622854394 | 1.161965848535295 | 0.026888833479644103 |
| maximum_positive_delay | 0.00038767049451706863 | 1.162059282741698 | 1.162059282741698 |
| recent_history_delay_contrast | 0.0007789881247403365 | 1.1624069086479731 | 0.1490588525707174 |
| latest_utilization_proxy | 1.165689722855096 | 1.165689722855096 | 0.0031493735608227676 |
| mean_utilization_proxy | 1.1646986243944093 | 1.1646986243944093 | 0.0026487078338149218 |
| bill_balance_change | 1.1681353251856046 | 1.1681353251856046 | 0.0053574165105383115 |
| bill_volatility_proxy | 1.1649088615415282 | 1.1649088615415282 | 0.003170182595731217 |
| mean_payment | 0.0026111438656749196 | 1.1665207694976776 | 0.0026111438656749196 |
| zero_payment_count | 0.003116273306351433 | 1.165001321279436 | 0.003116273306351433 |
| payment_to_prior_bill_proxy | 0.0018527631122389723 | 0.06567090795068427 | 0.0018527631122389723 |
| payment_to_prior_bill_missing | 0.0 | 1.1618249396469476 | 0.0 |
| aggregate_payment_balance_proxy | 0.14823901767693365 | 0.14823901767693365 | 0.0016071744002185016 |
| aggregate_payment_balance_missing | 0.0 | 1.1618249396469476 | 0.0 |
| p_default | 0.009229565306484696 | 1.165866406424884 | 0.02049447623583174 |

## Provenance and verification

Accepted run: `9ca62eca2665438c9c97b4889413acfa`. Base: `xgboost_05_engineered_none`; probability mapping: raw identity; positive class: 1. Prediction-time availability is the released month-end snapshot for existing accounts. This historical Taiwanese benchmark does not establish contemporary representativeness, new-applicant underwriting validity, causal intervention effects, actual profit or observed temporal drift.

| Identity | SHA-256 |
| --- | --- |
| Accepted freeze content | `89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b` |
| Accepted freeze manifest file | `0cd8c5c63e90ffc159acfa5fb63d10affeda015f885171e3bde9b4c08402e6f1` |
| Accepted bundle | `45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd` |
| Frozen Phase 5 source/test map | `816b8cce9ecd1327f94d971d0922b45d22671b1a9a4a1c085360c491f56f0130` |
| Phase 5 readiness file | `5d46230e76887c1b0a55acf23be86730c834e822d279b79b095a8977b936d144` |

Input byte hashes verified against the accepted freeze:

| Input | SHA-256 |
| --- | --- |
| `artifacts/feature_contract_v1_1.json` | `4adb6745e582e551239b9e999d0128649fdaff0b1f63deebfea6f538ecc2eeae` |
| `artifacts/phase1_export_manifest.json` | `6157949db2e77b548d7de831f196b5d6506bd9c8e28dc3bd6290401f2be0e81a` |
| `artifacts/split_checks/840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537.json` | `840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537` |
| `artifacts/split_manifest.csv` | `775f9862fb5b97095c81fdae440d4acb7fd52f692a216b6284e879db5e4d5e4c` |
| `data/processed/audit_attributes.csv` | `54f7869afe47e2a65e138fcf71b5ab0f69c60e7413875b76498e6df82a1f3204` |
| `data/processed/financial_features_v1.csv` | `4dc8498776fbe56b64d75ff3cd79257275ad7657cc133aaa08457b27c1cc6e7e` |
| `data/processed/labels.csv` | `ecb12689643cb256d1707338f695d22fe8c28bce70c985f7c2fd6247e8080f2f` |
| `data/raw/default of credit card clients.xls` | `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933` |

Post-run checks verified all **48** frozen source/test file hashes unchanged and all **106** accepted artifact hashes unchanged. All six scenario counts and 198 JSON/CSV distribution rows reconcile. Seed-42 draw order, weights/probabilities, source IDs, sampling counts and the 300 corruption positions reproduce exactly. All 52 plotted risk-bin counts/proportions match the report. The command’s built-in preflight also verified freeze/review binding, accepted dependency pins, source/feature contracts, assignments and reference-model identities.

The allowed-partition loader traversed shared CSV row strings for complete identifier/schema integrity and routing; conversion was limited to development and policy-validation values/outcomes. No final-test outcome was converted, evaluated or interpreted. Full-input byte hashing is an integrity check, not outcome analysis. Source/tests, accepted artifacts and shared logs were not edited.

Compact artifacts: [monitoring.json](../reports/phase5_monitoring/monitoring.json), [monitoring.csv](../reports/phase5_monitoring/monitoring.csv), [risk_distribution.svg](../reports/phase5_monitoring/risk_distribution.svg), [execution_checks.json](../reports/phase5_monitoring/execution_checks.json). The execution receipt contains generated-artifact and ignored-runtime receipt hashes.

Final-test evaluation is separate from the monitoring demonstration. Monitoring results do not change the frozen candidate or policy.
