# Phase 2 independent acceptance review

This technical summary preserves recorded findings and checks. Original review
documents and hash-bound receipts are retained privately. These checks were
performed at the dated checkpoint, not repeated for presentation cleanup.

Review date: October 8, 2026. Scope: completed fixed development baselines and
their artifacts, including the previously reviewed MLflow correction. No Phase 3
work or final champion selection is included.

Authoritative parent run: `49c7344ca89440e9a458fa2849d9122d`.
The inspected manifest is
`reports/phase2_runs/49c7344ca89440e9a458fa2849d9122d/manifest.json`, SHA-256
`2f5a31e8633ca751d63b5b4dbd43bd096812474954436e5df2e5ba3a88373761`.

## Evidence attribution and scope

The successful full-data baseline execution, dependency bootstrap, synthetic
smoke, lint and fixture checks are reported WSL execution evidence. The user also reports the
final enabled PostgreSQL suite passed **79 tests in 39.26s with no skips**; this
review did not rerun tests, SQL, installation or training. Existing independent
code and MLflow reviews remain in `docs/validation-phase2.md`.

This acceptance review performed read-only artifact, source, dependency and
tracking inspections described below. Only saved development OOF outcomes were
interpreted. The full label CSV and workbook were byte-hashed without decoding;
audit attributes and calibration/policy-validation/final-test outcomes were not
opened. Frozen assignments contain no outcomes. No model was fitted, no split
was regenerated, and no source/model/split/tracking artifact was changed.

The review recovered the scientific requirements from the project requirements,
design, phase plan, prior reviews, progress, decisions and exposure log. At the
start of this acceptance pass, report/progress still described the prior
checkpoint; those historical pending statements require the current measured
checkpoint to supersede them explicitly.

## Independent checks completed

| Contract | Read-only evidence and result |
| --- | --- |
| Provenance | All **101 model/output artifact hashes**, **7 input/evidence hashes**, **30 maintained code/config hashes**, and **6 compact artifact hashes** match the authoritative manifest. Its aggregate code hash matches the recorded code-file mapping. The source workbook, frozen split and feature contract preserve their Phase 1 identities. |
| Dependencies | All **58 expanded-lock pins** match installed distributions; all **59 distribution versions** recorded in the run manifest match the current environment. The archived original Phase 1 lock has its original SHA-256 `8ca35948b60fc22ce665588864982a468ef7bf362dd5fa61e9fd604d08eb4624`. |
| Frozen populations | The manifest retains 30,000 unique assignments. Every fingerprint has exactly one partition/fold destination. Each of the nine OOF files contains exactly the same **18,000 unique development IDs**, matching frozen folds and fingerprints, with finite class-1 probabilities. Development labels agree across all nine files. No held-out row enters an OOF file. |
| Fit/validation boundaries | All **45 fold evidence records** have the correct sorted fit-ID and validation-ID hashes: **14,400 fit / 3,600 validation** rows. Fit-class counts reconcile from development OOF labels, and every logged balanced weight equals `n_fit / (2 * n_fit_class)`; unweighted values equal one. |
| Parameters and names | Recorded parameters match declared seed-42 initial configurations, including logistic C=1/lbfgs and forest 200 trees/minimum leaf 5/one worker. Predictor names exclude ID, target and demographics. Raw encodings contain 74 or 76 named outputs; combined encodings contain 87 or 89, reflecting fold-local category vocabulary. Names remain unique and ordered within each fitted pipeline. |
| Convergence | Every fold reports convergence, zero convergence warnings, and an empty warning list. All **20 logistic fits** terminated in **67–131 iterations**, below the 2,000 limit. All 45 trusted pipeline files match their recorded hashes and have saved serialization-agreement evidence. |
| Tables and comparisons | For all nine variants, all four metric means/sample SDs and fit/predict timing means/sample SDs reconcile with the saved fold table. All **eight controlled contrasts** equal their declared right-minus-left differences. Pooled OOF metrics remain separately labeled. |
| Development errors | All nine aggregate 0.5-threshold confusion tables reconcile against saved OOF probabilities/outcomes. The five majority-reference rows correctly report class 0, zero positive recall and undefined precision. Error cases remain development-only artifacts; the threshold is diagnostic rather than a lending policy. |
| Local tracking | All **10 parent/child metadata records** are FINISHED in one experiment, with the default local metadata/artifact layout. Child parent links and positive-class parameters agree. Every logged parent/child artifact copy inspected is byte-identical to the corresponding local output. Tracking inspection made no mutations. |
| Modeling scope | The manifest and matching source record nine prespecified variants, five sequential frozen folds, 45 fits, zero searched configurations, class 1, seed 42 and one worker. The previously inspected pipelines place learned imputation/scaling/vocabularies inside each fold fit and map probabilities using `classes_`. No calibration, policy selection, XGBoost, SHAP, final-test evaluation or champion freeze is present. |

