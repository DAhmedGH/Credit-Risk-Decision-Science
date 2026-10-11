# Final independent audit

Audit date: 2026-10-11 UTC. Disposition: **PASS WITH LIMITATIONS** for the publication checkout with the uncommitted corrections described below.

The recorded Git states and execution results below describe the completed audit
before the subsequent delivery commit. They remain dated evidence; the delivery
review is recorded at the end of this report.

No critical or high scientific, software or public scoring blocker was identified. One medium receipt-integrity defect was independently reproduced and fixed locally. The unchanged public revision still contains that defect; these corrections have not been delivered remotely. Historical replay is unavailable from the public clone, several original acquisition facts remain unknown, individual bootstrap replicate statistics were not retained, historical execution paths remain public, and no repository-wide code license is declared. These limits qualify the disposition. This audit does not prove that all bugs or all historical leakage are absent.

## Revisions, scope and independence

| Evidence | Revision and state |
| --- | --- |
| Publication checkout at start | Branch `main`, HEAD `13d9f8670df42024b3a8a7f9a34ced91a6371996`, clean working tree and index; no pre-existing edits |
| Remote | `https://github.com/DAhmedGH/Credit-Risk-Decision-Science.git`; public `main` matched that HEAD initially and on the later remote check |
| Fresh public clone | The actual HTTPS remote was cloned into a new temporary directory at the same full revision; all 341 tracked files initially matched the publication checkout byte for byte; clone remained clean |
| Corrected execution export | Public clone files plus the two inference changes, two regression-test changes and batch-scoring guide change; no original/private files copied into execution images |
| Tested corrected source identity | SHA-256 of the canonical 71-file `src/`, `tests/`, `scripts/` Python hash map: `0a8e6411675e28e8a80e770cb10e9f16ced587f2898bb9e9c37b30ac2fa8aaf9` |
| Original project, corroboration only | Observed HEAD `3a051cb6dc56578f4adcb69876005695c3c0f0c3`; later status showed only untracked `publication/`; original tracked files were not edited |
| Historical accepted source | Recorded source commit `fb022d9dca79d6aee1a565a62c36df33ece743e2`; distinct from the publication revision and the current original checkout; no historical reproduction command executed |

The parent `AGENTS.md` was read before the audit; no additional publication instructions were found. The audit proceeded through inventory/provenance, source and scientific-evidence review, public-clone execution, then limited corrections and preservation checks. Earlier passing reports were examined as historical evidence rather than accepted as new verification.

The maintained implementation, configuration, SQL, packaging, locks, Docker context, CI, public bundle, README and guides were reviewed. Five reachable public commits and 386 blob objects were inspected for selected secret patterns, without copying detected path values into this report. All 81 tracked Python files parsed successfully. The initial 336 local Markdown targets, images and anchors resolved. External link verification was selective, not a crawl of every external URL.

Public execution used only public bytes. Original source data and saved evidence were accessed separately, read-only, to corroborate scientific history and recompute arithmetic. The original numerical environment was used only for those arithmetic checks, never to make a public installation pass. Host Python was 3.14.4; execution images used the pinned Python 3.12.11 and 72-package lock. Numerical library thread counts were limited to one. Cached Docker dependency layers were accepted and identified below.

## Findings and dispositions

The [machine-readable findings](final-independent-audit-findings.json) contain the affected locations, triggers, expected/actual behavior, impact, correction, verification and final disposition for every finding.

| ID | Severity | Finding | Final disposition |
| --- | --- | --- | --- |
| F001 | Medium | Input receipt could identify bytes different from those parsed/scored | Fixed and verified locally; remains in unchanged public HEAD |
| F002 | Low | Public-content description omitted retained real UCI case metadata | Disclosure corrected locally; preserved evidence unchanged |
| F003 | Low | Personal execution paths remain in selected public files and history | Disclosed; exposure remains, historical evidence preserved |
| F004 | Informational | No repository-wide code license or package license declaration | Owner decision remains; no license invented |
| F005 | Informational | Individual bootstrap replicate statistics unavailable | Interval tables reconciled; percentile replay remains unverified |
| F006 | Informational | Multi-file scoring output is not an atomic transaction | Behavior verified and completion/retry guidance added |

**F001 — receipt integrity.** `src/credit_risk/inference.py:18` and `src/credit_risk/scoring.py:41` previously parsed a path and hashed it after scoring. An independent synthetic probe replaced that path between parsing and receipt creation: scoring still matched the original example, but the receipt matched the replacement file. CSV validation and pandas parsing used separate passes over the same open file. Expected behavior is that the recorded input hash identifies exactly the captured bytes used for validation and prediction. The practical impact is incorrect batch provenance under concurrent replacement, not a change in the frozen model.

