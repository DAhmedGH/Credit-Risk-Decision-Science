# Phase 2: baselines and fold-safe machine learning

**Phase 2 complete: the scientific exit gate passes.** Acceptance date:
October 8, 2026. The measured development run is `49c7344ca89440e9a458fa2849d9122d`;
its parent and all nine child MLflow runs are **FINISHED**.
`runtime_validation_passed=true`, `champion_frozen=false`. Phase 3 has not begun.

These baselines estimate next-month default for existing credit-card accounts at
the released historical month-end snapshot, assuming all included history is
available then. They are development comparisons, without calibration,
policy-validation or final-test evaluation.

## Measured development comparison

Each row uses the same five frozen folds: 14,400 fit rows and 3,600 validation
rows per fold, covering 18,000 development customers. All values below are
**unweighted means across the five folds**; AP means average precision, not
trapezoidal PR-AUC. SD is the sample fold standard deviation (`ddof=1`). The
`engineered` variant includes the raw predictors plus engineered predictors.

| Model | Predictors | Weighting | Average precision mean ± SD | ROC-AUC mean | Log loss mean | Brier mean | Fit seconds mean |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Prior dummy | Raw | Unweighted | 0.22117 ± 0.00012 | 0.50000 | 0.52838 | 0.17225 | 0.054 |
| Logistic | Raw | Unweighted | 0.53443 ± 0.02023 | 0.76545 | 0.43924 | 0.13727 | 0.169 |
| Logistic | Raw | Balanced | 0.53282 ± 0.02056 | 0.76576 | 0.56605 | 0.18563 | 0.234 |
| Logistic | Raw + engineered | Unweighted | 0.54076 ± 0.02194 | 0.77107 | 0.43627 | 0.13622 | 0.282 |
| Logistic | Raw + engineered | Balanced | 0.53724 ± 0.02216 | 0.77140 | 0.56178 | 0.18457 | 0.335 |
| Random forest | Raw | Unweighted | 0.54878 ± 0.02212 | 0.77457 | 0.43192 | 0.13552 | 4.769 |
| Random forest | Raw | Balanced | 0.54911 ± 0.02147 | 0.77594 | 0.48863 | 0.15708 | 4.968 |
| Random forest | Raw + engineered | Unweighted | 0.55279 ± 0.01906 | 0.77926 | 0.43000 | 0.13501 | 7.161 |
| Random forest | Raw + engineered | Balanced | 0.55049 ± 0.02099 | 0.77943 | 0.47132 | 0.15100 | 7.089 |

All four metrics and fit/predict times have fold-wise measurements in
[fold_metrics.csv](phase2_runs/49c7344ca89440e9a458fa2849d9122d/fold_metrics.csv)
and means/SDs in [comparison.csv](phase2_runs/49c7344ca89440e9a458fa2849d9122d/comparison.csv).
The complete workflow took **204.68 seconds** according to the saved manifest;
mean fit time excludes scoring, serialization and tracking overhead. Timing
results describe this local execution and are not portable hardware benchmarks.

**Pooled OOF metrics are separate from fold averages.** For example, the
unweighted combined-feature forest has pooled AP **0.551747**, ROC-AUC
**0.778956**, log loss **0.429997** and Brier **0.135015**, versus fold-mean AP
**0.552791** and ROC-AUC **0.779257**. Pooled ranking metrics compare predictions
from different fitted pipelines. With equal fold sizes, decomposable log loss
and Brier equal their fold means up to rounding; AP and ROC-AUC need not. The
prior dummy has ROC-AUC 0.5 within each fold but pooled ROC-AUC 0.499871 because
training-fold prevalences differ slightly. Fold SDs are descriptive variation,
not confidence intervals or tests of a significant difference.

The **majority-class hard reference** predicts class 0 in every fold: default
recall **0**, undefined positive precision, and overall reference accuracy
**0.778833**. It misses all 3,981 development defaults despite that accuracy.
It is reported separately in
[majority_hard_reference.csv](phase2_runs/49c7344ca89440e9a458fa2849d9122d/majority_hard_reference.csv);
the probability baseline uses each fit fold's observed prior instead.

