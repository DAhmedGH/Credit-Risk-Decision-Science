# Independent review: allocation, SQL, and ingestion

This technical summary preserves recorded findings and checks. Original review
documents and hash-bound receipts are retained privately. These checks were
performed at the dated checkpoint, not repeated for presentation cleanup.

Review date: 2026-10-06. Scope: `src/credit_risk/splits/allocation.py`, split exports/tests, `sql/001_schema.sql` through `003_feature_export.sql`, `src/credit_risk/data/database.py`, `phase1.py`, `__main__.py`, integration tests, and the configuration/Compose identity guards used by ingestion. The review did not change these modules, split artifacts, or database contents.

This is an independent review of allocation and database work by the data/feature implementer. Comparison of SQL with that implementer's Python feature definitions verifies the cross-language contract; it does not constitute a second author's independent review of those Python definitions. No real workbook outcomes, predictive models, or held-out EDA were accessed during this review.

## Findings

| Severity | Affected paths/evidence | Scientific consequence | Concrete correction / disposition |
| --- | --- | --- | --- |
| High: verification dependency | `sql/001_schema.sql`, `002_curated.sql`, `003_feature_export.sql`; `data/database.py`; real source and service artifacts | Source-to-export reconciliation, actual PostgreSQL expression behavior, transaction rollback, and reingestion stability are not established by static inspection or mocks. Phase 1 cannot pass its real-data exit gate without them. | Run the documented workflow in the isolated Python 3.12 environment against the labeled disposable PostgreSQL instance; ingest the verified workbook twice, verify SQL/Python feature equality, and retain count/reingestion evidence. Include a runnable fixture-based database integration check. Pending because the original environment cannot access Docker or install dependencies. |
| Medium: EDA provenance; resolved by code inspection and fixture checks | `src/credit_risk/phase1.py:eda` / `reports/development_eda.json` | The original EDA report omitted its feature-contract and code identity. | The current report includes stage metadata, feature version, dataset version, source/split hashes, and dependency-lock identity. `write_run_evidence` preserves previous snapshots, permits only execution code/commit identity changes, and rejects changed scientific dependencies/results. Reinspected; fixture test passed. |
| Medium: standalone audit export verification; resolved by inspection and synthetic probe | `src/credit_risk/phase1.py:features` | The standalone export originally verified counts and predictors but could export a modified audit row without comparing it to the source. | The current command calls `verify_persisted_records` before any export query or file write. A synthetic probe confirmed a persisted-data disagreement aborts before both. Actual PostgreSQL behavior remains in the pending live check. |

No critical or high-severity defect was found in the inspected allocation or feature expressions. The verification dependency is a real gate, not a claim that source or database checks failed. No raw-data or live PostgreSQL result is represented as passed.

## Allocation inspection and evidence

The default financial fingerprint imports the exact 19-field raw financial allowlist. Its JSON payload includes the fingerprint version, ordered field names, and canonical numeric values. Labels, identifiers, and audit fields are excluded. Integer/float/Decimal equivalents and signed zero share a representation; missing values remain distinct, and missing columns fail. Neither learned filling nor category fitting occurs. A probe changed each of the 19 financial values separately and confirmed all change the fingerprint; simultaneous changes to ID, label, and demographics left it unchanged.

Groups preserve all customer IDs and both class counts. The allocation objective uses row counts plus both binary-class counts rather than assigning a majority label to a mixed group. Group order derives from size/rarity and seed-based hashes, followed by sorted IDs; output does not depend on input order. The reservation guard requires enough class-carrying groups for all partitions and all five development folds. It rejects infeasible inputs instead of changing the grouping rule or retrying seeds.

An independent recursive feasibility calculation enumerated assignments for 4,500 small resource/quota cases and matched `_can_fill` in every case. One hundred varied synthetic group datasets allocated successfully, passed every reported integrity check, and reproduced identical manifests/summaries after reordering. A further 120-row full-schema fixture passed default allocation. These are software-test observations, not dataset measurements or empirical guarantees of optimal class balance. The implemented greedy method reports its actual size deviations rather than claiming globally optimal allocation.

The summary contains assignment sizes, fingerprint counts, deviations, source/schema/assignment hashes, and boolean class-presence checks. It does not emit held-out class counts, prevalence, charts, or example labels. `validate_manifest` regenerates the fixed allocation and rejects altered source hashes, IDs, assignments, folds, seeds, or financial fingerprints. Class-label access is confined to stratification and structural feasibility checks in these modules.

