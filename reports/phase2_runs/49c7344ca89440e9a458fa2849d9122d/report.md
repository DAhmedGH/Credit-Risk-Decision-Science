# Phase 2 measured development baselines

MLflow parent run: `49c7344ca89440e9a458fa2849d9122d`. Five frozen development folds; no champion frozen.
Sample fold standard deviations are descriptive, not confidence intervals.

| Model | Features | Weighting | Average precision mean ± SD | ROC-AUC | Log loss | Brier | Fit seconds mean |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| dummy | raw | none | 0.22117 ± 0.00012 | 0.50000 | 0.52838 | 0.17225 | 0.054 |
| logistic | raw | none | 0.53443 ± 0.02023 | 0.76545 | 0.43924 | 0.13727 | 0.169 |
| logistic | raw | balanced | 0.53282 ± 0.02056 | 0.76576 | 0.56605 | 0.18563 | 0.234 |
| logistic | engineered | none | 0.54076 ± 0.02194 | 0.77107 | 0.43627 | 0.13622 | 0.282 |
| logistic | engineered | balanced | 0.53724 ± 0.02216 | 0.77140 | 0.56178 | 0.18457 | 0.335 |
| random_forest | raw | none | 0.54878 ± 0.02212 | 0.77457 | 0.43192 | 0.13552 | 4.769 |
| random_forest | raw | balanced | 0.54911 ± 0.02147 | 0.77594 | 0.48863 | 0.15708 | 4.968 |
| random_forest | engineered | none | 0.55279 ± 0.01906 | 0.77926 | 0.43000 | 0.13501 | 7.161 |
| random_forest | engineered | balanced | 0.55049 ± 0.02099 | 0.77943 | 0.47132 | 0.15100 | 7.089 |

These are fold averages. Separate pooled OOF metrics are in comparison.csv;
pooled ranking metrics need not equal the mean of the fold metrics.

| Controlled comparison | Variant | Δ average precision | Δ log loss |
| --- | --- | ---: | ---: |
| engineered_minus_raw | logistic/engineered/none | +0.00633 | -0.00296 |
| balanced_minus_none | logistic/raw/balanced | -0.00161 | +0.12682 |
| balanced_minus_none | logistic/engineered/balanced | -0.00352 | +0.12551 |
| engineered_minus_raw | logistic/engineered/balanced | +0.00442 | -0.00427 |
| engineered_minus_raw | random_forest/engineered/none | +0.00401 | -0.00192 |
| balanced_minus_none | random_forest/raw/balanced | +0.00033 | +0.05671 |
| balanced_minus_none | random_forest/engineered/balanced | -0.00231 | +0.04132 |
| engineered_minus_raw | random_forest/engineered/balanced | +0.00137 | -0.01731 |

Majority-class hard-prediction reference (separate from probability metrics):

| Fold | Fit majority class | Default recall | Accuracy (reference only) |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0.00000 | 0.77889 |
| 1 | 0 | 0.00000 | 0.77861 |
| 2 | 0 | 0.00000 | 0.77889 |
| 3 | 0 | 0.00000 | 0.77889 |
| 4 | 0 | 0.00000 | 0.77889 |

Positive AP changes favor the right variant; negative log-loss changes favor it.
Weighting changes the fit objective and may worsen probability quality. No benefit is assumed.
Convergence, classification diagnostics and development-only worst squared-error cases
are saved per variant. A 0.5 diagnostic cutoff is not a lending policy.
The majority-class hard reference is separate from the constant-prior probability baseline.
No calibration, policy-validation, or final-test outcomes contributed to these comparisons.
These historical existing-account results are not validated new-loan underwriting evidence.
