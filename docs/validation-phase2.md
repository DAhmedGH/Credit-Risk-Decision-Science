# Phase 2 independent scientific and code review

This technical summary preserves recorded findings and checks. Original review
documents and hash-bound receipts are retained privately. These checks were
performed at the dated checkpoint, not repeated for presentation cleanup.

Review scope: fixed development baselines, fold-fitted preprocessing, controlled
feature/weighting comparisons, out-of-fold predictions, metrics, and local
tracking. No calibration, policy-validation, or final-test outcome analysis is
outside this scope. This review does not choose a final champion.

## Phase 1 evidence recovered independently

The review inspected the project requirements, design, phase plan, progress,
decisions, exposure log, Phase 1 report and checkpoint receipt, reproduction guide,
feature/data/leakage contracts, source/export receipts, and canonical split
revalidation receipt. Reported WSL reconciliation and live PostgreSQL results were
already explicitly attributed; they were not rerun by this review.

A Python standard-library probe verified all seven checkpoint file hashes against
current workbook, split, feature contract, financial/label/audit exports, and
the original dependency lock. Byte hashing did not decode workbook cells or
parse label/audit values. Independent manifest inspection found 30,000 unique
customer assignments, fingerprint disjointness across partitions and development
folds, 18,000 development rows, and five 3,600-row folds. Non-development rows
had no fold assignment. The workbook and manifest bytes remain unchanged.

Canonical evidence identifies xlrd 2.0.2, the `Data` sheet, Excel header row 2,
30,000 accepted records, zero rejections, and all-row SQL/Python feature parity.
The canonical split receipt binds these unchanged assignments to the current
feature contract and records all integrity checks as true. No unresolved
scientific Phase 1 blocker was found. Missing Git initialization/commit remains
a documented repository-delivery limitation.

## Phase 2 review disposition

The review inspected `src/credit_risk/models/inputs.py`, `pipelines.py`,
`evaluation.py`, `src/credit_risk/phase2.py`, the CLI, `configs/phase2.toml`,
`requirements-phase2.in`, package metadata, all four new test modules, and the
synthetic import/train/save/load/local-tracking smoke script.
No unresolved scientific-integrity code finding was identified in these paths.
This disposition is static and qualified by the runtime blocker below.

| Area | Inspection and evidence |
| --- | --- |
| Held-out isolation | CSV records are matched to frozen development IDs before feature/label value conversion. The workbook is hashed, never decoded; audit values are never loaded. Assignment/source/export/contract bindings fail on changed inputs. An independent real-input guard ran successfully on exactly 18,000 development rows and matched every development fingerprint. |
| Learned transformations | An explicit selector removes metadata before fold-fitted `ColumnTransformer` branches. Numeric median imputation and logistic scaling, categorical imputation and vocabulary learning remain inside each fresh fold pipeline. Unknown categories encode to zero; names and order are recorded per fitted fold. |
| Weighting | Logistic and forest use sklearn `class_weight="balanced"`, recomputed from each actual fit's labels. The logged balanced formula receives those same fit rows. No global weights or resampling are used. Tests compare balanced fits to explicit fit-specific weights. |
| Baseline comparisons | Nine variants are prespecified: one unweighted prior dummy plus the two feature sets and two weighting settings for each learned family. Each uses identical five frozen folds; no champion selection or tuning is implemented. Majority hard predictions are separate from probability metrics. |
| OOF and metrics | Positive class 1 is located via `classes_`, not a fixed offset. Predictions retain IDs/folds/fingerprints/labels. Full coverage and assignment checks precede and follow CSV persistence. Fold metrics are recomputed from reloaded predictions and distinguished from pooled OOF metrics. Sample SD uses `ddof=1`. |
| Serialization and diagnostics | Each fold pipeline is saved and reloaded, with probability agreement checked. Error cases and the 0.5 classification diagnostic use development OOF rows only. Logistic warnings and iterations are recorded; failed convergence prevents a successful CLI validation result. |
| Tracking and provenance | An explicit local MLflow client URI avoids inherited remote tracking destinations. Parent/child run IDs, partition-named metrics, resolved pipeline parameters, fit IDs and weights, input/config/code/dependency hashes, package versions, timings, and compact result artifacts are recorded. Missing Git provenance is explicit. |
| Concurrency and scope | Folds and variants execute sequentially, forest workers equal one, and native thread pools are limited to one around fit/predict. No XGBoost, calibration, policies, SHAP, split regeneration, or final-test evaluation is introduced. |

