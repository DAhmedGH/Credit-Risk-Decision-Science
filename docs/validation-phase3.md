# Phase 3 independent scientific and code review

This technical summary preserves recorded findings and checks. Original review
documents and hash-bound receipts are retained privately. These checks were
performed at the dated checkpoint, not repeated for presentation cleanup.

Status: **Phase 3 gate BLOCKED**. The implemented and executed logistic/forest
scope passes the checks below. Real XGBoost profiling, the complete bounded
comparison and development-only base selection remain unverified requirements.

## Scope and evidence

The review read the repository instructions, design and Phase 3 plan, accepted
Phase 2 checkpoint and reproduction guide, progress/decision/exposure logs, and
inspected the Phase 3 pipeline, search and orchestration implementations. Review
does not open calibration, policy-validation or final-test outcomes. Frozen
inputs and model artifacts are not mutated.

Independently executed fixture verification:

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_model_search.py tests/test_model_pipelines.py \
  tests/test_baseline_evaluation.py
```

Result: **29 passed, 1 skipped in 15.03s**. The skipped test requires the absent
XGBoost package and therefore does not establish real XGBoost compatibility.

After the runner and correction tests were available, independently executed:

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_phase3.py
```

Result: **5 passed, 1 skipped in 26.31s**. Executed checks include a real local
MLflow logistic fixture, complete-family/provenance guards, stale-profile
rejection, nonconverged final-refit rejection and mocked XGBoost wrapper
weight/clone/serialization plumbing. The mock does not validate the XGBoost
library. Its real complete-selection integration remains skipped.

After OOF capture was added to the search scorer, independently reran
`tests/test_model_search.py`: **8 passed, 1 skipped in 12.97s**. Scorer-side OOF
capture preserves predictions from the budgeted fits, with a single-worker
guard and reload-based reconciliation; it requires no additional fits.

## Real-data evidence

Read-only audit of logistic parent `0c41719e0c73482f875a4015477a03c6` under
`/tmp/credit-risk-phase3-real-03kpjn82` independently verified:

- All input, original maintained code, runtime and compact artifact hashes
  agreed at the numerical audit; the preserved original source snapshots and
  reviewed later orchestration differences are verified separately below.
- All 12 candidates have exactly 18,000 distinct development OOF IDs,
  covering 216,000 saved prediction rows; folds and fingerprints match the
  label-free frozen assignments, with 3,600 validation rows per fold and no
  cross-fold profile groups.
- AP, ROC-AUC, log loss and Brier were recomputed for all 60 folds, then fold
  means/sample SDs and pooled OOF metrics. Maximum absolute difference from
  saved fold metrics was **0.0**; logged candidate means also agree.
- All 13 parent/child MLflow records are FINISHED with correct parent links;
  there are no captured search warnings and `base_selected=false`.

Only saved development outcomes and label-free assignments were interpreted.
The workbook and full label export were byte-hashed without decoding. No
calibration, policy-validation or final-test outcomes were read by this audit.

The same independent read-only audit passed for forest parent
`e055463d1abd40f3bcdd6a2bd47f82a8`: all hashes match; another **216,000 OOF rows**
cover 12 candidates and the exact 18,000 development customers/frozen groups;
all **60 fold metrics**, means/sample SDs, pooled metrics and logged candidate
means agree, with maximum absolute fold-metric difference **0.0**. Its parent
and 12 children are FINISHED, warnings are empty and `base_selected=false`.

Combined evidence is **24 configurations, 120 real CV fits, 432,000 saved OOF
rows and 26 FINISHED MLflow records**. There were no automatic refits, XGBoost
fits, base-selection fits or final-development model artifacts. Both searches
completed; no interrupted or failed search is inferred. Valid completed
searches should be preserved and reused under explicit compatible provenance,
rather than rerun merely because the session was interrupted.

## Findings and corrections

| Severity | Affected path | Scientific consequence | Correction and disposition |
| --- | --- | --- | --- |
| Medium | `src/credit_risk/phase3.py`, all-development fit inside `select` | Checked OOF convergence does not establish convergence of the larger final development refit. The saved selected base could be nonconverged. | Resolved: `_fit_development` rejects `ConvergenceWarning` and max-iteration exhaustion before serialization; independent focused fixture passed. |
| Medium | `src/credit_risk/phase3.py`, `_verify_profile` | A changed preprocessing/model implementation or search declaration can reuse a profile that did not measure the current configuration's implementation. | Resolved: current code-tree and declaration hashes are required to match the profile; independent stale-provenance fixture passed. |
| Medium | `src/credit_risk/phase3.py`, additive-reuse AST guard | The initial guard omitted final-fit input/frame/target assignments outside the reference loop, permitting those statements to change while claiming compatible provenance. | Resolved: the guard compares original input, frame, predictor and outcome assignments as well as protected functions, candidate/reference decisions and numerical loop statements. Independent focused no-fit tests passed. |
| Medium | `src/credit_risk/phase3.py`, additive-reuse lock guard | Adding XGBoost while retaining the old Phase 2 lock hash would describe an installed environment with a stale dependency lock, especially after restoring materialized runtime snapshots. | Resolved: additive reuse requires an updated lock, current runtime lock bytes matching its fingerprint and every installed noneditable dependency pin; independent no-fit tests passed. Ordinary orchestration-only reuse remains allowed. |
| Low | `src/credit_risk/phase3.py`, profile runtime estimate | Scaling tree count does not guarantee an upper runtime bound for other tree depths and feature variants. | Resolved: renamed to a linear tree-count planning estimate, explicitly qualified in reproduction instructions. |
| Low | `reports/phase3_reuse_audit.json` | The initial receipt's current code-tree hash preceded the final guard correction, so it no longer described the reviewed current orchestration. | Resolved: regenerated after code freeze; both complete current-code proofs independently recompute exactly. Original search contexts and numerical evidence remain valid and unchanged. |