The executed command was:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_splits.py' -v
```

All 11 tests passed under the available Python 3.14. The additional adversarial probes used only standard-library code and synthetic records; no project service or source workbook was opened.

## SQL and transaction inspection

The predictor view and export contain only the explicit financial allowlist and 13 engineered fields, plus provenance/join keys. Labels have their own view and demographics their own audit table. No imputation statistic, learned category vocabulary, percentile cutoff, or population aggregate enters the SQL feature formulas.

All 13 formulas were compared with the Python definitions. April-to-September order, July–September minus April–June positive-delay contrast, signed utilization/change, population rather than sample bill standard deviation, and zero-payment counts match. Six-value completeness guards prevent PostgreSQL `GREATEST` null behavior from silently filling missing histories in the status and aggregate summaries. The September-payment/August-bill proxy uses only a positive denominator; aggregate ratios use positive bill balances and require all dependencies. The two missingness flags match Python. This is static parity evidence; PostgreSQL execution remains pending.

`connect_database` checks database name, role, and project/disposable lifecycle settings. `ingest_records` repeats that check inside its transaction before locks, DDL, or writes. A synthetic mocked connection with an incorrect database/lifecycle was rejected after its identity query and before any mutating statement. Compose binds loopback, names a dedicated project volume, and the service runner checks ownership labels and host-port availability before creating new project resources.

The ingester uses a transaction, a source-hash primary key, and source/customer composite keys. A repeated source with the same rules, feature contract, version, and counts takes the no-append path. A mismatched signature raises rather than overwriting provenance. Source, curated, rejected, audit, and feature-export counts are checked before transaction exit. Per-ID SQL features are compared against Python values before commit. The static control flow supports the intended atomic/idempotent behavior; mocks do not establish live rollback or second-ingestion results.

`tests/test_database.py` supplies a live fixture check gated by `CREDIT_RISK_SQL_TEST=1`. It covers missing histories, zero denominators, quarantine, second-ingestion counts, per-ID SQL/Python parity, detection of a changed persisted label, and rollback inside an outer fixture transaction. The review ran its three fixture-only contract tests successfully; the live test was skipped because PostgreSQL is unavailable. This is appropriately a pending check, not evidence that SQL ran.

## CLI, source access, and EDA inspection

`provenance_context` verifies original workbook bytes against both pinned SHA-256 and byte count; `source_records` records permitted structural target access before parsing and checks that the parsed checksum still matches. Access-log entries identify the source, any existing split manifest, stage, and timestamp, including parsing attempts that later fail. No unobserved download date is manufactured by this logic. At initial review the provenance manifest was pending; subsequent reinspection independently hashed the supplied workbook bytes and confirmed the pinned hash/size, explicit unknown acquisition date, absent ZIP/null ZIP checksum, and current feature-contract artifact. The review did not decode any source outcomes. The source manifest honestly qualifies the bounded BIFF diagnostic and pending canonical xlrd comparison.

`freeze_splits` validates an existing manifest against the fixed allocation rather than replacing it. A stale/altered manifest fails. Summary evidence retains the original reader qualification when another reader later confirms assignments. Model-oriented reporting only runs after a manifest exists and validates. `development_report` filters to development IDs before feature summaries or default counts; full-source accesses in manifest validation are confined to structural stratification checks. A sentinel test makes held-out features/labels unaggregatable and confirms they cannot enter the reporting calculations, while isolating the separately tested structural validator.

`reproduce` orders validation, actual ingestion twice, export parity, split freezing, and development EDA. Neither CLI nor orchestration imports or calls a predictive estimator. Whole-source label and audit exports remain separate from the predictor contract.

The review also ran:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_phase1.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_database.py' -v
```

The four Phase 1 tests and three fixture-only database tests passed; one live PostgreSQL test was explicitly skipped. Across these commands and the split command, this review ran 18 passing tests and one skipped integration test under Python 3.14.

## Correction reinspection

The reviewed `uci350-v1.1` / `financial-row-v1.1` corrections retain original draft artifacts and the original split manifest/summary. A content-addressed receipt binds the revised feature contract, dataset version, reader qualification, and validated assignments without replacing the original summary. A synthetic revised-contract/reader probe confirmed the split and summary stayed byte-identical, a distinct receipt was added, and all captured writes stayed inside its `TemporaryDirectory`. The receipt test writes beside the supplied manifest, not into repository artifacts.

PostgreSQL financial amounts now use `numeric`, with `Decimal(str(value))` adaptation. The persisted-data comparator runs on first ingestion, no-op ingestion, and standalone feature export. It compares raw records, source row order, accepted/quarantined status, rejection reasons, exact financial values, labels, audit values, and audit groups against the validated source. Synthetic probes passed for Decimal adaptation and detection of changed financial values, target, demographics, audit-group strings, and rejection ledger. Counts and floating-point feature tolerance cannot substitute for these exact persisted-value checks.

`write_run_evidence` archives prior reports before changing execution-only Git/code provenance. Scientific values, rules hashes, feature hashes, source identity, and lock identity remain invariant unless a new report version/path is used. The added fixture test confirmed previous evidence survives and changed row results fail. EDA now includes the missing feature/code metadata, resolving the provenance finding. The standalone export guard resolved the second medium finding by aborting before export/query/file output in a synthetic disagreement probe.

The review reran `test_phase1.py`: five tests passed. `test_database.py`: three fixture-only tests passed and the one live test remained explicitly skipped. The bounded-inspection wrapper was also read: it verifies the pinned bytes, logs permitted source access before invoking any numeric decoder, rejects optimized Python that would disable the original diagnostic assertions, and preserves the original bounded parser code for traceability. It was not rerun by this review and cannot replace canonical xlrd/PostgreSQL evidence.

## Review disposition

All medium findings from this review are corrected within the code-inspection and synthetic-test scope. The real split/receipt artifacts are qualified as diagnostic-reader evidence, and the raw-profile split contract is unchanged. Phase 1 remains pending canonical Python 3.12/xlrd setup and source-reader parity, actual PostgreSQL reconciliation/rollback/idempotency/SQL parity, and unavailable environment checks such as Ruff. This review does not pass those checks by inference. No change to a modeling choice or policy was made from held-out evidence, and no predictive model was trained.
