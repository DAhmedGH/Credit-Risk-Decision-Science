# Independent audit and fix review

This is a review of the project audit's maintained-code fixes. It does not replace or reseal historical phase acceptance receipts.

The scientific inspection, original reproductions and recomputations are recorded in [scientific-audit-notes.md](scientific-audit-notes.md), [bootstrap-verification.json](bootstrap-verification.json), [recompute-bootstrap.py](recompute-bootstrap.py), and [verify-scientific-alignment.py](verify-scientific-alignment.py). These contain code and aggregate evidence; no customer records are included. Execute the scripts from the project environment with the repository installed. They infer the repository root from their location. The missing-input reproduction adds the repository's `tests` directory for synthetic fixtures.

## CSV parser correction

Read `src/credit_risk/inference.py` and `tests/test_audit_inference.py` directly and compared the old pandas-only parse with the new structural validation. The strict CSV prepass rejects short and extra-width rows before pandas can infer an implicit index and shift identity/predictors. It rejects NUL bytes before pandas can truncate an identity/amount and supplies the physical ending line in malformed-record errors. CSV header uniqueness remains enforced; UTF-8 BOM, quoted commas, quotes, embedded newlines, missing financial cells and a valid header-only empty batch remain supported.

Executed `pytest tests/test_audit_inference.py tests/test_phase5.py -q`: **23 passed in 20.33 seconds**. Additional independent temporary-file probes preserved identifiers `0001`, literal `NA`, quoted commas, embedded newlines and quotes through CSV and Parquet, including UTF-8 BOM CSV input. No fitting or accepted scientific artifacts were involved.

The extra format probe identified a remaining consequence: Parquet `record_id='original\x00suffix'` passed identity validation, but its CSV output could be silently truncated to `original` by ordinary pandas CSV reading. This was corrected through cross-format identity validation and regression coverage. The subsequent correction in `validate_batch` rejects NUL-containing identities before row validation/prediction across Parquet and direct DataFrame input. The two new format-specific regressions use a predictor that fails if called. Inspection covered the guard and tests and independently reran parser/Phase 5 coverage: **25 passed in 14.33 seconds**. This finding is resolved; no accepted outputs are affected.

## Monitoring preservation correction

Read the complete monitoring diff and `tests/test_audit_monitoring.py`. The early guard rejects nonempty aggregate destinations before prediction. A separate pre-scoring guard rejects existing customer receipt directories, including interrupted runs whose aggregate destination remains empty. Receipt-directory creation is exclusive and the aggregate destination is rechecked before writing. Existing empty output directories remain supported for compatibility. A failed or repeated run cannot silently replace the previous aggregate/customer evidence through the original `exist_ok=True` behavior.

The focused tests preserve and byte-compare both report and customer receipts; a predictor that raises if called verifies guard ordering. The existing receipt replay and stale-runtime regressions exercise distinct paths. Independent execution of `pytest tests/test_audit_monitoring.py tests/test_phase5_monitoring.py -q` completed: **13 passed in 23.74 seconds**. No unresolved material defect was found in this correction. No original accepted monitoring output was regenerated or overwritten.

## Scope and limitations

The audit fixes leave original fitted identities, mapping, scenarios, policies, cutoffs, saved predictions and freeze manifests intact. Core source changes intentionally invalidate exact historical preflight against the working tree; original source/commit is required for unchanged scientific reproduction. This review does not establish absence of other bugs, externally authenticated workbook acquisition, remote CI execution, temporal robustness or production suitability.

The retained assertion-based alignment and missing-input scripts reject Python `-O` before data access. These guards were executed and both correctly exited with RuntimeError. Ruff passed on retained evidence scripts without suppressions. Bootstrap reconstruction prints aggregate JSON by default; `--output NEW_PATH` optionally writes it exclusively, preserving existing evidence. The original bootstrap was not repeated solely for formatting or path changes.

## Public command and reproduction validation corrections

Read the `phase5.main` argument-validation/readiness-path changes, the early optimized-Python guard in `scripts/reproduce_phase5.py`, and all six command regression cases. Required `score`/`monitor` flags now fail with argparse exit code 2 before preflight or loading. Relative evaluation readiness paths resolve under the explicit project root; absolute paths remain explicit overrides. The reproduction guard exits before imports/output creation when Python optimization would disable assertions. Independent command-test execution: **6 passed in 12.38 seconds**. The tests prevent artifact access with raising sentinels and use only mocked evaluation; no scientific evaluation was launched.

