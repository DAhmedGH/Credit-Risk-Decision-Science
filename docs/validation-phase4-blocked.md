# Independent Phase 4 scientific and code review

This technical summary preserves recorded findings and checks. Original review
documents and hash-bound receipts are retained privately. These checks were
performed at the dated checkpoint, not repeated for presentation cleanup.

Reviewed October 9, 2026 against the design, phase plan, accepted Phase 3
review/loading instructions, Phase 4 implementation and saved real-data run
`9ca62eca2665438c9c97b4889413acfa`.

**Disposition: BLOCKED for the complete Phase 4 exit gate.** The completed
calibration, policy and descriptive-analysis contracts pass independent
inspection. Required real SHAP execution and plots are missing because SHAP and
matplotlib are unavailable in the isolated environment. A full pre-test freeze
and an independent PASS receipt must follow that execution; they have not been
produced. Final-test evaluation remains prohibited.

The review owns this document only. It performed zero real-data fits, searches
or split/model mutations. Independent numerical checks interpreted only the
saved 3,000 policy-validation outcomes in `policy_predictions.npz`. Label-free
split assignments, saved model objects, compact descriptive summaries and
artifact bytes were inspected. The review did not open the source workbook,
label export, calibration outcomes or final-test outcomes. Synthetic fixture
fits remain separate from real-data experiment accounting.

## Evidence and independent measurements

The run is stored under the project’s durable
`artifacts/models/phase4/9ca62eca2665438c9c97b4889413acfa/`; compact evidence is
under `reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/`. It loads the
accepted base and four references from the durable Phase 3 backup, with no
dependency on the historical `/tmp` runtime. The input integrity path verifies
the inventory-bound selection manifest, accepted code archives, dependency
versions, source/export/split hashes, feature contract and exact original model
and metadata hashes before routing outcomes.

The final reviewed incomplete checkpoint contains **94 hash-verified
artifacts**. Its manifest identity is
`b075d624841fc51abccd3519da3ba4ba5d8f4c4e337acd416b52ef3c5154195a`.
Historical core code SHA is
`7ab37cae2add653a960d0773d542b4004e4cb26d5de8c1c726e33127cd039124`;
reviewed completion code SHA is
`a0c2e7808e42b3d3123f6aba21542f3c5718abe2094d2f3a27ff57f10162d311`.
The completion context independently matches current maintained source.
These identify a durable **incomplete checkpoint**, not a complete frozen bundle.

Every saved policy-prediction ID matches the frozen policy-validation IDs.
Development/calibration/policy ID hashes independently agree with label-free
assignments. Inspection confirms fingerprint groups cannot cross partitions or
development folds. Predictor frames use the financial allowlist; IDs, target
and audit demographics stay outside preprocessing and estimator inputs.

Independent metric calculations, without the production metric/selection
functions, reproduce the saved values within 1e-12:

| Probability variant | AP | ROC-AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: |
| Raw | 0.5485792516 | 0.7762329283 | 0.4329887140 | 0.1361703025 |
| Sigmoid | 0.5485792516 | 0.7762329283 | 0.4362283190 | 0.1370796970 |
| Isotonic | 0.5287544252 | 0.7754766927 | 0.4559940960 | 0.1367095427 |

Raw probabilities minimize validation log loss and are first in the declared
raw/sigmoid/isotonic simplicity order within 0.005 of the minimum. Sigmoid is
also inside that tolerance but cannot displace raw; isotonic is outside it.
The unchanged sigmoid ranking and lower isotonic AP are reported honestly.
All 30 fixed equal-width reliability-bin counts, means, observed frequencies
and sparse-bin flags were independently reconstructed. Log loss/Brier assess
overall probability quality; reliability diagrams diagnose calibration with
limited evidence in sparse bins.