## Controlled findings and development errors

The following are differences between fold means under identical folds and
other declared settings. Higher AP and lower log loss/Brier are preferable.

| Comparison | Model / setting | Δ AP | Δ log loss | Δ Brier |
| --- | --- | ---: | ---: | ---: |
| Raw + engineered minus raw | Logistic, unweighted | +0.00633 | −0.00296 | −0.00105 |
| Raw + engineered minus raw | Logistic, balanced | +0.00442 | −0.00427 | −0.00106 |
| Raw + engineered minus raw | Forest, unweighted | +0.00401 | −0.00192 | −0.00051 |
| Raw + engineered minus raw | Forest, balanced | +0.00137 | −0.01731 | −0.00607 |
| Balanced minus unweighted | Logistic, raw | −0.00161 | +0.12682 | +0.04836 |
| Balanced minus unweighted | Logistic, raw + engineered | −0.00352 | +0.12551 | +0.04835 |
| Balanced minus unweighted | Forest, raw | +0.00033 | +0.05671 | +0.02155 |
| Balanced minus unweighted | Forest, raw + engineered | −0.00231 | +0.04132 | +0.01599 |

Engineered features produce **small AP improvements and lower log loss/Brier in
all four matched comparisons**. These changes do not establish statistical
significance. Balanced weighting produces mixed, small ranking changes and
**worsens log loss and Brier in all four comparisons**. ROC-AUC increases slightly
with weighting (0.00017–0.00137), which does not establish better probabilities.
The unweighted combined-feature forest has the highest baseline mean AP and the
lowest log loss here; **this does not select or freeze the final champion**.
Full differences are in
[controlled_comparisons.csv](phase2_runs/49c7344ca89440e9a458fa2849d9122d/controlled_comparisons.csv).

At the **diagnostic 0.5 cutoff**, combined-feature logistic recall rises from
0.35745 to 0.61618 with weighting, while false positives rise from 683 to 2,858.
For the combined-feature forest, recall rises from 0.36850 to 0.53580 and false
positives rise from 710 to 1,833. Thus weighting shifts the error tradeoff and
fit objective; it does not demonstrate policy value. These aggregate OOF diagnostics were reviewed without using held-out outcomes.
Development-only worst squared-error cases are saved as local artifacts; their
individual contents were not part of this acceptance review. Aggregate counts are in
[development_diagnostics.csv](phase2_runs/49c7344ca89440e9a458fa2849d9122d/development_diagnostics.csv);
customer-level cases remain ignored local artifacts. No threshold was selected.

**No warnings were recorded in any of the 45 folds.** All 20 logistic fits
converged in **67–131 iterations**, below the 2,000-iteration cap. Logistic L2
regularization shrinks fitted coefficients to control model complexity; C=1 is
an initial inverse-regularization setting, not a tuned result. Class weighting
changes the loss assigned to each class and can shift the fitted probabilities
away from the observed development prevalence, as the poorer proper scores here
illustrate. No post-hoc probability correction or calibration was applied.

## Pipeline and scientific contracts

The [resolved configuration](../configs/phase2.toml) declares one prior dummy
plus logistic/forest × raw/combined × unweighted/balanced: **nine variants,
45 fits, zero searched configurations**, seed 42. Folds execute sequentially;
forest workers and BLAS/OpenMP threads are limited to one.

| Family | Reproducible initial configuration |
| --- | --- |
| Prior dummy | `DummyClassifier(strategy="prior")`, fit-fold prevalence |
| Logistic | L2, C=1, `lbfgs`, `max_iter=2000`, `tol=1e-4` |
| Forest | 200 trees, unlimited depth, minimum leaf 5, `max_features="sqrt"`, bootstrap, one worker |

