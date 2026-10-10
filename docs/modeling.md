# Modeling and partition isolation

The modeling workflow compares financial-history classifiers for an existing
account's released next-month default. Model choice uses development evidence;
calibration, policy selection and final evaluation remain separate. The target is
`default_next_month`, positive class `1`, with the availability assumption in the
[data contracts](data_contracts.md).

## Frozen partitions

| Partition | Rows | Financial-profile groups | Permitted use |
| --- | ---: | ---: | --- |
| Development | 18,000 | 17,508 | EDA, feature/weighting comparisons, tuning, base selection and fitting |
| Calibration | 4,500 | 4,378 | Probability mappings for the fixed base model |
| Policy validation | 3,000 | 2,919 | Mapping selection, simulated cutoff selection and descriptive diagnostics |
| Final test | 4,500 | 4,378 | Evaluation of frozen candidates and policies |

Assignments use seed 42 and stratified group-aware allocation at target shares
60/15/10/15. Fingerprints use the 19 raw financial predictors without labels,
identifiers or demographics. Identical profiles remain in one partition and one
development fold; different customers are retained. Each of five frozen
development folds has 3,600 rows. This is a held-out customer design, not a
chronological split; customer ID is not a timestamp.

The [split manifest](../artifacts/split_manifest.csv) and
[split summary](../reports/split_summary.json) retain assignments and counts.
The summary preserves its original diagnostic-reader/feature-hash checkpoint.
[Canonical split validation](../artifacts/split_checks/840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537.json)
subsequently verified the same assignments under the revised feature contract;
historical pending annotations were not overwritten.
Earlier complete-source integrity/stratification reads and CSV-string routing are
disclosed in the [access record](test-exposure-log.md). The test was isolated from
model-oriented analysis, not from every historical byte or string traversal.

## Features and preprocessing

The raw contract has 19 financial predictors; the combined contract adds 13
deterministic row features. Identifiers, target and all four demographic fields
are excluded. Row arithmetic may precede splitting; learned statistics may not.

Each fit uses a scikit-learn `Pipeline`/`ColumnTransformer`: numeric median
imputation, logistic scaling where appropriate, categorical mode imputation and
unknown-safe one-hot encoding. Statistics, category vocabularies and balanced
weights are fitted only on the relevant training rows. Held-out sentinel tests
protect that boundary. Stable transformed names support coefficient and SHAP
interpretation. No resampling is used in the core comparison.

## Candidates and bounded search

| Family | Role | Completed configurations | Five-fold search fits |
| --- | --- | ---: | ---: |
| Constant-prior dummy | Probability baseline; separate majority hard reference | No randomized search | No search fits |
| Regularized logistic regression | Interpretable reference | 12 | 60 |
| Random forest | Nonlinear reference | 12 | 60 |
| XGBoost | Bounded boosting candidate | 24 | 120 |

`RandomizedSearchCV` scores average precision (AP), with frozen folds, seed 42,
one search worker and controlled native threads. Initial ceilings were 12/15/25;
actual budgets were 12/12/24, including raw/combined and unweighted/balanced
variants. Ceilings are limits, not minimum required search sizes. Three sampled
settings per logistic/forest family and six for XGBoost were each crossed with
both feature sets and both weighting choices, preserving matched comparisons. XGBoost tunes bounded tree counts without early stopping or a global
validation `eval_set`. Completed search fitting took 533.734 seconds. Additional
profile/OOF/final-development fits are separately recorded in the
[development report](../reports/phase3.md).

ROC-AUC, log loss, Brier score, fold variation and fit time accompany AP. Fold
means and pooled OOF metrics are distinct; AP is not unlabeled trapezoidal
PR-AUC. Accuracy and the majority hard prediction are not the probability
selection criterion.

## Selection and measured development findings

The rule takes maximum mean development CV AP, admits candidates within absolute
0.01 AP, then compares log loss with the declared 0.001 small-loss tolerance and
simplicity. D014 made the design's qualitative small-loss tie explicit at 0.001
before search; D015 restricted selection to the 48 declared search configurations,
excluding earlier untuned baselines. See [technical decisions](decision-log.md#bounded-model-comparison-and-selection--d014d017).
These are practical tolerances, not significance tests. Seventeen
candidates met the AP floor; two XGBoost models met the small-loss ceiling. The
100-tree candidate was retained over the near-tied 200-tree candidate.

Within the small-loss set, the recorded order is logistic, forest, XGBoost; fewer
trees; shallower trees (unbounded last); raw predictors; unweighted fitting; lower
exact log loss; faster measured inference; higher AP; then stable candidate ID.
Runtime cannot override AP/loss eligibility or the exact-loss tie-break.

The selected identity is `xgboost_05_engineered_none`: combined financial
features, no class weighting, 100 trees. Its fold-average AP/ROC-AUC/log
loss/Brier were 0.56125/0.78350/0.42652/0.13372. All 24 matched combined-feature
contrasts improved AP/log loss/Brier; weighting worsened log loss/Brier in all
24 matched contrasts. These are development-sample findings, not independent
test improvements. See the [selection table](../reports/phase3_selection_candidates.csv)
and [feature/weight contrasts](../reports/phase3_controlled_comparisons_accepted.csv).

The selected pipeline fits development only. Calibration does not refit it;
final-test rankings do not change it. The forest's higher final-test AP is
reported in [evaluation](../reports/results.md), while the original selection
remains fixed. Historical training commands require preserved source, locks,
inputs and receipts; [setup](setup.md#historical-reproduction) describes that
dependency rather than treating training as a fresh-clone setup step.
