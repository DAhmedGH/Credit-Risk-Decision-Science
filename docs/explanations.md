# Explanations and descriptive slices

The explanation layer describes fixed-model associations and selected diagnostic
cases. It does not estimate causal effects, certify fairness or select a policy
from final-test examples. Model identities and output scales remain explicit.

## Explained models and samples

| Analysis | Model and scale | Data boundary |
| --- | --- | --- |
| Logistic numeric coefficients | Fixed logistic reference; log-odds change per training standard deviation | Development-fitted preprocessing and coefficients |
| Logistic status contrasts | Category coefficient relative to a declared reference level | Training vocabulary; special statuses preserved |
| Global/dependence SHAP | Selected `xgboost_05_engineered_none`; raw default log odds | 100 fixed development background rows, 996 development explanation rows |
| Local SHAP cases | Same selected tree and raw-margin scale | Four diagnostic cases chosen on policy validation before final evaluation |
| Behavioral/demographic slices | Selected raw probabilities and a declared 0.5 detection threshold | Policy validation; descriptive only |

## Coefficients and TreeSHAP

Numeric logistic coefficients must be interpreted at their training-standardized
scale, rather than as a one-unit monetary change. Categorical contrasts use the
declared reference status, rather than comparing unrelated dummy coefficients.
Correlated financial histories can alter conditional associations. The
[numeric coefficient table](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/logistic_numeric_coefficients.csv)
and [status contrasts](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/logistic_categorical_contrasts.csv)
retain scales, reference levels and odds multipliers. These coefficients explain
the logistic reference, not the selected tree.

TreeSHAP uses fixed development background data with `model_output="raw"` and
interventional feature perturbation. Expected margin plus feature contributions
reconstructs the selected tree's raw default log odds; recorded maximum
additivity residual is 1.43148e-6. Passing the sum through a sigmoid recovers raw
risk, but applying a sigmoid to individual contributions is not a probability
attribution. The selected bundle uses raw identity mapping; sigmoid/isotonic
challengers are separate and are not explained by these figures.

The development global summary highlights recent positive delays, September
repayment status and utilization among prominent associations. This is the fixed
sample's model behavior, not proof of a causal repayment mechanism. Correlated
history fields may share attribution. The
[importance table](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/shap_development_importance.csv)
retains transformed feature names and mean absolute log-odds contributions.

The two dependence features are selected by mean absolute SHAP on the fixed
development sample, with feature-name ties. Local cases use the fixed 0.5
diagnostic: probabilities at least 0.5 predict default. Correct-default/false-alarm
cases take the highest probability; correct-nondefault/missed-default cases take
the lowest, with lowest customer ID resolving ties. This diagnostic threshold
is separate from the utility policy's strict acceptance cutoff.

## Existing figure gallery

| Figure | Interpretation |
| --- | --- |
| [Global SHAP summary](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/shap_global.png) | Distribution of raw-log-odds contributions on the development sample |
| [Positive-delay count dependence](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/shap_dependence_1.png) | Development feature values versus that feature's contribution |
| [September status-2 dependence](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/shap_dependence_2.png) | A specific encoded repayment-category contribution |

Correct-default, correct-nondefault, missed-default and false-alarm local
waterfall figures remain in the separately supplied bundle under
`explanations/shap_local_<category>.png`. They are unavailable in a source-only
clone. Cases were selected before final evaluation and were not replaced with
favorable test examples. See [the recorded explanation report](../reports/phase4.md).

## Descriptive slice contracts

Behavioral strata use development-defined reference cutoffs and fixed
policy-validation records. Demographic fields remain audit-only. Reported
demographic metrics are suppressed when a group has fewer than 100 records,
fewer than 20 defaults or fewer than 20 nondefaults. Unsupported values remain
unavailable rather than being presented as precise comparisons. Suppression
retains counts and class counts while withholding rates and probability summaries.
Behavioral slices are not subject to the demographic suppression rule.

Utilization uses development quartiles 0.022051293103448274, 0.31697 and
0.83686125, with cutpoint ties in the higher band and explicit tails/missingness.
Age bands are fixed under-30, 30–39, 40–49, 50-plus and unknown. Supported
calibration summaries are mean risk minus prevalence, plus log loss/Brier;
they are not complete subgroup reliability curves.

The [behavioral slices](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/behavioral_slices.csv),
[demographic audit](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/demographic_audit.csv)
and [descriptive metadata](../reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/descriptive_metadata.json)
retain definitions and counts. No demographic-specific policies are optimized.
Financial predictors may encode demographic proxies even when demographics are
excluded. These descriptive checks cannot establish fairness or external validity.