The correction captures CSV/Parquet bytes once, parses that snapshot and records its SHA-256 in both public and historical scoring entry points. Three focused regression cases cover replacement before CSV parsing and after CSV/Parquet scoring. The corrected full suite passed, and the accepted example remained byte-identical. Capturing input bytes adds memory proportional to input size. A file modified while the operating system is reading it can still yield a mixed snapshot, but the parser and receipt identify the same captured bytes.

**F002 — public records disclosure.** `README.md:92` and `docs/publication-package.md:13` overstated content exclusion. Preserved Phase 4 `metadata.json:46`, `descriptive_metadata.json:46` and manifest metadata contain four real UCI policy-validation case IDs, labels and probabilities, plus explanation sample/background IDs. The split manifest also intentionally contains benchmark IDs and frozen assignments. These are distinct from the 12 synthetic scoring examples. No raw financial workbook, full customer export, private identity mapping or case records are in the five-member scoring archive. The documentation now makes this distinction; no historical receipt was redacted or rewritten.

**F003 — historical paths.** The current public inventory contains 33 matching locations in 21 files, including `configs/phase4.toml:3`, `src/credit_risk/models/phase4_inputs.py:21`, `docs/partition-access-log.md:55` and preserved reports/receipts. These disclose local execution details and cannot provide a public user with the referenced private files. The publication guide now acknowledges them. Removing hash-bound historical material or rewriting already public history was outside the authorized correction scope. No path values are reproduced here. Pattern scans found no private-key, GitHub-token, AWS-access-key, credentialed-URL or email matches; manual configuration review distinguished explicit fixture credentials and placeholders. This is a bounded inspection, not a guarantee that no secret can exist.

**F004 — licensing.** `pyproject.toml:5` has no license declaration and the repository has no `LICENSE` file. UCI attribution, DOI and CC BY 4.0 data/model notices are present; the scoring notice explicitly does not establish a code license. Scientific inspection and scoring remain possible, but general code reuse terms are unresolved. Only the owner can choose a license.

**F005 — bootstrap evidence.** The source construction and 341 saved interval entries were checked, including agreement between CSV/JSON representations and undefined-count accounting. No individual replicate statistic arrays were found. Consequently percentile endpoints and the recorded bootstrap-plan hash were not independently regenerated. This limitation is consistent with the documented conditional interpretation and the prohibition on rerunning bootstrap analysis.

**F006 — partial writes.** `src/credit_risk/scoring.py:52` writes two CSVs before the atomic JSON receipt (`src/credit_risk/artifacts.py:42`). An independently injected failure on the second CSV left only `scored.csv`, propagated the error, omitted the receipt and rejected a retry to the same existing directory. Output collision checks protect existing evidence; failed new outputs need a new destination. `docs/batch_scoring.md:91` now states this behavior and identifies the receipt as the completion marker. No transaction refactor was introduced.

## Scientific reconciliation

### Dataset, groups and development

The official [UCI dataset page](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) supports the historical Taiwan credit-card context and next-month default target. The project uses one labeled snapshot per customer, April–September 2005 histories, and assumes all September predictors are available at month end. This assumption is a recorded operational contract, not independently established outcome timing or contemporary lending suitability.

The preserved official comparison receipt records a subsequent retrieval at `2026-10-10T18:00:23.006402Z`. A new official archive retrieval was independently checked at `2026-10-11T06:04:38.041349Z`: HTTP 200, verified TLS, 5,539,494 archive bytes, SHA-256 `56c885f84457f6680f8438f02bfcdac9579323d8a94465ee5f26e32baa727602`. Its sole 5,539,328-byte workbook member has SHA-256 `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`, matching the existing original workbook and accepted source manifest byte for byte. Workbook cells were not decoded during this audit. Neither comparison reconstructs the original acquisition date, download chain or original archive checksum.

All 30,000 saved financial fingerprints were independently recomputed from the 19 raw financial predictors. Group membership, unique record identity, disjoint partitions and frozen folds reconciled:

| Partition | Rows | Financial-profile groups |
| --- | ---: | ---: |
| Development | 18,000 | 17,508 |
| Calibration fitting | 4,500 | 4,378 |
| Policy validation | 3,000 | 2,919 |
| Final test | 4,500 | 4,378 |

