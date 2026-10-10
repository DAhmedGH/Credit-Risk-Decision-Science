# Independent acceptance review of completed Phase 4 artifacts

This technical summary preserves recorded findings and checks. Original review
documents and hash-bound receipts are retained privately. These checks were
performed at the dated checkpoint, not repeated for presentation cleanup.

**Current Phase 4 status: PASS, complete pre-test freeze succeeded.**
complete_bundle_frozen=true; independent_review_status=PASS; status FROZEN.
Freeze content SHA:
`89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b`.
All 106 final artifact hashes and guarded loading pass. Final-test outcomes
remain unevaluated; Phase 5 remains unstarted.

The review text below records the independent review's **pre-seal inspection
time**, when the 104-artifact inventory was ready for finalization and the
incomplete loading guard correctly refused access. Those pending statements
describe historical review-time state. The finalization section
at the end records the successful seal. The unchanged attested document is
[validation-phase4-complete.md](validation-phase4-complete.md); this current index and
post-seal verification summary are not the receipt-attested document.

Reviewed October 9, 2026. **Disposition: PASS for the complete scientific and
artifact review.** Run `9ca62eca2665438c9c97b4889413acfa` is ready for the
guarded pre-test finalization step. This review does not itself seal the bundle
or authorize final-test evaluation. The historical dependency-blocked review
is preserved in `docs/validation-phase4-blocked.md`. The exact attested independent
review remains unchanged in `docs/validation-phase4-complete.md`.

No unresolved scientific-integrity, explanation-delivery or dependency
compatibility finding remains. The review performed **zero fits, searches,
calibration refits, policy changes or test-suite reruns**. It changed no model,
source, split or runtime artifact. The correction changed only an operational
checkpoint directory alias, described below.

## Exact reviewed identity and environment

The completed checkpoint contains **104 regular hash-verified artifacts**.
Its canonical artifact-inventory SHA-256 is
`4de2c397ec4ad8659b6da9a4dd7cda9d58a9c57474ecd3c743dc0a5411ea4e2a`.
The pre-finalization manifest content identity is
`000fae1a7130b5322edb144b48a783efdb1c56517b4e53d5fcaf4ddf332adb6e`;
it correctly records explanations complete, no blockers and independent review
pending. Complete-bundle loading must continue to reject it until sealing.

The accepted Phase 3 selection remains
`6a0725d18b164582938e0b07b2df6b27`, selected
`xgboost_05_engineered_none`. Its original binary SHA remains
`265db2cbe02e88ca7c75c29f39b5c0230a29ba40e4735ea808aea08df4a5e83c`.
The probability bundle SHA remains
`45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd`.
All five original pipeline/metadata identities match the accepted durable
Phase 3 backup. The bundle includes their corresponding fitted references;
feature selectors/preprocessors and meaningful fitted estimator state agree.
For the forest, all 200 trees’ node fields, values, parameters and fitted
attributes agree fieldwise; irrelevant structured-array padding is not used
as scientific identity evidence.

The accepted Phase 3 lock is preserved byte-for-byte as
`requirements-phase3.lock`, SHA
`31e7241f3499567f92579f1381892351dcd433faf219fe8b0be70321937e6b57`.
All **59 distribution-version pins** are unchanged in the current **71-pin**
lock. All accepted manifest dependency versions and all current locked
distribution versions agree with the installed environment. The additions
include the intended `shap==0.48.0` and `matplotlib==3.10.6` and their compatible
dependencies; they do not replace accepted numerical packages.

Current lock SHA:
`af2037d68e8508c120ff7e70fa2c4d43720f309839230b88db106703479668d8`.
Current completion code SHA:
`fe44551d459c780b1ee2cce011aecb35ff1c54601ed2fb198f5be620098f2885`.
Every original core-source and completion-source snapshot hash was checked,
and current maintained source matches the completion context. The historical
core execution context and original fitted identities remain preserved rather
than being retroactively rewritten.

## Partition protection and access

Source/export/feature-contract/split hashes match accepted evidence before
value interpretation. Frozen sizes remain 18,000 development, 4,500 calibration,
3,000 policy validation and 4,500 final test. Assignment inspection verifies
partition/fold integrity and fingerprint-group separation without outcomes.
Development/calibration/policy ID hashes agree with assignments. IDs, target
and audit-only demographics cannot enter the financial predictor contract.

The review interpreted only saved policy-validation outcomes in
`policy_predictions.npz`. For explanation verification it additionally routed
**1,089 development financial rows**, the union of the fixed 100-row background
and 996-row explanation sample, by frozen IDs before conversion. That access
intention was recorded before conversion in the partition/access logs. The
review did not decode the workbook or label CSV, inspect calibration outcomes,
convert final-test financial values, or inspect final-test outcomes.