The explicit selector preserves the order of **19 raw financial predictors** or
**32 raw + engineered predictors**. ID, target, sex, age, education and marital
status cannot enter learned predictor matrices. Numeric median imputation,
categorical mode imputation and one-hot vocabularies are fitted on training
rows only; logistic numeric scaling is also fit-local. Unknown categories map
to zero indicators, and empty fit columns remain present with deterministic
imputation. Numeric columns retain allowlist order, followed by repayment-status
columns in documented oldest-to-latest order. Encoded names are saved per fold;
fold-specific vocabularies can yield different dimensions (74/76 raw, 87/89
combined), while names and ordering remain explicit within each saved pipeline.

Balanced weights are recomputed inside each estimator fit as
`n_fit / (2 * n_fit_class)`; forest weighting is `balanced`, not
`balanced_subsample`. Probability extraction looks up positive class **1** in
`classes_`, rather than assuming a column index. Duplicate financial-profile
groups remain together in every frozen partition and fold. No resampling,
all-development refit, calibration, policy selection, XGBoost, SHAP or final-test
analysis occurred.

## Acceptance evidence and attribution

The following successful ordinary-WSL commands are **reported WSL execution evidence**. They
were not rerun during this acceptance pass; exact test timestamps were not
supplied.

| Reported WSL command | Reported result, corroborated where artifacts exist |
| --- | --- |
| `bash scripts/bootstrap_phase2.sh` | Synthetic import/fit/save/load/local-MLflow checks and Ruff passed; **78 passed, 1 skipped**; dependency closure verified and locked |
| `.venv/bin/python -m credit_risk baseline-inputs --config configs/phase2.toml` | **18,000 development rows**, five × 3,600; `frozen_inputs_verified=true`, `heldout_outcomes_interpreted=false`, `predictive_fit=false`, development only |
| `.venv/bin/python -m credit_risk baselines --config configs/phase2.toml` | Actual nine-variant run above; runtime validation passed; no champion frozen |
| `python3 scripts/dev_db.py up` | Dedicated project PostgreSQL ready at **127.0.0.1:55432**; credentials remain in ignored `.env` |
| `CREDIT_RISK_SQL_TEST=1 .venv/bin/python -m pytest -q -p no:cacheprovider` | **79 passed in 39.26s; no skips** |

Acceptance separately performed **read-only artifact and fitted-state audits**:

- All **101 local artifact, 7 input/evidence, 30 maintained code/config and 6
  compact artifact hashes** match the run manifest. Logged artifact copies match
  their local counterparts. All **58 lock pins** match installed distributions;
  all 59 manifest-recorded distribution versions agree with the environment.
- Every variant has exactly **18,000 unique development OOF IDs**, one prediction
  per customer, correct frozen fold/fingerprint assignments, and consistent
  development outcomes. Every fit/validation ID hash, class count and fold-local
  weight reconciles. There is no cross-fold fingerprint overlap.
- All **45 trusted saved pipelines** were reloaded and scored on their original
  validation rows without refitting. Maximum prediction difference from saved
  OOF probabilities is **1.11×10⁻¹⁶** (required tolerance 1e-12).
- Learned medians, logistic means/variances, categorical imputations and
  vocabularies were checked against each fold's **training financial rows only**.
  Predictor allowlists, ordered names and class-1 mapping match fitted state.
- Independently recomputed AP, ROC-AUC, log loss and Brier reconcile with saved
  fold results within **1.11×10⁻¹⁶**. Fold means/sample SDs, pooled metrics,
  timings, all eight contrasts and confusion/reference tables also reconcile.
- All ten run metadata records are FINISHED, with correct parent/child links,
  local artifact destinations, seed, scope and resolved parameter evidence.

The numerical/fitted-state receipt is
[phase2_acceptance.json](phase2_acceptance.json). Separate validation inspected
provenance, folds, weighting, contrasts, convergence, diagnostics, dependencies
and tracking, then reviewed that receipt:
[independent acceptance review — PASS](../docs/validation-phase2-acceptance.md).
Behavioral tests cover held-out sentinels, unknown/missing categories, excluded
predictors, reversed class-column mapping, OOF guards, metric reconciliation,
serialization and real repeated local tracking. Their successful execution is
attributed to the reported WSL suites above, supplemented by prior fix verification.