Each of five development validation folds contains 3,600 rows. These groups identify identical financial profiles, not proven households or independent economic clusters. IDs, target and demographic audit attributes are excluded from predictors and grouping. Thirteen deterministic engineered features were independently reconstructed: 390,000 saved values reconciled, maximum absolute difference `1.8189894035458565e-12`. Learned imputation, scaling, vocabulary and model fitting are inside fold pipelines. Seventy stored baseline/reference fold receipts independently reconciled fit/validation ID hashes, training-only class counts and effective weights. These receipts and source checks support the recorded fit scope; passing fixtures alone do not establish historical isolation.

All 62 saved OOF files had exactly 18,000 development records with matching IDs, frozen folds, fingerprints, labels and positive class 1. Independently recomputed fold metrics, means, standard deviations and pooled metrics reconciled across 1,784 fields. The bounded search recorded 48 candidates: 12 logistic, 12 forest and 24 XGBoost. The recorded AP tolerance 0.01 admits 17 candidates; the 0.001 practical log-loss band retains the two documented XGBoost candidates, and the selected 100-tree model satisfies the recorded simplicity ordering over the 200-tree alternative. No selection procedure was rerun. All 24 matched engineered-feature contrasts improve AP/log loss/Brier, while all 24 weighting contrasts worsen log loss/Brier within the recorded development comparison.

Selected fold-mean AP is `0.5612527444711741`; pooled OOF AP is `0.5589734398765549`. They are distinct quantities and the maintained model-selection narrative uses the fold aggregate.

### Calibration, policies and saved final outcomes

Five accepted model metadata records bind development-only fitting, positive class 1 and the preserved pipeline hashes. Calibration receipts identify separate 4,500-row mapping fitting and 3,000-row policy validation, zero base-model refits and two mapping fits. Twelve validation metric fields were recomputed from saved raw/sigmoid/isotonic probabilities. Their log losses are respectively `0.43298871400379296`, `0.43622831898160774`, `0.4559940960180188`; retaining the raw mapping follows the recorded practical-improvement rule.

All 88 frozen policy definitions and 396,000 existing final decisions reconcile by record ID and order. Cutoff policies accept strictly below the cutoff; equality abstains. Fraction policies retain validation-derived scalar cutoffs and do not rank/select anew on test batches. The analytic cutoff follows `(gain - cost)/(gain + loss)`, with explicit degenerate abstention handling. Expected acceptance utility is `(1-p)*gain - p*loss - cost`, and abstention utility is zero. Eleven sensitivity scenarios retain their separate identities, including the documented abstain-all case. These are synthetic payoff assumptions, not actual lending profit, causal benefit or avoided loss.

Existing final prediction vectors were read and their 24 model metric fields independently recomputed; no new final predictions or accepted evaluation command ran. Selected-model AP is `0.5642176410184566`, ROC-AUC `0.7939820067943004`, log loss `0.42331365771732493`, Brier `0.13319703405584427`. The forest has AP `0.5663601841455993` and log loss `0.42301349563375373`; the selected vector remains exactly the raw probabilities of `xgboost_05_engineered_none`. Documentation correctly preserves development selection despite reference results.

All 1,760 final policy metric fields reconciled. The base empirical cutoff remains 0.085: 1,028 accepted, 55 accepted defaults, 973 accepted nondefaults, benchmark utility 21,150 total / 4.70 per customer. Predicted expected utility is 16,461.54038766399 total / 3.6581200861475534 per customer. It is explicitly distinct from benchmark utility calculated with saved outcomes.

The 106 freeze members and independent-review receipt binding were verified. This supports consistency of the frozen record and chronology. It cannot independently reconstruct every human action or access before the freeze.

### Uncertainty, explanation, summaries and monitoring

Bootstrap code samples sorted fingerprint groups with replacement, preserves their members and pairs models/policies on the same draws; row counts can vary. The recorded seed is 42 and repetition count 1,000. The 341 saved interval entries agree across formats. Intervals describe evaluation-sample uncertainty conditional on fitted models/policies, excluding development, temporal and external uncertainty. Replicate statistics and percentile replay are unavailable (F005); no bootstrap plan or sampling was regenerated.

Saved SHAP arrays have 1,000 rows and 89 expanded features: 996 development rows and four selected policy-validation cases, with a 100-row development background. Seeded sampling, membership and case selection reconciled. Maximum raw-log-odds additivity residual is `1.431484473179978e-6`; all 89 saved mean-absolute importance values reconcile. No SHAP explanations were recomputed. Attribution is model-specific, depends on background/sample choice, and is neither causal evidence nor calibrated-probability attribution.