After portable evidence-script formatting, the numerical AST from saved-frame loading through bootstrap result construction was compared with the exact originally executed independent script and was unchanged. The optional bootstrap CLI help also executed successfully without data access.

## Underlying Phase 3 evidence

The preserved runtime was available read-only. Executed `verify-development-oof.py --model-root /home/danieal/credit-risk-backups/phase3-20261008-195946/runtime --output reports/project-audit-evidence/development-oof-verification.json`. The script requires the external historical runtime explicitly and produces aggregate evidence only. All **2,682** preservation-inventory paths matched recorded SHA-256 and byte counts (**131,298,257 bytes**); inventory SHA also matched the accepted receipt. No serialized model was loaded.

Independently recalculated all 48 search candidates' **864,000** saved development OOF rows: exact frozen ID coverage/order, fingerprint/fold alignment, label agreement across candidates, **960** fold metric cells, **192** pooled metric cells and **384** mean/SD cells. Maximum absolute metric discrepancy was **8.326672684688674e-17**, within 1e-12. Recorded family CV-fit counts were 60/60/120; no fits were performed. Raw labels were not reread, so label agreement here is across existing saved development evidence, complementing the separate ingestion/hash/loader inspection. Full result: [development-oof-verification.json](development-oof-verification.json).

## Underlying Phase 2 evidence

The original nine baseline artifact directories were also available. Independently ran `verify-phase2-oof.py --output reports/project-audit-evidence/phase2-oof-verification.json`. All **101** manifest artifact hashes matched. All **162,000** saved development OOF rows across nine variants matched frozen ID coverage/order and fingerprint/fold assignments, and saved labels agreed across variants. Recomputed **180** fold metric cells, **36** pooled metrics and **72** fold mean/SD cells; maximum discrepancy **8.326672684688674e-17**. No model was loaded/fitted, and no raw source outcomes or final-test outcomes were read. Result: [phase2-oof-verification.json](phase2-oof-verification.json).

## Final report/findings and guide review

Read the completed draft of `reports/project-audit.md`, `reports/project-audit-findings.json`, the relevant source/SQL/tracking receipts, updated progress/decision/exposure records and reproduction-guide edits. Compared the reported model values, bootstrap counts/errors, OOF/group/calibration/SHAP evidence, eight findings and 24 new cases with direct inspections and this review's executed checks. Audit timing crosses October 10 UTC while remaining October 9 in America/Toronto, as documented. Full-suite/live-SQL results were inspected separately; those executions were not repeated in this review.

The reviewed guide preserves accepted source `fb022d9`, supplies an explicit new restored-copy environment setup and pinned-container alternative, and explains why fixed maintained core source intentionally fails exact historical preflight/report. Current standalone scoring retains the original transformations/bundle. Historical container and acceptance receipts remain clearly distinct from current local validation.

Requested small report corrections during review: explicitly include the verified Phase 2 baseline evidence; distinguish predeclared saved-evidence comparisons from prohibited new test-driven choices/exploration; attribute the BOM check to an independent temporary-file probe rather than the 11 added parser/identity cases. No discrepancy in accepted scientific outputs or substantive fix behavior was found. This review supports the bounded audit verdict after these documentation clarifications; it does not assert zero defects or replace original acceptance receipts.

## Closeout

Re-read the final report and structured findings after integration. All three requested prose clarifications are resolved: the Phase 2 baseline verification appears explicitly, the scientific-execution statement distinguishes new exploratory final-test comparisons from frozen-evidence reconstruction, and A001 distinguishes eleven regression cases from the independent BOM probe. The added policy receipt records all 88 policy/scenario rows and 396,000 saved masks/counts/rates without reselection; these counts agree with the frozen eight-policy/eleven-scenario reporting contract. This review inspected that receipt and attribution, without repeating numerical evaluation.

Reviewed the retained database-check helper's new --output argument and early existing-file/symlink refusal. It preserves the original database.json receipt, permits an explicitly new receipt for repetition, and rejects existing output before workbook hashing, exposure logging or database access. The original executed numerical reconciliation remains historical evidence.

The completed bounded audit scope passes with the documented resolved findings and remaining limitations. Original frozen scientific acceptance remains supported; all historical receipts retain their original meaning and were not resealed. This closeout does not assert absence of other bugs or unverified external validity.

Independently exercised the database helper against the existing receipt: `python reports/project-audit-evidence/verify-database.py --output reports/project-audit-evidence/database.json` exited **2** with the expected `choose --output NEW_PATH before any source access` error. No numerical/source/SQL reconciliation was repeated.