Acceptance interpreted only saved **development OOF outcomes**. The full label
CSV and workbook were byte-hashed without decoding; audit attributes and
held-out outcomes were not opened. The original CLI streamed full label-row
strings for ID routing but converted only development outcomes; this distinction
is recorded in [test-exposure-log.md](../docs/test-exposure-log.md).

## Run identities and artifacts

Parent MLflow run: **`49c7344ca89440e9a458fa2849d9122d`**. Experiment:
`credit-risk-phase2-development-baselines`. All child runs below are FINISHED.

| Variant | MLflow child run ID |
| --- | --- |
| `dummy__raw__none` | `4593ebb8c5384a10b9c9c92863312f1d` |
| `logistic__raw__none` | `fae6572cb2e8443cbdc4580f6f475ddb` |
| `logistic__raw__balanced` | `96c9c67e25354c7b96f02315b799b4f0` |
| `logistic__engineered__none` | `9090e7e1698147589f64b69f362216bd` |
| `logistic__engineered__balanced` | `ec0e1d5bf7fe4cbb891a9294cc1969c3` |
| `random_forest__raw__none` | `a707f88a7320408887b350a14fb64336` |
| `random_forest__raw__balanced` | `2456a02662374cb7a3e0cddd3d6f8e5e` |
| `random_forest__engineered__none` | `aa8cd98635824b2aa7414a4afb35140b` |
| `random_forest__engineered__balanced` | `74d4b87493604c8d8e1216758e1ae3cc` |

| Location | Evidence |
| --- | --- |
| [Run report and compact tables](phase2_runs/49c7344ca89440e9a458fa2849d9122d/report.md) | Measured comparison, all fold metrics, controlled contrasts, majority reference and aggregate development diagnostics |
| [Provenance manifest](phase2_runs/49c7344ca89440e9a458fa2849d9122d/manifest.json) | Input/code/lock/artifact identities, configuration, dependencies, timings and run IDs |
| `artifacts/models/phase2/49c7344ca89440e9a458fa2849d9122d/` | Ignored execution context; nine OOF files, 45 fold pipelines, names/weights/warnings and customer-level development errors |
| `mlruns/` | Ignored explicit local tracking metadata and logged parent/child artifacts, using MLflow's default layout |
| [Acceptance receipt](phase2_acceptance.json) / [independent review](../docs/validation-phase2-acceptance.md) | Read-only validation and final gate disposition |

| Identity | SHA-256 |
| --- | --- |
| Original workbook | `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933` |
| Frozen split manifest | `775f9862fb5b97095c81fdae440d4acb7fd52f692a216b6284e879db5e4d5e4c` |
| Feature contract | `4adb6745e582e551239b9e999d0128649fdaff0b1f63deebfea6f538ecc2eeae` |
| Expanded `requirements.lock` (58 pins) | `b8f4f36250c998b0d9850d8d99d6968b6810c244c06aa7c1262bb28d91c00fd5` |
| Archived `requirements-phase1.lock` | `8ca35948b60fc22ce665588864982a468ef7bf362dd5fa61e9fd604d08eb4624` |
| Run code/config tree | `8f4a9975a50b1d87c2426ac3649391662efb6b9e48ae590caac920188e351bd0` |
| Run manifest | `2f5a31e8633ca751d63b5b4dbd43bd096812474954436e5df2e5ba3a88373761` |

Python **3.12.11**, scikit-learn **1.7.2**, MLflow skinny **3.3.2**. The run
records an explicit null Git commit because Git is unavailable in the original
workspace; source/config content hashes supply provenance. Git delivery remains
outstanding, without blocking the scientific Phase 2 gate. Tracking/model/raw
customer files and credentials are excluded by existing ignores. This acceptance
changed documentation/evidence only; raw files, splits, feature formulas,
configuration, dependency locks, code and completed run artifacts were preserved.

