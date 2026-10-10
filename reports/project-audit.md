# Completed-project audit

**Verdict:** the inspected scope passes after the corrections below. Original acceptance remains supported for the frozen scientific results. No finding requires scientific re-execution or changes a model, mapping, scenario, cutoff or reported result. This bounded audit does not prove that no bugs exist.

Audit date: October 9, 2026 America/Toronto (execution crossed into October 10 UTC). Starting state: clean `main` at `fb022d9dca79d6aee1a565a62c36df33ece743e2`, 317 tracked files, no remote configured. Initial audit closeout left changes local and uncommitted; subsequent delivery records separately reported WSL container evidence. Findings: **one high, three medium, four low; all resolved**. `reports/project-audit-findings.json` (private historical evidence).

## Scope and concrete plan followed

1. Read design/phase plan, phase reports, logs, reproduction guides, model card, README, acceptance/review evidence; inspect Git, files, dependencies, commands, tests, Docker/Compose and CI.
2. Establish authoritative artifact locations and verify the accepted freeze before code changes.
3. Directly inspect execution paths and scientific contracts; independently recompute predeclared saved-evidence quantities. Acceptance reports are supporting history, not substitutes for inspection.
4. Reproduce plausible public-command/artifact failures with synthetic fixtures; fix actual defects and add focused regressions. Preserve accepted evidence.
5. Run lint, full live-SQL tests, read-only full-source/database parity, restoration and database-independent scoring; independently review fixes and documentation.
6. Record findings, measurements, limitations and local Git checkpoint.

Separate scientific and implementation checks inspected code, substantive fixes, extra probes and separately executed tests. The [scientific checks](project-audit-evidence/scientific-review.md) and [implementation checks](project-audit-evidence/implementation-review.md) retain technical findings and their actual verification results. Historical receipts were preserved.

Direct code review covered workbook/header/type/target/category validation; signed balances/missingness/rejections; raw preservation; database identity/transactions/idempotence/exact persisted values; Python/SQL formulas; source fingerprints, partition/fold allocation and routed joins; predictor exclusions and learned preprocessing/weights; bounded search/OOF/selection; class-1 probabilities/serialization; fixed-base calibration; policy math/scalar thresholds/ties; SHAP/slices; freeze/review binding; final evaluation guards/snapshots; paired group bootstrap/degeneracy; saved-report validation; inference/monitoring; CLI/configuration; artifact writes/loading; local MLflow recovery; pack/restore/setup scripts; Docker context and CI. Tests were inspected for independent sentinels, row alignment and scientific boundaries. Twenty-four new regression cases supplement the unchanged original tests/tolerances.

## Authoritative artifacts and measured verification

Accepted Phase 4 directory: `artifacts/models/phase4/9ca62eca2665438c9c97b4889413acfa/`. Content seal: `89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b`. Bundle SHA: `45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd`. All **106** artifacts, manifest content/file hash and independent review binding verified before fixes; payload hashes verified again afterward. Accepted final evidence: `artifacts/runtime/phase5/final_evaluation/`, run `faa4d59ec05c408aacd3bd6560678c76`; compact results: `reports/phase5/`. Historical acceptance-bound receipt/document bytes match the starting commit.

Read-only live SQL verification decoded the original workbook for structural validity and exact persisted-value reconciliation only. All 30,000 source, curated, audit and exported rows reconcile; zero rejected. Original source/financial/target/audit values agree exactly with stored rows. All SQL features match Python formulas and the accepted exported CSV within the declared parity tolerance. Database identity was checked before queries; a read-only transaction enforced no writes. [Database evidence](project-audit-evidence/database.json).

Independent scientific checks established:

- All 30,000 profiles match frozen fingerprints; 29,183 groups; exact IDs and partition/fold isolation. Sizes remain 18,000/4,500/3,000/4,500.
- All 101 Phase 2 artifact hashes verified. Nine baseline variants' 162,000 development OOF rows have exact frozen coverage/alignment; 180 fold, 36 pooled and 72 mean/SD metric cells independently recompute within 8.33e-17. [Baseline OOF evidence](project-audit-evidence/phase2-oof-verification.json).
- All 2,682 Phase 3 preserved payload hashes/sizes match the inventory (131,298,257 bytes). All 48 candidates' 864,000 saved development OOF rows match frozen IDs/fingerprints/folds and common labels. Independently recomputed 960 fold metric cells, 192 pooled metric cells and 384 mean/SD cells agree within 8.33e-17. [OOF evidence](project-audit-evidence/development-oof-verification.json).
- Budgets remain 12/12/24 configurations and 60/60/120 search fits. Reconstructed selection gives 17 AP-eligible candidates; XGBoost 04/05 meet the predeclared 0.001 small-loss tolerance and simplicity retains 05. The 0.01 AP/0.001 loss tolerances are practical choices, not significance tests. Fit-local preprocessing/weights and controlled threads were inspected; fold means and pooled metrics remain distinct.
- Calibration ID hashes and shared FrozenEstimator base aliases agree with fixed-base evidence. All three mapping predictions reproduce saved policy-validation vectors exactly without fitting; raw wins the unchanged 0.005 log-loss rule.
- SHAP's 100-background/996-development/four-validation identities reproduce. All 89 transformed columns/values and margins agree with the saved model; importance recomputes. Maximum margin-additivity residual is 1.431484473179978e-06. Output is raw default log odds. Slice definitions, suppression and descriptive/noncausal limits were inspected.
- All 24 final model metric values reproduce exactly from saved predictions. Selected AP **0.5642176410184566**, ROC-AUC **0.7939820067943004**, log loss **0.42331365771732493**, Brier **0.13319703405584427** support the rounded claims.
- All 341 predeclared interval statistics were independently reconstructed with 1,000 seed-42 paired profile-group draws. Endpoints differ by at most 5.55e-17; valid/undefined counts and exact plan hash agree. All 88 policy/scenario rows and 396,000 saved decision IDs/masks independently reconcile, including counts, benchmark utility and accepted default rates. Policy choices remain fixed. [Bootstrap evidence](project-audit-evidence/bootstrap-verification.json), [decision evidence](project-audit-evidence/policy-decisions.json).
- All 198 monitoring distribution/count/PSI records reconcile within 2.22e-16; corruption metrics have no labels. All 541 aggregate metric values agree with the FINISHED local MLflow run `61449a81592f446281de1f939fc8badd`. [Tracking/monitoring evidence](project-audit-evidence/tracking-monitoring.json).

Visual inspection of the saved precision-recall, reliability, confusion, detailed policy-utility, sensitivity and global SHAP figures found their annotations and scientific framing consistent with the saved results. Numerical figure-generation paths were inspected; no figures were regenerated.

The empirical base cutoff remains 0.085: 1,028 acceptances, 55 defaults, 21,150 synthetic units, 4.70/customer. Analytic utility 5.0667/customer and the forest's slightly higher test AP remain contextual results. No test-driven selection, new exploratory final-test comparisons, real-data fits/searches/calibration fits or accepted final evaluation were executed. Accesses are recorded in the [exposure log](../docs/test-exposure-log.md). Fixture tests fit synthetic models; those fits provide no portfolio measurements.

## Resolved findings