`CalibratedClassifierCV(FrozenEstimator(base), ensemble=False)` uses the
installed sklearn 1.7.2 API. Its two fitted probability mappings each retain
one frozen accepted estimator. The workflow fits those mappings on the 4,500
calibration rows and selects on the separate 3,000 policy-validation rows.
The selected base’s loaded state hash matches the recorded before/after hash,
`bfdafb97487d3ae9cbbb836faed9e2ad`; original-process predictions on all permitted
partitions remain identical. Saved serialization evidence records exact
save/load probabilities and batch/single agreement at absolute tolerance
1e-12. The review inspected the loaded class mappings and frozen wrappers;
it did not refit calibrators or re-score raw source rows.

Exact original bytes for all five accepted pipelines independently match their
pinned Phase 3 binary identities. Selected/dummy/logistic/second-XGBoost loaded
object hashes also match the corresponding bundle references. Forest object
hashes can differ because structured tree-node arrays include padding bytes;
all 200 trees’ meaningful node fields, values, depth/count, fitted attributes
and parameters independently agree, and feature/preprocessing object hashes
agree. This padding difference does not represent a replacement fitted model.

## Policy and sensitivity audit

Independent arithmetic reproduces all eight base-policy rows and all 80
sensitivity-policy rows. For sensitivity rows, the retained maximum absolute
difference across recomputed counts, utilities, predicted expected utilities
and detection metrics is **0.0**. Each scenario’s empirical selection was
independently recomputed from the 201-point 0–1 grid plus explicit all/none;
the resulting acceptance mask agrees exactly, including lower-acceptance ties.
All fraction cutoffs equal the first excluded validation order statistic.
Their strict `p < cutoff` rule freezes numerical thresholds without recomputing
later sample percentiles. Boundary ties abstain.

Base G=50/L=500/C=0 gives analytic cutoff 50/550. Analytic acceptance selects
760 rows, with 47 observed benchmark defaults and utility 12,150 (4.05 per
customer). The validation-selected empirical cutoff 0.085 accepts 681 rows,
including 36 benchmark defaults, with utility 14,250 (4.75 per customer).
Accept-all utility is -215,200; abstain-all utility is zero with undefined
accepted default rate. These are selection-sample results in synthetic,
dimensionless units and cannot establish actual profit or causal benefit.

| G | L | C | Analytic cutoff | Analytic utility | Empirical cutoff | Empirical accepted | Empirical utility |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 250 | 0 | 0.090909 | 6,075 | 0.085 | 681 | 7,125 |
| 25 | 500 | 0 | 0.047619 | 425 | 0.060 | 301 | 2,275 |
| 25 | 750 | 0 | 0.032258 | -1,200 | Abstain all | 0 | 0 |
| 50 | 250 | 0 | 0.166667 | 33,450 | 0.180 | 1,783 | 33,950 |
| 50 | 500 | 0 | 0.090909 | 12,150 | 0.085 | 681 | 14,250 |
| 50 | 750 | 0 | 0.062500 | 4,000 | 0.060 | 301 | 7,050 |
| 100 | 250 | 0 | 0.285714 | 125,150 | 0.320 | 2,372 | 129,050 |
| 100 | 500 | 0 | 0.166667 | 66,900 | 0.180 | 1,783 | 67,900 |
| 100 | 750 | 0 | 0.117647 | 36,750 | 0.115 | 1,092 | 37,800 |
| 50 | 500 | 5 | 0.081818 | 10,470 | 0.085 | 681 | 10,845 |

The unfavorable G=25/L=750 cell is retained: analytic acceptance selects 14
rows and loses 1,200 benchmark units; empirical selection abstains on all.
Processing cost is charged once per accepted row. Historical limits/balances
are predictors rather than synthetic new-loan exposures. Detection correctly
treats abstention as the positive action and default as the positive outcome;
zero denominators remain undefined.

## Explanations and remaining limitations

The 26 saved standardized logistic slopes match the accepted logistic
reference’s fitted coefficients and development-imputation/scaling statistics.
All 63 categorical coefficients and explicit contrasts agree with the accepted
one-hot model and the lowest learned category reference. They are conditional
model associations, including regularization and correlated predictors.