## Methodology inspection

The bounded plan counts all four matched feature/weighting variants within each
family: 12 logistic, 12 forest and 24 XGBoost configurations, respectively
60/60/120 five-fold fits. Matched settings make feature and weighting contrasts
interpretable. Explicit frozen indices preserve customer and financial-profile
groups, and learned preprocessing is constructed within each estimator fit.
The XGBoost wrapper computes the positive-class ratio from that fit's labels,
protects concurrency/weighting settings and omits early stopping.

The multimetric callable records AP, ROC-AUC, log loss, Brier and timing from a
single prediction call. AP ranks are retained; `refit=False` prevents an
unaccounted automatic fit. Positive losses in reported tables are distinct from
scikit-learn's negative loss scores. Sample fold SDs are distinct from pooled
OOF metrics. Selected/reference OOF refits reconcile saved predictions and
search fold metrics before development-only refits.

Selection implements the design's 0.01 absolute AP eligibility rule, then a
declared 0.001 log-loss simplicity tolerance, then explicit simplicity and
runtime tie rules. Neither tolerance is a significance test. Complete
three-family, matching-plan/input evidence with verified scientific source and
environment compatibility is required before selection. Partial searches
cannot establish a final base winner.

The accepted Phase 2 forest is a prior incumbent. Restricting the unchanged
declared search universe to its sampled Phase 3 configurations is not a leakage
or budget violation. Reports must compare with that incumbent honestly and
must not call a limited-universe choice the best across every previously
evaluated configuration. No real selection has happened.

## Compatible continuation without repeating completed searches

The original 36 source/config/lock files were snapshotted before orchestration
changes; the review byte-hashed every snapshot against both historical search
contexts. The only actual source differences inspected were the provenance-reuse
guard/receipt integration in `phase3.py` and explicit runtime-root support in the
CLI. Numerical model, feature, preprocessing, frozen-CV and search code stayed
unchanged. Current-environment reuse proofs for both completed searches passed
with exactly those two allowed changed files, no dependency changes and **zero
additional search fits**.

The reuse interface requires exact plan/config/input/Python/platform identities,
unchanged existing package versions, and unchanged numerical source hashes.
It permits only the pinned `xgboost-cpu==3.0.5` addition and explicitly reviewed
runner/CLI/lock differences. Original runner snapshots, protected function/input
assignment/selection/refit AST comparisons and internally consistent hashes
prevent a blanket code-tree or dependency-lock waiver. New receipts preserve
original search provenance separately from the current refit environment.
This is a compatibility proof, not a claim that XGBoost has been installed or
that old searches ran in the new environment.

Independently executed `tests/test_phase3_reuse.py`: **17 passed in 0.50s**
(earlier pre-lock-correction run: 16 passed in 0.47s),
with no fits. Tests exercise accepted additive reuse and rejection of changed
existing packages, unlisted/wrong-version additions, numerical source, missing
snapshots, plan/input/config/Python identities, selection/final-fit/input-frame
statements, inconsistent fingerprints and stale/incomplete dependency locks.
Original receipts remain unchanged.

All **24** saved controlled feature/weighting contrasts were independently
recomputed from the audited candidate fold means and agree within 1e-12.
The measured report accurately distinguishes family AP leaders from a selected
base, prior Phase 2 evidence from Phase 3, search-fit from tracking-inclusive
runtime, and fold means from pooled OOF scores. It reports the blocked gate
honestly. Continuation instructions reuse the completed searches, preserve
their separate FileStore and original source snapshots, and scope imported
source/lock provenance to the restored runtime.

After final code freeze, both regenerated orchestration-only reuse proofs were
independently recomputed and match exactly, including current code-tree hash
`9725240b75a6b3c8b6243a32bfaeafc5da0e18c350b2130806e0901ed3a47858`.
The resume receipt's linked evidence hashes and all **38** project/runtime
compact-file copies were independently byte-verified. The final recorded
verification receipt reports **108 passed, 3 skipped in 46.38s**, Ruff and shell
syntax passed. These full-suite executions are separate execution evidence; the
separately executed verification checks are identified above. The three skips
are the two real-XGBoost integrations and live PostgreSQL; none is described as
a completed execution.

## Final disposition

No unresolved scientific-integrity finding remains in the implemented and
executed logistic/forest scope or the reviewed continuation interface. The
completed searches remain valid and must not be duplicated merely to resume.
Actual additive-XGBoost compatibility is still unrun.

**Phase 3 gate remains BLOCKED.** Missing real XGBoost import/fit/save-load,
development profile/search, complete base selection, and development-only
base/reference refit/serialization evidence prevent acceptance. The selected
base is not frozen, and no complete calibrated/policy bundle exists. Finish
those Phase 3 requirements using the documented verified-reuse procedure, then
obtain review of the new evidence. Phase 4 and final-test evaluation have not
run and remain outside this milestone.