| ID | Severity | Defect and correction | Accepted-result impact |
| --- | --- | --- | --- |
| A001 | High | CSV extra fields shifted IDs/features via pandas implicit indexing; short records silently added missingness; NUL bytes truncated fields/IDs. Strict widths/quoting/NUL parsing and cross-format NUL-ID rejection now fail before scoring. Eleven new regressions. | Well-formed accepted inputs/results unaffected; malformed public batches could previously score wrong identities/predictors. |
| A002 | Medium | Phase 4 routing fingerprinted NaN instead of canonical missing None and int-converted blank audits. Preserve null semantics before fingerprints/pipeline conversion; unknown audits remain supported. Four regressions. | Complete accepted workbook unaffected; valid incomplete inputs previously crashed. |
| A003 | Medium | Monitoring reused nonempty aggregate/runtime directories and could replace evidence. Reject nonempty output or existing receipts before scoring; exclusive runtime creation. Three preservation regressions. | Original outputs unchanged; prior repeated/interrupted path reuse risked lost provenance. |
| A004 | Medium | Optimized Python disabled reproduction assertions while permitting success output. Reject -O/PYTHONOPTIMIZE before imports/writes. Subprocess regression. | Original nonoptimized reproduction unaffected. |
| A005 | Low | Missing score/monitor paths caused late TypeError after loading. Required flags now produce actionable argparse exit 2 before artifact access. Three regressions. | None. |
| A006 | Low | Relative evaluation readiness ignored --root. Resolve under explicit project root; preserve absolute override. Two no-evaluation regressions. | Accepted root-local invocation unaffected; other-root calls could fail/read an unintended receipt. |
| A007 | Low | Exposure-log opening denied completed evaluation; old guides lacked current context for phase-specific Git/lock status. Correct opening/add historical pointers. | Original entries/receipts preserved. |
| A008 | Low | Restoration used live HEAD despite exact source guards, and created no .venv before environment-dependent commands. Pin the accepted-source replay/provide no-fit pinned setup and container route. | No resealing/regeneration; fixed source and historical replay are explicit. |

Structured findings include files, reproductions, fixes, regression evidence and individual statuses. No unresolved material finding remains in the audited scope. Source-bound historical preflight/report deliberately refuse changed maintained core/tests; protection was retained.

## Exact checks executed

| Check | Result |
| --- | --- |
| Full maintained pytest suite, SQL enabled | **231 passed, zero skips, 82.04s** |
| REPORTED WSL audit container build and network-disabled tests | Build succeeded; **230 passed, one expected live-PostgreSQL skip, 48.75s**; image SHA-256 `b3c645d144c7d0943efc4aa95ddc9e6b714979ff32322bf6b24c2acbd23340f9` |
| Live PostgreSQL fixture file separately | **4 passed, 2.06s**; identity/rollback checks |
| Repository Ruff, bootstrap shell syntax, Git whitespace | Passed |
| Dependencies | All 72 pins exact; uv pip check: 73 packages compatible |
| Workbook/persisted source/audits/SQL/Python/saved export | Passed, 30,000 rows, zero exclusions, read-only |
| Original freeze/archive/existing restored payload | 106 freeze artifacts; 174 archive and restored hashes exact |
| Newly executed documented restore plus the private accepted-source archive | 174 new restored hashes and 48 historical source/test files exact; original preflight executed successfully |
| Maintained-source historical preflight | Correctly rejected changed phase4_inputs.py before outcome decoding |
| CLI unlabeled scoring with deliberately unusable DB settings | 12 scored/0 quarantined; chosen-action EU correct; output CSV byte-identical to accepted example |
| Underlying OOF/selection/calibration/fingerprints/SHAP/saved metrics/bootstrap | Independent checks above passed |
| Delivery inventory/document links | Relative links resolve; no raw data/models/credentials/environments/tracking stores tracked |
| Independent fix verification | Parser/Phase 5: 25 passed; monitoring: 13 passed; commands: 6 passed; direct code/test inspection |