All four validation diagnostic categories are available, and independent
selection reproduces the saved IDs: highest probability for correct defaults
and false alarms, lowest probability for correct nondefaults and missed
defaults, with smallest-ID tie breaking at a fixed 0.5 diagnostic threshold.
Behavioral/demographic group counts reconcile to 3,000 for each attribute.
Demographic suppression exactly follows n<100 or either class count<20 and
suppresses all probability/rate summaries while retaining counts. Utilization
bands use development-defined cutpoints with explicit overflow handling.
Neither demographic exclusion nor these descriptions establish fairness.

The inspected SHAP implementation uses a fixed 100-row development background,
996 development explanation rows plus up to four validation cases, and
interventional raw-default-log-odds explanations. It selects two dependence
features by development mean absolute SHAP with a feature-name tie break,
records IDs/features/settings/model identities, and guards raw-margin
additivity. This inspection does **not** establish actual SHAP compatibility,
additivity, feature rankings or plots: those measurements require successful
execution after dependency installation. Raw-tree SHAP does not automatically
explain a fitted probability mapping and is not causal inference.

## Findings, corrections and checks

1. **High, corrected — incomplete freeze acceptance**,
   `src/credit_risk/models/bundle.py`. Originally complete/PASS flags and an
   arbitrary supplied artifact map could pass without required hashed bundle,
   policy/report/reference/explanation artifacts. This could admit premature
   final-test exposure. The validator now requires these artifacts, binds the
   report hash, rejects unsafe paths/symlink escapes and requires independent
   review evidence tied to the exact inventory and document hash. It also
   requires explicit availability for all four case categories and local SHAP
   plot hashes for available cases.
2. **Low, corrected — logistic reference identity**,
   `src/credit_risk/phase4.py`. The missing-dependency descriptive branch
   initially omitted its reference SHA. The corrected execution records the
   exact accepted logistic identity.
3. **Delivery gap, corrected implementation — review/freeze transition**,
   `src/credit_risk/phase4.py`. A dedicated finalization path now requires
   completed SHAP, an exact-content independent PASS receipt and unchanged
   accepted inputs/completion source. Historical core source stays preserved
   separately from completion source. It verifies the existing incomplete
   manifest hash and run/mapping/input identity before sealing, so an edited
   manifest cannot be silently legitimized. A completed freeze cannot be
   overwritten by resume. Actual sealing remains blocked.
4. **Exit-gate blocker, unresolved — SHAP/plotting execution**,
   the real run’s `explanations/` and `freeze_manifest.json`. Missing packages
   prevent required global/dependence/local SHAP plots and measured explanation
   evidence. Complete installation/import/save-load smoke checks, resume the
   same run without fits, independently review the new evidence and seal only
   after a PASS receipt. Do not evaluate final-test outcomes in this state.

The review ran policy/explanation fixtures: **61 passed in 13.89s**; the
initial calibration fixtures: **7 passed in 12.23s**; after validator/finalizer
corrections, the expanded calibration/freeze suite: **11 passed in 12.17s**.
This independently exercises **72 distinct Phase 4 fixture tests**. Separate recorded
whole-repository Ruff passed; its final full fixture suite completed with
**182 passed, 1 skipped in 53.31s**. The SQL identity probe failed with
`OperationalError` before any database mutation, so the skipped SQL integration
test is not represented as passed. These recorded results are separately
attributed from the review’s targeted runs and from Phase 3’s earlier
SQL-enabled suite. The report and reproduction guide were also inspected for
consistent selection, synthetic-utility limitations, blocked status and
zero-refit resume/finalization commands. The real
incomplete manifest was hash-checked and its loading guard independently
rejected it with `Incomplete pre-test bundle`. It remains BLOCKED rather than
being represented as a completed freeze. No final-test performance result,
bootstrap interval, SHAP finding, SQL test success or fresh-container
reproduction is claimed by this review.
