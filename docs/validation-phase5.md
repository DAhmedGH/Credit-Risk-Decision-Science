# Independent Phase 5 saved-evidence review

This technical summary preserves recorded findings and checks. Original review
documents and hash-bound receipts are retained privately. These checks were
performed at the dated checkpoint, not repeated for presentation cleanup.

**Final independent numerical/scientific/code/documentation disposition: PASS.**
Evaluation run `faa4d59ec05c408aacd3bd6560678c76`; 4,500 frozen final-test rows.
This is an independent saved-evidence review, not a claim that the complete Phase 5 delivery gate has passed.

## Scope and actual access

Verification scope is recorded in `docs/test-exposure-log.md` at 2026-10-09T21:31:47.068723+00:00. The review decoded saved `predictions.csv` and `decisions.csv` at 2026-10-09T21:32:56.084151+00:00, and reread saved predictions at 2026-10-09T21:34:29.375573+00:00 for independent reliability-bin/CSV checks. Aggregate results and figures were read after they became available. Source label CSV and workbook were never opened. No fit, search, calibration, reselection, threshold adjustment, source/test edit, or training-database access occurred.

## Independent computations

All six raw-reference/selected-bundle metric rows match: AP, ROC-AUC, log loss and Brier. The selected raw XGBoost has AP 0.5642176410184566, ROC-AUC 0.7939820067943004, log loss 0.42331365771732493 and Brier 0.13319703405584427. The forest's AP 0.5663601841455993 is reported without changing the development-selected champion.

All 88 frozen policy/scenario rows independently reconcile, including counts, accepted default rate, benchmark and predicted expected utilities, and abstention-positive detection TP/FP/FN/TN, precision, recall, F1 and FPR. All 396,000 saved decision records match the frozen strict-cutoff masks and exact final-test ID/fingerprint assignment.

Base empirical cutoff 0.085 accepts 1,028 records, including 55 defaults, for 21,150 synthetic utility units (4.7/customer). Confusion counts are TN 973, FP 2,531, FN 55 and TP 941. The analytic cutoff accepts 1,160, including 64 defaults, for 5.066666666666666 units/customer. Neither policy is reselected.

A separate implementation (no project evaluation imports) rebuilt sorted fingerprint groups using a dictionary, sampled groups with replacement using NumPy seed 42, retained all rows and repetitions of each drawn group, and reused each draw across every model/policy comparison. All 1,000 repetitions over 4,378 groups reproduce the plan SHA:
`18ecf64cac061d62831872327e7bd08d5d2e3e4902acac4086529b879e61b447`.
All 341 interval statistics, estimates, percentile endpoints and valid/undefined counts match exactly; maximum absolute numeric discrepancy is 0.0. This includes 24 probability intervals, 264 policy intervals, 20 model-difference intervals and 33 empirical-minus-analytic/all/none utility contrasts.

The base empirical utility 95% interval is [2.9012050079916825, 6.371055963172558]. Empirical-minus-analytic is -0.36666666666666625 with interval [-0.9862242784145837, 0.4164518935709502]. No superiority claim is justified by that contrast. Intervals condition on fixed fitted models/policies; they exclude model-development and temporal uncertainty.

Twelve accepted-default-rate statistics are undefined in every replicate: 11 explicit abstain-all cells and G25/L750 empirical abstain-all. Each has null estimate/endpoints, zero valid and 1,000 undefined repetitions. No undefined rate is coerced to zero. All other required interval statistics have 1,000 valid repetitions.

All CSV model/policy/interval tables agree with JSON. All 60 reliability bins independently reconcile, including fixed boundaries, inclusion of probability one, counts, sparsity and empty-bin N/A; maximum mean/rate discrepancy 1.11e-16. All five original final PNGs were visually inspected: ranking, reliability, confusion, utility and sensitivity; numerical definitions and annotations agree.

All 106 frozen artifacts, 48 source/test hashes, archived source/test files, archived lock, completion/exposure/readiness bindings and saved-evidence hashes verify. The full reviewed source/test-map SHA is `816b8cce9ecd1327f94d971d0922b45d22671b1a9a4a1c085360c491f56f0130`.

## Supplemental delivery evidence

Separate validation recomputed 198 monitoring distributions/counts/PSI values and CSV agreement; maximum PSI discrepancy 2.22e-16. Corrupted financial histories have no labeled-performance evidence; count reconciliation passes. This check did not reroute source financial rows or reproduce recorded sampling from them.