Fifteen demographic summary rows and four suppressed rows were checked against minimum support of 100 records and 20 of each class. Unsupported performance quantities are blank. Demographic exclusion does not establish fairness; descriptive and behavioral associations do not establish causal effects.

Six monitoring scenarios and 198 PSI distribution entries reconciled from saved counts with the recorded epsilon and normalization. All 32 development-derived feature bin/reference counts, 6,000 saved draw positions/IDs/counts and 300 corruption positions were independently checked; eight mixture metrics were recomputed from existing saved validation probabilities. No new model predictions or monitoring command ran. Corrupted-history performance is suppressed, quarantine counts reconcile, and PSI bands describe synthetic distribution diagnostics rather than validated real-world alarms.

### Recorded evidence access and unavailable replay

Saved development OOF, calibration/policy receipts, policy-validation probability/outcome vectors, final prediction/decision vectors and aggregates, SHAP arrays, demographic summaries, monitoring receipts and label-free financial exports were read for this audit. The successful principal arithmetic access record is `2026-10-11T06:06:00.233307Z`; supplemental read-only arithmetic followed during this audit. Earlier shape inspections and unsuccessful audit-harness attempts also accessed saved vectors. Raw workbook cells and new final-outcome conversions were not performed. This is subsequent review of already observed outcomes, not a claim that the auditor was blind to final labels. No original access log was rewritten; this report records the new access.

Public scoring is reproducible from the clone. Historical training, calibration, searches, source-bound replay and accepted final evaluation require private original inputs, model stores, backup and complete accepted-source attachments. Their recorded methods and available saved evidence were inspected; their scientific executions were not replayed. Source-only fixture success cannot fill those missing public dependencies.

## Implementation and edge cases

Direct review covered inference validation/features, artifact restoration/loading, CLI/configuration, model pipelines, policy calculations, monitoring, supporting scripts and SQL transaction/idempotency behavior. Maintained regression coverage exercises malformed quoting and uneven CSV widths, duplicate headers/IDs, missing/extra columns, NUL, nonnumeric/nonfinite values, empty/all-quarantined batches, transformation overflow, policy ties, positive-class mapping, artifact/source/runtime tampering and output collisions. Unknown categories and extreme finite values may remain scoreable; this does not demonstrate distribution support or operational validity.

Independent synthetic probes established quoted comma/multiline and leading-zero identity preservation, single-row/batch equivalence, finite extreme-input behavior, and 264 exact/adjacent-float boundary calculations across all 88 policies. Valid/scored and quarantined rows retain source positions and reconcile to input size. The verifier was read before use; its guards cover unintended fitting, database access, network/tracking and model mutation on the public route.

The public restorer streams only five allowed regular members, bounds compressed/decompressed/member sizes, rejects unsafe paths, links, duplicate members and sparse/extended-header abuse, and requires a new destination. A separately pinned manifest binds model, schema, policy, transformation modules and runtime. Deserialization receives verified captured bytes only after explicit trust acknowledgement. Optimized Python verification and an independently injected model tamper both confirmed checks remain effective before `joblib.load`. Integrity is not a license to deserialize arbitrary trusted-by-caller models.

The separate historical restorer was inspected but not executed. It checks its recorded digest and traversal/link/type hazards; it does not provide all duplicate/decompression bounds of the maintained public restorer. It remains a trusted, recorded historical-payload route, not a general untrusted archive importer.

The SQL fixture route checks disposable-database markers, transaction rollback, reconciliation and repeat ingestion. Four live fixture tests passed against a new isolated PostgreSQL 16 instance, with no host ports, shared database or persistent volume. All fixture relations rolled back; the audit-created database container was removed.

## Commands, environments and outcomes

Commands below use `AUDIT_TMP=/tmp/credit-risk-final-audit.A2gOHg`, `public/` for the untouched clone and `repaired/` for the corrected public-file export. Private evidence paths are deliberately represented by placeholders. Full scientific reproduction commands were not run.