The accepted base is still unweighted, combined-feature XGBoost with 100 trees,
development-only fitting and positive class 1. Loaded selected/base/calibrator
state agrees with recorded unchanged base hash
`bfdafb97487d3ae9cbbb836faed9e2ad`. Both mappings retain one frozen accepted
estimator using sklearn 1.7.2 `FrozenEstimator`, `ensemble=False`; saved evidence
records two calibration fits and zero base/reference fits. This review adds
none. Exact original model bytes remain independently loadable without the
historical `/tmp` runtime.

## Independent probability and policy calculations

Fresh calculations from the saved policy predictions reproduce every reported
probability metric with maximum absolute difference **0.0**:

| Variant | AP | ROC-AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: |
| Raw | 0.5485792516 | 0.7762329283 | 0.4329887140 | 0.1361703025 |
| Sigmoid | 0.5485792516 | 0.7762329283 | 0.4362283190 | 0.1370796970 |
| Isotonic | 0.5287544252 | 0.7754766927 | 0.4559940960 | 0.1367095427 |

The independent simplicity/tolerance calculation selects raw. It minimizes
log loss and precedes sigmoid within 0.005; isotonic is outside the tolerance.
No mapping, model or cutoff is reselected from test evidence.

All **88 policy rows** (eight base plus 80 sensitivity) reproduce with maximum
absolute difference **0.0** across counts, rates, benchmark utilities, predicted
expected utilities and defined detection metrics. Independent fixed-grid
optimization reproduces every empirical acceptance mask, including lower-count
utility ties and explicit accept-all/none. All fraction boundaries match their
frozen validation order statistics; numerical cutoffs will not be recomputed
from final-test percentiles.

Base analytic cutoff is 50/550: 760 accepted, 47 benchmark defaults, utility
12,150. Empirical cutoff 0.085: 681 accepted, 36 benchmark defaults, utility
14,250. These are selection-sample synthetic utilities, not observed profit or
causal intervention effects. All nine G/L cells and the C=5 secondary scenario
remain published. G=25/L=750 correctly has an empirical abstain-all winner with
zero utility and N/A accepted default rate; its analytic policy accepts 14 and
has utility -1,200. Processing cost is charged once per accepted account.

All 30 reliability bins independently reproduce. The original SVG’s XML,
27 nonempty-bin point coordinates, sparse-point styling and all 30 count
annotations were audited. A native librsvg/Cairo preview of that original SVG
was visually inspected without adding dependencies or modifying artifacts.
The figure has readable axes/variant colors/counts, hollow sparse-bin points,
asterisks and no points for empty bins. It distinguishes overall probability
quality from calibration diagnostics.

## Actual SHAP and descriptive explanations

All **seven actual SHAP PNGs** were visually inspected: one global summary,
two development dependence plots and four local waterfalls. Titles correctly
identify the accepted XGBoost and raw default log odds; local IDs match the
frozen diagnostic cases. Rounded waterfall labels are presentation values;
exact contributions are retained in the NPZ artifact.

The explanation matrix has **1,000 rows × 89 encoded financial features**:
996 development rows plus the four selected policy-validation cases.
Independent seed-42 sampling reproduces every background/development ID and
their order. All 100 background IDs are development-only; no calibration or
final-test ID enters explanation/background samples. Reapplying accepted
preprocessing to the routed 996 development records reproduces all stored
transformed values exactly. Encoded names match accepted preprocessing, with
no target, ID or demographic feature.

All 1,000 saved raw margins reproduce exactly from the accepted estimator.
SHAP uses `TreeExplainer`, interventional perturbation, raw output and the
fixed transformed development background. The recorded expected raw log odds
is **-1.660279731919057**. Independently reconstructing contribution sums gives
maximum absolute raw-margin residual **1.431484473179978e-06**, matching the
stored measurement and satisfying the stated additivity bound.

A separate TreeExplainer constructed from the accepted estimator and verified
background recomputed **14 rows** (10 fixed development checks plus all four
local examples). Every recomputed contribution and expected value matches the
saved result exactly; maximum contribution difference is **0.0**. This small
verification adds no fitting or full explanation rerun. Sigmoid of raw margins
matches model probabilities within 6.901343829746054e-08, ordinary numeric
rounding; all four case probabilities match saved raw policy predictions
exactly. Six single/batch predictions on saved transformed records also match
exactly. Earlier end-to-end save/load evidence remains unchanged.

Independent development-only mean absolute SHAP calculations reproduce all
89 importance values and select the same two dependence features:

| Feature | Mean absolute SHAP, log-odds units |
| --- | ---: |
| Recent delinquency count | 0.3907695779 |
| September repayment status 2 indicator | 0.1356965149 |
| Latest utilization proxy | 0.1180831040 |
| September bill amount | 0.0897371165 |
| Mean payment | 0.0895208424 |

Dependence-feature selection uses only development evidence. Higher displayed
delay counts and presence of the September-status-2 indicator associate with
positive raw-model contributions in these sampled plots; this is model behavior,
not a causal effect. Correlated histories can share attribution. Raw-tree SHAP
does not automatically explain other probability mappings or other models.

The accepted logistic reference’s 26 standardized numeric coefficients,
training means/SDs and 63 categorical coefficients/contrasts independently
agree with the saved fitted model. Reference levels are explicit lowest learned
categories, and contrasts are coefficient differences rather than individual
full-one-hot coefficients misrepresented as reference contrasts.

Independent 0.5 classification rules reproduce the four selected cases:
correct default 19983, correct nondefault 27074, missed default 2561 and false
alarm 28302. Selection uses highest/lowest confidence as specified, with
smallest-ID ties; none is invented. Behavioral counts and weighted probability,
Brier/log-loss and detection summaries reconcile globally. Each demographic
attribute totals 3,000 rows; all unstable probability/rate summaries are
suppressed below n=100 or 20 of either class. Development-defined utilization
bands, demographic audit rules and their unchanged reviewed implementation
remain separate from allocation thresholds. No demographic-specific policy,
fairness conclusion or causal claim is introduced.

## Freeze gates, execution attribution and disposition

The finalizer and loader were inspected for required schema, policy, model,
reference, reporting, SHAP and available-local-case artifacts; content identity,
safe paths and review-document/inventory binding; unchanged accepted inputs and
completion source; and refusal to resume a completed freeze. A finalization
receipt must bind this exact 104-artifact inventory and this review document.
Report definitions already freeze all models/policies/scenarios, fixed bins,
1,000 seed-42 paired fingerprint-group bootstrap replicates, conditioning and
undefined-statistic treatment. No final-test evaluation or interval ran.

The recorded operational correction changes only
`checkpoint.compact_dir` from the uppercase project path to its lowercase
writable workspace alias. Independent `samefile` checks confirm the workspace,
runtime, compact directory and bundle aliases identify the same objects.
The original checkpoint is retained in
`reports/history/phase4_pre_acceptance/checkpoint_before_runtime_path_alias.json`.
The correction changes neither the 104 hashes nor inventory identity, source,
model, mapping, policy, sample or reporting definition. It is not a new
scientific experiment or a workaround for review/manifest requirements.

The **reported WSL** bootstrap passed the synthetic calibration/TreeSHAP/plot/
save-load smoke and 182 tests with one SQL skip. The user then started the
project database and reports the enabled suite **183 passed in 54.31s, no
skips**, plus Ruff PASS. These commands were not re-executed by this acceptance
review; attribution and unavailable exact invocation timestamps are retained
in `reports/phase4_user_verification.json`. Review independently checked the
actual packages, completed real artifacts and numerical evidence rather than
claiming reported WSL tests as its own execution.

The historical high-severity incomplete-freeze omission and missing logistic
identity were corrected before this review. No new scientific/code correction
is required. There is no remaining dependency/SHAP blocker. **PASS receipt may
be issued for guarded sealing.** Successful sealing requires verification
and loading and update the report/progress/checkpoint. Final-test access, Phase 5
evaluation/batch/monitoring, remote CI and fresh-container reproduction remain
outside this acceptance task and are not claimed.


## Finalization verification (after technical review)

The guarded finalize CLI completed successfully. Final status FROZEN;
complete_bundle_frozen=true; independent_review_status=PASS. Freeze content SHA
`89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b`; bundle SHA
`45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd`. All 106 final hashed artifacts,
including review receipt/document, reconcile; guarded loading passes without
final-test outcomes. The independent review document named in the receipt remains
unchanged. Earlier blocked evidence is preserved in
[validation-phase4-blocked.md](validation-phase4-blocked.md). No Phase 5 work occurred.

Independent post-seal and post-incident verification confirms the complete guard,
five original reference loads, joined metadata contract, review bindings and
unchanged source/lock/artifact identities. D022 discloses corrected scratch
assertions and an interrupted documentation-shell bootstrap attempt that failed
at integrity writing before installs, fits, smoke or tests. No scientific finding
or frozen-artifact change resulted. This summary is outside the attested review;
receipt and runtime review document remain unchanged.

Final read-only documentation review also passes. The separate validation
executed the exact documented loading command successfully and confirmed
current report/progress/checkpoint/acceptance evidence, each-class support rules,
historical status labels, 104-versus-106 counts, separate content/file hashes
and source-versus-canonical receipt hashes. No unresolved issues remain.