Separate validation loaded the trusted frozen bundle and rescored the 12-record unlabeled example in memory. Saved outputs agree within 1e-12, every single-row/batch probability agrees exactly, and counts reconcile. Zero fits or database access.

Recorded execution evidence, inspected separately during validation: full SQL-enabled suite 207 passed in 87.89s with zero skips, focused suite 24 passed in 32.60s, and repository Ruff PASS. Recorded fresh-container fixtures passed 206 tests with one expected SQL skip in 54.31s with networking disabled. The fresh core reproduction receipt records PASS in 114.77779685499263s, zero fits, identical saved metrics/341 intervals/plan and rebuilt split hash. Separate validation checked the compact/runtime receipt equality, split byte hash, source/test-map equality, and recorded tolerances, but did not reopen the workbook or rerun that recorded execution. Feature max absolute discrepancy 1.1641532182693481e-10 meets combined atol=1e-10 and rtol=1e-12, not a claim of exact feature equality.

## Final prose and delivery review

Read README, reports/results.md, model card, walkthrough, leakage audit, monitoring report, reproduction guide, project checklist and Phase 5 report. Ranking/selection, AP naming, historical existing-account population, prediction-time assumption, supplied-source provenance, synthetic noncausal utility, calibration partition separation, unchanged champion/policies, conditional group uncertainty, SHAP output/background, support thresholds and fairness/temporal limitations are correctly scoped. All inspected relative documentation links resolve now that the final guide exists. The guide accurately distinguishes fresh frozen-core reproduction from optional expensive training reproduction and does not claim remote CI success.

Reviewed pack/restore/log/reproduce scripts: immutable accepted models, new output directories, pinned input/split identity, no fits/reselection, and aggregate-only logging are maintained. Restoration validates digest/safe entries and refuses an existing destination. The archive has 174 payload files, SHA `0a4f075b34257eb651f10cf1edcdaf5852aeb3fb76629af0a6c90b3f090a49c2`, 9,819,660 bytes. Separate validation verified archive bytes/size/inventory safety without extraction, then 172 permitted restored file hashes and byte-exact restored scoring outputs; source labels/workbook were deliberately excluded from validation access. The restoration receipt now supports the guide's restoration-success statement.

The supplemental aggregate-only policy plot was inspected along with its script: all eight base policies are retained; the zoom separates low-acceptance labels; original figure and statistical evidence remain unchanged. The synthetic timing receipt is properly limited to validation/feature/scoring, excluding loading/I/O, with no population/production performance claim. No delivery script was executed by this review.

The resumed original MLflow run `61449a81592f446281de1f939fc8badd` is FINISHED. Separate validation compared all 541 saved aggregate metric values against local metric files and verified the evaluation identity and unchanged aggregate-results hash. Reviewed batched recovery logging performs no evaluation or fitting. The current Phase 5 report accurately distinguishes restoration success from the interrupted outer tool and records same-run logging recovery. Local delivery commit `1a0af13972ce4dc6e22856abfdc895d5da07f388` is verified on `main` with 316 tracked files. Final status/prose changes were reviewed, including the checklist, current progress with preserved Phase 4 history, D025 and exposure-completion record. Spacing and numeric grouping preserve scientific values, model names and paths. Six polished documents remain modified relative to that commit at this check; their current bytes are bound in the review receipt. The subsequent acceptance/prose commit remains recorded separately. Historical training null commits remain honest; source/test identities are content-bound.

## Findings and disposition

- **P5-L01, LOW, reports/phase5/policy_utility.png — resolved:** original overlapping labels obscured visual comparison only. Supplement reports/phase5/policy_utility_detail.png fixes readability using saved aggregates and preserves original evidence.
- **P5-M02, MEDIUM, reports/results.md:64 — resolved:** malformed `F 10.42122` could imply an impossible detection score. Corrected to `F1 0.42122`; saved numeric evidence unchanged.
- **P5-M03, MEDIUM, docs/leakage_audit.md:48,74–75 — resolved:** earlier pending/future wording is explicitly historical; current learned-transform/sentinel verification and accepted evidence links are stated. Reporting now agrees with verified leakage protections.
- **P5-L04, LOW, docs/setup.md, Saved-evidence reporting — resolved:** current prose correctly places freeze/source/review/evidence-hash checks before outcome decoding and exact model/ID/fingerprint/decision validation before reporting.
- **P5-M05, MEDIUM, reproduction guide restoration success — resolved:** initially premature while execution was pending; actual restoration receipt and independent permitted-file/scoring checks now support it.

**All findings resolved.**