| Check | Actual execution and result |
| --- | --- |
| Remote and clone | `git ls-remote ... HEAD refs/heads/main`; `git clone https://github.com/DAhmedGH/Credit-Risk-Decision-Science.git "$AUDIT_TMP/public"` — succeeded after sandbox DNS restriction required approved network access |
| Public Docker build | In `public/`: `docker build --progress=plain -t credit-risk-final-audit:13d9f86 .` — passed; base, dependency and unchanged COPY layers cached; no claim of fresh dependency downloads |
| Documented default Docker tests | `docker run --rm --network none credit-risk-final-audit:13d9f86` — **270 passed, 1 expected live-SQL skip**, 57.70 s, in the documented writable container mode |
| Public read-only scoring | `docker run --rm --network none --read-only --tmpfs /tmp credit-risk-final-audit:13d9f86 python scripts/verify_public_scoring.py` — passed; no bind mounts or private inputs; 12/12/0 example, 12/10/2 quarantine fixture, 0/0/0 empty batch; byte-exact example output and all 88 policies/utilities |
| Actual CI invocation | Full public-context image; temporary writable copy, pinned inherited venv, `python -m pip install -r requirements.lock`, `python -m pip install --no-deps --no-build-isolation -e .`, `python -m pip check`, the three actual smoke scripts, `ruff check .`, **`pytest -q`** — all passed; **270 passed, 1 expected live-SQL skip**, 53.18 s |
| Isolated public SQL | Actual CI database-marker statements; `CREDIT_RISK_SQL_TEST=1 ... pytest -q tests/test_database.py` against the audit-created PostgreSQL instance — **4 passed**, 0.26 s |
| Corrected full suite | Corrected public-context image; editable installation and no `PYTHONPATH`, `python -m pip check`, `ruff check . --no-cache`, `CREDIT_RISK_SQL_TEST=1 ... pytest -q` — **274 passed, zero skips**, 47.68 s, including three new regression cases |
| Corrected Docker build | In `repaired/`: `docker build --progress=plain -t credit-risk-final-audit:repaired .` — changed source/test COPY layers rebuilt; base/dependency layers cached |
| Corrected optimized scorer | `docker run --rm --network none --read-only --tmpfs /tmp credit-risk-final-audit:repaired python -O scripts/verify_public_scoring.py` — passed with unchanged example output |
| Installed wheel | `docker run --rm -i --network none --read-only --tmpfs /tmp:rw,exec credit-risk-final-audit-public:repaired python - < "$AUDIT_TMP/wheel-check.py"` — built/installed ordinary wheel without dependencies, removed `PYTHONPATH`, ran from another directory; installed imports, console help, restore/verify/score, byte-exact example and optimized tamper rejection passed |
| Independent probes | `runtime-probe.py` and `input-race-probe.py` through container stdin with no network/mounts; `partial-write-probe.py` in corrected read-only image — boundary/identity checks passed, original receipt race reproduced, partial-write behavior confirmed |
| Saved-evidence arithmetic | `env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 <ORIGINAL_EVIDENCE_PYTHON> "$AUDIT_TMP/scientific-reconcile.py"` and supplemental `scientific-additional.py` — read-only arithmetic results described above; zero accepted scientific fits or evaluation/bootstrap executions |
| Static/final review | AST parse, bounded history scan, Markdown target/anchor inspection, hash preservation comparison and `git diff --check`; complete source/test/documentation diff reviewed |

Docker Desktop client/server were 29.8.0. The documented image was `sha256:d5a4d0e40263291fdbbf6f8b7dfd262cec5a34e87d6d65ece9347ddd2e477f89`; the corrected image was `sha256:be4de5beb4c0bda7d62d2daeaedeb8352fce90d8aba309edfe2c8efcc616c7a8`. Full-context check images were `sha256:3cd65170217c0e252aecee4d0d7b38a8c4ce3d212dba4ce9f86203463e85db6b` and `sha256:21b744b4b04a3e642dbf25db674fae3f11a79da9749b0b1f4cf7a964214f467b`. They copied only public tracked files, plus the local correction for the latter.