Independent synthetic standard-library probes additionally confirmed that
unparseable held-out predictor and outcome strings are ignored, while incomplete
OOF coverage, duplicate IDs, wrong folds, and nonfinite probabilities are
rejected. These probes are software evidence, not real-data model results.
The review independently ran
`.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_model_inputs.py`:
**5 passed in 0.58s**. Modeling and tracking tests could be inspected but not
executed without their dependencies. A regression test covers strict JSON
encoding of the imputer's NaN configuration sentinel; this sentinel is encoded
as a string rather than permitting nonfinite reported metric values.

## Findings and limitations

| Severity | Affected paths/artifacts | Consequence | Correction or disposition |
| --- | --- | --- | --- |
| High: external execution blocker | `.venv`, expanded dependency closure, all measured Phase 2 model/MLflow outputs | The review confirmed NumPy, pandas, SciPy, scikit-learn, joblib, threadpoolctl, and MLflow skinny are absent. Preprocessing APIs, fit behavior, metric numerics, model serialization, tracking, convergence and measured comparisons cannot be independently runtime-verified. Phase 2 cannot pass its exit gate. | Install/resolve the declared pins in the isolated Python 3.12 environment when network access is available, run import/train/save/load smoke and modeling tests, deliberately lock the validated expanded closure, then run the actual CLI workflow and inspect measured artifacts. Do not fabricate run IDs or scores. |
| Low: failure lifecycle robustness, corrected after review | `src/credit_risk/phase2.py:run` | Initial post-parent filesystem/context setup outside the exception handler could leave a RUNNING MLflow record on setup failure. | The setup is now within the handler, and termination runs in `finally` even if failure-artifact writes fail. The review inspected this correction. Failure metadata retains type and stage; detailed exception messages are omitted, limiting diagnosis but not scientific integrity. |

The original dependency lock was preserved rather than falsely expanded without
resolution/import verification. Canonical Phase 1 receipts remain immutable;
their historical lock/code hashes are not recast as Phase 2 execution metadata.

Runtime checks and measured real-data baseline results are unavailable in this
restricted session. A static review cannot satisfy the Phase 2 exit gate, which
requires actual baseline training and metric reconciliation. No final-test
performance evidence or held-out outcome distribution was accessed by this
review; full-file byte hashing and assignment-structure checks are distinguished
from outcome interpretation.

## Final attribution and checkpoint review

The review inspected `reports/phase2.md`, current progress, decisions
D009–D011, `docs/reproduction-phase2.md`, README, and the staged dependency
bootstrap. These documents distinguish implemented behavior from executed
checks, preserve attribution of reported WSL Phase 1 results, mark model comparisons
and run IDs unavailable, and explicitly leave the Phase 2 exit gate unpassed.
No scientific result or runtime-success overclaim was identified.
The final `reports/phase2_verification.json` was inspected: it records the
recorded 53 passing tests with four explicit skips, successful lint,
compilation, shell syntax and input checks, plus failed dependency installation,
baseline and smoke attempts. These are distinguished from the review's own
five-test run above. The exposure log now includes both the retrospective
pre-hook input-routing disclosure and a timestamped automatic input request;
held-out row-string traversal is not hidden or described as model evaluation.

The final input-access hook logs full CSV row-string traversal before either
CLI input path loads records, while only development values are interpreted.
The separate compact majority-class and aggregate development-diagnostic exports
were inspected; neither leaks customer examples into compact committed reports.
The dependency-failure guard precedes outcome loading and tracking; a new
standard-library-compatible test verifies this boundary. The staged bootstrap
preserves the original lock/archive identity, installs only into `.venv`, and
replaces the current lock only after smoke/lint/tests succeed. Its actual
dependency-resolution and model execution remain blocked, not verified.

Final disposition: **static scientific/code review complete; no unresolved
scientific-integrity implementation finding; runtime acceptance pending and
Phase 2 exit gate not passed**. Install and validate the expanded dependencies,
run all model/tracking tests and the actual 45-fit workflow, then independently
inspect its metrics, convergence, comparisons, and run artifacts before closing
the gate or beginning Phase 3.