Full suite: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CREDIT_RISK_SQL_TEST=1 .venv/bin/python -m pytest -q -p no:cacheprovider`.
Lint: `.venv/bin/ruff check . --no-cache`.
SQL file: `CREDIT_RISK_SQL_TEST=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_database.py`.
Dependencies: `.tools/bin/uv pip check --python .venv/bin/python --cache-dir /tmp/credit-risk-audit-uv-cache`.
Read-only parity: `PYTHONPATH=src .venv/bin/python reports/project-audit-evidence/verify-database.py` (executed with the original script; logs structural access). For a repetition, supply `--output artifacts/runtime/project-audit/database-recheck.json` with a new path; the retained script refuses existing receipts before source access.
Scoring: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 POSTGRES_DB=unavailable_for_audit POSTGRES_PASSWORD=REPLACE_FOR_AUDIT POSTGRES_HOST_PORT=1 .venv/bin/python -m credit_risk.phase5 score --input examples/scoring_batch.csv --output artifacts/runtime/project-audit/score --scenario base --policy empirical` (choose a new output for repetition).
Restore: `python3 scripts/restore_phase5.py artifacts/runtime/phase5/credit-risk-phase5-artifacts.tar.gz --sha256 0a4f075b34257eb651f10cf1edcdaf5852aeb3fb76629af0a6c90b3f090a49c2 --destination artifacts/runtime/project-audit/restored`, then `tar -xf /path/to/credit-risk-accepted-source.tar -C artifacts/runtime/project-audit/restored`.
Historical preflight: `PYTHONPATH=artifacts/runtime/project-audit/restored/src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m credit_risk.phase5 preflight --root artifacts/runtime/project-audit/restored`.

Independent scripts and compact evidence are retained under `reports/project-audit-evidence/`; record repeated workbook/saved-outcome accesses before replay. The initial database connection probe failed without writes; later read-only checks succeeded. An initial pip-check attempt found no pip in the uv-managed .venv; the uv check succeeded. The initial preflight CLI refreshed its operational report; that audit result was saved separately as `initial-preflight.json` and the historical preflight was restored byte-exact from the starting commit. No accepted prediction/binary/freeze/review/acceptance receipt was overwritten.

**REPORTED WSL container verification:** the recorded WSL execution supplied these ordinary-WSL commands and results after audit closeout. The build succeeded with image SHA-256 `b3c645d144c7d0943efc4aa95ddc9e6b714979ff32322bf6b24c2acbd23340f9`; the container completed with 230 passed, one expected live-PostgreSQL integration skip in 48.75s. This is reported execution evidence, not an new execution. No raw terminal log was supplied. The local SQL-enabled audit suite remains 231 passed with zero skips.

```bash
docker build -t credit-risk-phase5:audit .
docker run --rm --network none \
  -e OPENBLAS_NUM_THREADS=1 \
  -e OMP_NUM_THREADS=1 \
  credit-risk-phase5:audit
```

## Reproducibility, delivery and limitations

The original 206-pass/one-SQL-skip network-disabled container and 114.778s fresh-core receipts, source/input/result identities, restored outputs and tolerances were inspected and reused. They were **not rerun or relabeled** as audit container executions. Current fixes passed the local SQL-enabled suite and the subsequently completed **REPORTED WSL rebuilt audit container** above. Earlier independent review notes describe the state before that reported WSL verification. The original scientific fresh-core reproduction was not repeated; no remote GitHub Actions run was observed. Fresh-environment installation instructions were inspected; another dependency install was unnecessary after exact pin/compatibility checks.

The ignored trusted scientific archive must accompany the accepted source checkout: a Git clone alone cannot score. The guide explains both pieces and provides no-fit setup. Historical Phase 3 private backup/absolute MLflow paths remain disclosed; completed-study scoring/core replay uses the final payload. Hash guards establish integrity, not safety of arbitrary serialization. Only trusted local bundles are supported.

Remaining limits: unauthenticated original official ZIP/download chain/retrieval time; retrospective September availability/target semantics; historical Taiwan existing accounts; no temporal/external/new-applicant validation; synthetic utility/monitoring; intervals conditional on fitted models/policies; no causal/profit/fairness-certification/production evidence. Documentation accurately qualifies these. No required execution check remains externally blocked after successful SQL escalation. Tests/inspection cannot cover every input, dependency/platform combination, concurrent filesystem race or future edit. No model searches or original fold models were retrained for fresh timestamps or increased confidence.

Maintained corrections cover inference, Phase 4 missing-value routing, monitoring,
Phase 5 CLI and the reproduction script, with four regression modules and
updated technical documentation. Accepted scientific artifacts remain unchanged.
No model searches or scientific re-execution are needed for these corrections.