The maintained CI workflow was independently observed through the public GitHub API: HEAD run [38114444370](https://github.com/DAhmedGH/Credit-Risk-Decision-Science/actions/runs/38114444370) completed successfully, updated `2026-10-11T05:22:05Z`, including installation, all smoke scripts, Ruff, pytest and SQL steps. This is observed remote evidence at the audited revision, not a newly triggered run or a substitute for local execution.

### Failed attempts and skipped checks

- An additional, stricter full-suite invocation with `/app` read-only produced **7 failed, 263 passed, 1 skipped** in 46.82 s. The seven monitoring fixture failures attempted runtime receipt writes under `/app/artifacts/runtime/monitoring`. The guide prescribes a writable container for the full suite and read-only mode for the scorer. Exact CI in a temporary writable copy passed. This failure is retained as an unsupported extra execution mode.
- The initial wheel probe reached successful installed scoring, then console help failed because Docker's default `/tmp` tmpfs is `noexec`. The retry used the appropriate `:rw,exec` tmpfs and passed. No product change was required.
- An early independent total-utility comparison used an overly strict absolute tolerance of `1e-12`; two different reduction orders differed by approximately `1.8e-12`. Only the audit total tolerance became `1e-9`; per-customer/metric tolerance remained `1e-12`. Supplemental monitoring checks initially compared SQL-exported derived floats rather than inference reconstruction, and selected a small fixture receipt directory rather than the report-bound scientific receipt. Correcting those audit assumptions yielded matching development bins and draw evidence. No scientific result was edited.
- The host lacked Python 3.12, so a newly downloaded native host venv was not tested. Docker supplied the exact interpreter and lock, including editable and ordinary-wheel installation checks. Dependencies were already present at all 72 pins; index/download availability and other operating systems remain unverified.
- No real-data ingestion, training, search, calibration refit, policy/model reselection, historical reproduction/preflight, accepted final evaluation, bootstrap rerun or new SHAP execution occurred. Fixture estimators fitted only synthetic test data. No shared database, release, push, deployment or GitHub mutation occurred.
- Individual bootstrap statistics and complete public historical replay inputs remain unavailable. All external links and every possible filesystem-failure timing were not exhaustively tested.

## Preservation and final state

The public archive remains 29,213 bytes with SHA-256 `d2fb60ca57f3b8b39fc271b62a2f0386db35842a8389d3444a4e6d6af6ce1349`; sidecars match the public bytes. The accepted pipeline, feature schema and frozen-policy projection match the original bytes/definitions. Archive contents remain five regular members and contain no customer records or original execution paths.

The final preservation comparison checked all 341 initial tracked publication files, 601 protected original evidence files and 2,693 referenced Phase 3 backup files. There were zero original/backup changes and zero changes to publication artifacts, bundles, configuration, existing reports, examples, SQL or locks. All 71 tested runtime Python files still matched the tested corrected code map. Accepted fitted models, probability mapping, thresholds, policy definitions, saved predictions, decisions, bootstrap intervals, source manifests and historical receipts remained unchanged.

Seven tracked files changed: `README.md`, `docs/batch_scoring.md`, `docs/publication-package.md`, `src/credit_risk/inference.py`, `src/credit_risk/scoring.py`, `tests/test_audit_inference.py`, `tests/test_public_scoring.py`. These two audit reports are new untracked files. Nothing was staged or committed; branch/HEAD/remote remain as recorded. No historical report was rewritten. Final checks passed for 337 local Markdown targets/anchors, JSON syntax, new-report privacy patterns, whitespace and the complete diff. The companion JSON records the validation seal and Git state.

The necessary delivery action is owner review of the uncommitted correction and disclosures before any later publication. The current remote continues to expose the receipt race and prior wording. Code licensing remains an owner decision; historical path exposure and absent bootstrap replicate statistics remain explicit limitations. No additional general audit is required to close this authorized work.

## Delivery review — 2026-10-11

The correction, regression tests, disclosures and both audit reports passed the
requested delivery review. All 71 runtime Python files match the recorded tested
code map, so the 274-pass corrected suite, Ruff/dependency checks, optimized
scoring and installed-wheel verification were reused without rerunning them.
The change preserves validation, artifact trust, source/runtime compatibility,
positive-class mapping and overwrite checks. The regression tests replace the
input before parsing and after scoring, covering the captured-byte and receipt
mechanisms for CSV and Parquet.

This review corrected the F001 wording above: the former CSV parser rewound the
same open file between validation and pandas parsing. No implementation or test
change was needed. The report privacy review found no real credentials, private
customer values or personal execution-path values; the recorded PostgreSQL
credential is explicitly a synthetic disposable fixture. The public bundle and
all tracked scientific artifacts and historical evidence remain unchanged.
Original and backup preservation checks are the dated audit evidence above,
not newly replayed checks.

The user authorized staging these nine reviewed files and creating a local
delivery commit. The recorded audit's uncommitted Git snapshot is retained;
the later commit identity and resulting working-tree state are reported in the
delivery handoff. No push or publication is authorized or performed. The audited
public revision `13d9f8670df42024b3a8a7f9a34ced91a6371996` contains the old
receipt behavior; this correction has no new remote CI result. Remaining findings
and the **PASS WITH LIMITATIONS** disposition are unchanged.