## Historical failures and resolutions

The `reports/phase2_checkpoint_78de644f03b0.md` (private historical evidence) preserves the complete
prior blocked/fix-only narrative. These historical records are superseded by
the measured acceptance above, not deleted or represented as successful runs.

- Initial original-environment dependency installation failed at PyPI DNS;
  fitting/smoke did not run, and modeling tests skipped. Preserved receipt:
  [phase2_verification.json](phase2_verification.json). Reported WSL bootstrap later
  validated the closure and archived the original Phase 1 lock before updating
  `requirements.lock`. The earlier missing-package blocker is resolved.
- Four initial fixture failures exposed `None` versus CSV-empty fold handling;
  normalization fixed them. NaN imputer-parameter serialization was also corrected
  and regression-tested. These were software corrections, not split changes.
- The reported real MLflow failure (**1 failed, 74 passed, 1 skipped**) was
  reproduced against 3.3.2. A custom top-level `mlruns/artifacts/<run-id>` could
  shadow metadata during FileStore discovery. New experiments use the supported
  default metadata/artifact layout; explicit local tracking still ignores remote
  environment configuration. Existing nondefault experiments require a **new
  experiment name**; all old runs/artifacts remain untouched.
- Child/parent failure-status and receipt cleanup is best effort and cannot mask
  the original exception. A temporary fixture cache assumption was corrected by
  adding deterministic filesystem fault injection. Successful tests use real
  MLflow, including repeated execution, retrieval, downloads and FINISHED status.
  Prior executed correction checks were: focused test **1 passed in 27.50s**,
  tracking module **4 passed in 38.91s**, Ruff passed, full fixture suite
  **78 passed, 1 skipped in 40.17s**, and three-model synthetic smoke passed.
  See [phase2_mlflow_fix.json](phase2_mlflow_fix.json),
  [prior independent review](../docs/validation-phase2.md), decision D012 and the
  [legacy recovery instructions](../docs/reproduction-phase2.md).

Phase 1 canonical xlrd agreement, counts, SQL/Python feature parity and frozen
integrity remain supported by [phase1.md](phase1.md) and its receipts. The user's
prior **4 enabled SQL tests passed in 2.37s**, two ingestion no-ops and
18,000-row-only EDA remain reported WSL historical evidence. The earlier statement
that no predictive training ran applies to Phase 1, not these completed baselines.

## Exit gate, limitations and next task

| Phase 2 requirement | Disposition |
| --- | --- |
| All declared baselines train from the CLI | PASS: reported WSL measured nine-variant workflow and 45 saved fits |
| Fit-local imputation, scaling, vocabularies and weighting | PASS: behavioral tests, inspected source and direct fitted-statistic checks |
| OOF/fold metrics reconcile; names and class-1 mapping are preserved | PASS: exact coverage and numerical/serialization audit |
| Controlled comparisons, convergence/errors and local tracking recorded | PASS: measured tables, no convergence warnings, ten FINISHED runs |
| Development-only choices with unchanged frozen groups/inputs | PASS: manifest/OOF/hash checks and exposure disclosure |
| Independent scientific acceptance | PASS: separate acceptance review; no unresolved integrity findings |

There is **no unresolved scientific or runtime Phase 2 blocker**. Outstanding
Git initialization/commit is a delivery limitation. No remote CI or fresh-volume
container rebuild is claimed. Results describe a historical Taiwanese
existing-account benchmark, without temporal/external validation, demonstrated
contemporary Canadian applicability, new-loan underwriting, fairness validation,
real profit, causal intervention effects, or calibrated/policy performance.
Small development differences and fold SDs are not uncertainty intervals.

Exact reproduction and manual verification commands are in
[reproduction-phase2.md](../docs/reproduction-phase2.md). Completed experiments
were not rerun for this acceptance. The subsequent [Phase 3 comparison](phase3.md) used the unchanged five folds,
bounded searches and the declared AP/log-loss/simplicity rule. No Phase 3
computation occurred during this Phase 2 acceptance check.