The review also inspected the completed read-only audit receipt,
`reports/phase2_acceptance.json`. It confirms all **45 trusted pipelines** were
reloaded and scored on their frozen validation rows, with a maximum saved-OOF
probability difference of **1.11e-16**. Independently recomputed fold metrics
agree within **1.11e-16**, and fold means/SDs/pooled metrics reconcile with local,
compact and MLflow results. The audit verifies fitted medians, scaling means and
variances, and categorical vocabularies against the corresponding training-fold
financial rows. This supplies direct fitted-state evidence beyond the separate
metadata/provenance checks performed by this review. Neither audit retrained
models or reran the user's test suite.

## Measured interpretation

These are development fold means, not final-test estimates:

| Variant | Average precision | Log loss | Brier score |
| --- | ---: | ---: | ---: |
| Prior dummy | 0.22117 | 0.52838 | 0.17225 |
| Logistic, raw, unweighted | 0.53443 | 0.43924 | 0.13727 |
| Logistic, raw, balanced | 0.53282 | 0.56605 | 0.18563 |
| Logistic, combined, unweighted | 0.54076 | 0.43627 | 0.13622 |
| Logistic, combined, balanced | 0.53724 | 0.56178 | 0.18457 |
| Forest, raw, unweighted | 0.54878 | 0.43192 | 0.13552 |
| Forest, raw, balanced | 0.54911 | 0.48863 | 0.15708 |
| Forest, combined, unweighted | 0.55279 | 0.43000 | 0.13501 |
| Forest, combined, balanced | 0.55049 | 0.47132 | 0.15100 |

Combined features modestly improve average precision and lower log loss in all
four matched comparisons: average-precision gains range **0.00137–0.00633**.
Balanced weighting has mixed small ranking changes (**−0.00352 to +0.00033 AP**)
and worsens log loss and Brier score in all four matched comparisons. Weighting
raises positive recall at the diagnostic 0.5 threshold while adding false
positives; that does not establish better probability estimates or policy value.

The combined unweighted forest has the highest baseline mean AP here. Phase 2
does not select a final champion; bounded tuning, XGBoost and the design's
selection rule belong to Phase 3. Fold SDs describe variation and are not
confidence intervals or proof that the small differences are significant.

## Findings and acceptance disposition

**Disposition: PASS — Phase 2 exit gate supported.** No unresolved
scientific-integrity finding was identified in the inspected code, artifacts,
contracts, comparisons or tracking state. The completed numerical/fitted-pipeline
audit closes the remaining acceptance dependency. The current report and
progress should identify this measured run as the completed Phase 2 checkpoint;
earlier blocked/fix-only checkpoints remain historical evidence.

Git still reports that the directory is not a repository. This is a delivery
limitation, not evidence of scientific contamination: the successful run records
an explicit null commit plus code/input hashes. Initialize and inspect/stage/
commit the maintained files and compact evidence when Git is available; preserve
ignored raw/customer data, credentials, tracking stores and bulky pipelines.

No temporal or external validation, calibrated probability assessment, fairness
conclusion, real profit claim or lending intervention effect follows from these
development baselines. The historical existing-account population and
prediction-time availability assumptions remain the documented limits. Stop at
Phase 2; the next task is Phase 3's small XGBoost compatibility/profile run and
bounded development searches, which have not run.

## Final documentation closeout

The review read the finalized measured report, progress, decision D013,
Phase 2 reproduction guide and README. All nine transcribed measurements, eight
contrasts, diagnostic counts, run identities, convergence limits and evidence
attributions agree with the inspected artifacts. The exit-gate table is
supported by the successful user execution plus the separate read-only audits.
Commands preserve the isolated environment, use the declared frozen exports and
local tracking, and stop within Phase 2.

Two documentation findings were corrected and re-inspected:

- **Low, README/Phase 1 reproduction guidance:** the expanded lock changes the
  lock identity protected by Phase 1's report-overwrite guard, so an unqualified
  recommendation to replay historical `reproduce` can fail against canonical
  evidence. README now starts with the supported Phase 2 commands; both guides
  and D013 disclose the historical cross-lock replay limitation and preserve
  existing reports. Future versioned Phase 1 replay is separate from this
  Phase 2 acceptance.
- **Low, `reports/phase2.md` error-analysis attribution:** aggregate OOF
  diagnostics were inspected, while individual worst-error case files were
  saved and hashed without reviewing their contents. The report now states
  that distinction explicitly. The inspected aggregate diagnostics satisfy
  the Phase 2 development-error requirement without implying case review.

Final documentation disposition: **PASS; no unresolved correction within the
requested Phase 2 checkpoint.** No model, test, SQL or training workflow was rerun
for this documentation closeout.