## Addendum: MLflow 3.3.2 storage correction, October 8, 2026

This follow-up review covers the requested MLflow layout and exception-cleanup
fix only. The earlier missing-dependency and static-only dispositions above are
historical: the pinned modeling packages are now installed, and synthetic model
and tracking execution is available. Full-data baseline comparisons and the
overall Phase 2 exit gate remain pending. No Phase 3 work, real-data experiment,
source-label read, or model/split mutation was performed by this review.

The review inspected the changed `_local_experiment`, `_mark_failed`, and
`run` functions, the real-client tracking tests, and the fix sections of the
report, progress, reproduction guide and decision D012. Inspection of the
installed `mlflow-skinny==3.3.2` source independently confirmed the collision:
`FileStore._get_active_experiments` lists top-level directories without requiring
experiment metadata, and `_find_run_root` returns the first matching run
directory. A custom top-level `mlruns/artifacts/<run-id>` can therefore shadow
the metadata directory. Installed `_create_experiment_with_id` confirms that
omitting the artifact URI uses the experiment ID under the local artifact root.

| Finding | Affected paths | Consequence and reviewed correction |
| --- | --- | --- |
| High: artifact/metadata collision, corrected | `src/credit_risk/phase2.py:_local_experiment`, `run`; prior custom-layout experiments | Ambiguous discovery can break run retrieval and FINISHED/FAILED updates after artifact logging. New experiments now use the default layout with metadata and artifacts under the same experiment/run directory. The explicit local client URI remains in force. Existing nondefault artifact locations are rejected before creating a parent or child run, with instructions to choose a new experiment name. |
| Medium: cleanup can replace the original failure, corrected | `src/credit_risk/phase2.py:_mark_failed`, child and parent exception handlers | A secondary tracking or failure-artifact error can hide the triggering training error. Each cleanup operation is now best effort; secondary error types are attached as notes, and the original exception is re-raised unchanged. A run can honestly remain RUNNING when metadata cleanup is impossible. |

No unresolved implementation finding remains within this correction. Legacy
metadata, artifacts and statuses are neither rewritten nor deleted. The real
legacy-store test snapshots every existing file, verifies rejection leaves those
bytes unchanged, creates a new experiment name in the same store, then confirms
the original bytes are still intact. Recovery instructions explain that old
ambiguous runs may remain unreadable through discovery; they do not promise a
historical migration or manufacture missing metadata.

The main integration test uses the actual MLflow client and executes the
synthetic 45-fit workflow twice against one store. It retrieves all twenty
distinct parent/child runs, checks FINISHED statuses and default metadata/artifact
paths, lists artifacts, downloads parent manifests and child summaries, verifies
parent links, and confirms a remote environment URI cannot redirect tracking.
The other real-store tests cover ordinary FAILED statuses and exact original
exception identity while run metadata is temporarily unavailable. The latter
also creates a fixture-only failure-file collision so artifact cleanup fails
despite MLflow's artifact-repository cache. Test filesystem changes are confined
to temporary synthetic fixtures; metadata is restored afterward.

Recorded evidence reported for this correction:

- Original focused test reproduced the failure before the fix: **1 failed in
  43.03s**; the first corrected focused run passed: **1 passed in 27.50s**.
- Expanded real tracking module: **4 passed in 38.91s**.
- Repository Ruff: passed. Full fixture suite: **78 passed, 1 skipped in 40.17s**;
  the skip is the unchanged, disabled live PostgreSQL test.
- Three-model synthetic import/fit/save/load/local-MLflow smoke: passed; all seven
  direct modeling pins match the declared versions.
- Workbook, frozen split, feature contract, and original eleven-pin lock hashes
  remain unchanged.

These command results are recorded evidence inspected for this review,
not a claim that the review independently reran the expensive fixture workflow.
The earlier failing cleanup-test iteration is retained in the fix receipt rather
than concealed; the final real-filesystem failure injection is included in the
passing module and suite above.

Disposition: **MLflow correction independently reviewed; no unresolved integrity
finding; synthetic tracking/runtime verification passes. The full-data Phase 2
exit gate remains pending measured development comparisons and their review.**
