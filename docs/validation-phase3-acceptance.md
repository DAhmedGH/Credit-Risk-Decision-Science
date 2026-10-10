# Independent Phase 3 acceptance review

This technical summary preserves recorded findings and checks. Original review
documents and hash-bound receipts are retained privately. These checks were
performed at the dated checkpoint, not repeated for presentation cleanup.

Reviewed October 8, 2026 against the saved completed experiments, the design,
phase plan, accepted Phase 2 checkpoint and original Phase 3 review. This review
owns documentation only. It performed **zero fits, tests or searches**, changed
no experiment/source/model/split/tracking artifact and interpreted no held-out
outcomes. The earlier [blocked review](validation-phase3.md) remains an accurate
historical checkpoint; this review assesses the subsequently completed evidence.

**Disposition: PASS for Phase 3.** The fixed development-fitted base is
`xgboost_05_engineered_none`, selection run
`6a0725d18b164582938e0b07b2df6b27`. No unresolved scientific-integrity or model
delivery blocker remains. This accepts base selection and its saved references;
the complete calibrated/policy bundle is **not frozen**, and Phase 4 has not run.

## Evidence inspected

| Purpose | MLflow run |
| --- | --- |
| Logistic search | `0c41719e0c73482f875a4015477a03c6` |
| Forest search | `e055463d1abd40f3bcdd6a2bd47f82a8` |
| XGBoost development profile | `80034d2113a04f6ab978837a292e294c` |
| XGBoost search | `6c2fee1f9e5e4bfeab64e9bcda9ffed6` |
| Base selection and reference preservation | `6a0725d18b164582938e0b07b2df6b27` |

Inspection used `/tmp/credit-risk-phase3-real-03kpjn82`, both user-created
`/home/danieal/credit-risk-backups/phase3-20261008-*` backups, compact project
copies, materialized source snapshots, installed packages and trusted saved
pipelines. The accepted durable root is the newer
`/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime`; the earlier
`194353` backup lacks selection and is retained as history.

Only saved development outcomes, label-free frozen assignments and financial
values for development IDs were interpreted. The full label export and original
workbook were byte-hashed without decoding. Financial CSV strings were routed
by ID before converting development values; the audit export was not opened.
This audit adds no final-test outcome exposure. The existing loader routing
disclosures and actual execution accesses remain in the exposure log.

## Independent numerical and selection audit

All **48 configurations / 240 fold results / 864,000 search OOF rows** reconcile
with the five existing frozen folds. Every candidate has exactly one OOF
prediction for each of the 18,000 development customers, with matching labels,
folds and fingerprints; identical financial-profile fingerprints do not cross
folds. Recomputed AP, ROC-AUC, log loss and Brier, their fold means/sample SDs and
pooled OOF metrics agree within 1e-12. Fold means were kept distinct from pooled
scores. Search and selected/reference reconstructed OOF metrics agree within
the same tolerance. Saved timings identify search fitting, prediction and
later reconstruction separately.

In a separate read-only calculation, financial fingerprints were recomputed
from the 19 raw financial fields for all **18,000 development customers** and
matched every frozen assignment. Their **17,508 distinct groups** remain within
individual folds, each of size 3,600. This calculation invoked the versioned
fingerprint function on development values, independently of the saved OOF
coverage check; it did not open a label file or convert held-out values. Frozen
input bytes and the unchanged loader's fingerprint guard were also checked.

A separate calculation from all saved candidate rows, without calling the
production selector, reproduces the full decision:

1. `xgboost_04_engineered_none` has maximum mean AP
   **0.5615037770790678**. The absolute 0.01 AP boundary is
   **0.5515037770790678**, leaving 17 candidates.
2. Minimum eligible log loss is **0.4265207738885099**. The predeclared 0.001
   small-loss tolerance gives **0.4275207738885099**. Only XGBoost settings
   `04_engineered_none` and `05_engineered_none` remain.
3. Both have depth 3. Setting 05 has **100 rather than 200 trees**, so the
   prespecified simplicity ordering selects it. Its exact log loss is also
   marginally lower; the measured prediction-time advantage corroborates the
   choice but is unnecessary to resolve it.

The selected mean AP is **0.5612527444711741**, only 0.0002510326078937 below
the maximum. Its mean ROC-AUC/log loss/Brier are
**0.7834954430721319 / 0.4265207738885099 / 0.13371946671245333**;
pooled OOF AP is separately **0.5589734398765549**. No logistic configuration
reaches the AP boundary. The minimum-loss AP-eligible forest is
`random_forest_00_engineered_none`, log loss **0.4276785804369312**, which
exceeds the small-loss ceiling by 0.0001578065484213. Thus no forest enters the
final simplicity set; considering only its family AP leader would be insufficient
to establish this.

The 0.01 AP and 0.001 log-loss tolerances are declared practical choices, not
significance tests. The unchanged candidate universe contains the 48 declared
Phase 3 configurations. The unsampled Phase 2 incumbent is honestly reported
as prior evidence rather than silently added to selection. The result is a
development-tuned choice within this bounded universe, not a claim of optimality
over all possible or previously evaluated configurations.

The matched plan supports raw/combined and weighting comparisons without
multiplying family budgets. All 24 combined-feature contrasts improve AP,
log loss and Brier; all 24 weighting contrasts worsen log loss and Brier, with
mixed AP effects. These conclusions use development evidence only.

## Fitted-state, serialization and leakage inspection

The review reloaded and re-scored **35 saved pipelines**: 25 selected/reference
fold pipelines, five all-development pipelines and five XGBoost profile models.
For each applicable model, inspection verified numerical median imputations,
categorical modes/vocabularies, logistic scaling, class counts, predictor names
and exclusions against the corresponding fit rows. Fold fit/validation ID
hashes match the frozen assignments. Numeric fit-statistic comparisons allow
ordinary floating-point summation rounding; the learned scope is the correct
14,400 fit rows or 18,000 development rows.

IDs, target and audit-only sex/age/education/marital-status fields are outside
the financial predictor allowlist. Encoded names and schemas match the saved
evidence; positive-class mapping is explicitly class 1. Logistic convergence,
forest tree counts and actual estimator parameters, and XGBoost tree counts,
CPU histogram algorithm, seed, one-thread execution and absence of early
stopping were checked. Saved unweighted XGBoost models retain weight 1 and
fit-local class counts. Code inspection verifies that balanced XGBoost computes
its ratio inside `fit` from that fit's labels, and logistic/forest weighting is
delegated to their fold-fitted estimators. Weighted search models were not all
serialized; their weighting guarantee additionally rests on the inspected
unchanged numerical implementation and earlier meaningful fixture tests.

Reloaded fold predictions match saved OOF values within **1e-12**. The separately
recorded maximum for XGBoost/profile reconciliation is
**9.71445146547012e-17**; an exact combined maximum across the other families
was not retained and is not claimed. Their reconciliations also passed the
1e-12 bound. Five development bundles pass repeated-load and batch-versus-single
prediction agreement. The accepted XGBoost binary was independently loaded
directly from the durable backup and scored consistently with the runtime copy.

Serialization checks used trusted local artifacts and the existing compatible
environment. They do not establish behavior under a fresh environment, other
library versions, unrelated inputs or future edited custom pipeline source.

Preserved bundles are selected `xgboost_05_engineered_none`, reference
`xgboost_04_engineered_none`, `random_forest_02_engineered_none`,
`logistic_00_engineered_none` and `dummy_prior`. All metadata states development
training only, 18,000 rows and training-ID SHA
`45dd0dc4b8b2222458101a1e0aea0167aa5392d36bad3ce84e5732668ae7763e`.
Resolved parameters, seeds, feature schema, hashes and reference roles agree
with the loaded estimators. `champion_frozen=false` and
`complete_bundle_frozen=false` correctly preserve the later-phase boundary.

## Budget, provenance and durable delivery

The unchanged plan SHA is
`9927448bbd9535fec4922a39d218ee745b77156e73e42ee071c05f9669d9c88a`.
Logistic **12/60**, forest **12/60** and XGBoost **24/120** configurations/fits
are within the 12/15/25 ceilings. `RandomizedSearchCV` uses the explicit frozen
indices, AP scoring, one worker and `refit=False`; OOF capture adds no fits.
The five 30-tree profile fits precede the XGBoost search. Its runtime estimate
is explicitly a planning estimate, not an upper bound.

Actual real-data accounting is **240 search fits + five profile fits + 25 OOF
reconstruction fits + five development fits = 275**. The preserved manifests
and **53 FINISHED MLflow records** support this accounting; no duplicate search
or failed/interrupted scientific fit appears. Search.fit times independently
match 19.948072020 / 438.547289794 / 75.238602103 seconds, total
533.733963917 seconds. Synthetic compatibility and fixture training remain
separate. Acceptance itself contributes no fits.

All three reuse proofs were independently recomputed and exactly match those
saved by selection. All **60 installed distributions** match the final context.
The completed logistic/forest contexts retain every original dependency version
and numerical/feature/loader/preprocessing/search source identity; only the
pinned `xgboost-cpu==3.0.5` addition, validated lock and reviewed runner/CLI
changes differ. XGBoost search reuse is identical-context. Original snapshots,
protected AST comparisons, exact plan/input/config/Python/platform identities
and lock consistency constrain this exception. This is verified compatible
reuse with preserved old contexts, not a retroactive claim that earlier searches
used the new environment.

The review independently verified every final preservation-inventory entry:
**2,682 regular files / 131,298,257 bytes**, each with identical runtime, durable
backup and inventory hashes/sizes. Inventory SHA is
`73bce5a8573b00af27d0fab873def39f95f6c60c2f53e2655ae7a52e57aee5ae`.
An additional 170 cross-backup artifact comparisons passed. Model, OOF and
tracking outputs are actual regular files. All **36 accepted source identities**
reconstruct exactly from materialized original snapshots plus the three accepted
runner/CLI/lock overrides. Accepted code tree is
`bcad5c99614b24044c72f904ce1a73c2552d82528b50d90679478cec3f50a44f`,
accepted lock SHA
`31e7241f3499567f92579f1381892351dcd433faf219fe8b0be70321937e6b57`.

Source/input/config symlinks in the backup still refer to the project; they are
not independent archived bytes. Original immutable inputs remain hash-bound,
and preserved source snapshots support exact reconstruction. All 53 copied
MLflow artifact URIs retain the original absolute `/tmp` runtime path. Direct
verified durable model loading works independently of these URIs; historical
MLflow artifact APIs require restoration at the original path if absent.
Documentation must enforce non-overwriting restoration and retain both backups.
These disclosed constraints do not prevent loading the exact accepted base.

## Findings, verification attribution and boundary

Earlier code-integrity findings and their corrections remain in
[the implementation review](validation-phase3.md). No new unresolved scientific
finding was identified in completed evidence. Two low-severity documentation
corrections were requested and independently verified as resolved during acceptance:

| Severity / affected path | Consequence | Verified correction |
| --- | --- | --- |
| Low — report/progress/decision/acceptance receipt prediction maximum | A subset's recorded numerical maximum could be mistaken for a measured maximum across every family. | Resolved: global reconciliation is reported within 1e-12; the 9.71445e-17 observed maximum is attributed to XGBoost/profile only. |
| Low — `docs/reproduction-phase3.md` restoration/reconstruction commands | A standalone failed `test` does not prevent an interactive shell from executing the following copy. | Resolved: Python `shutil.copytree` rejects existing destinations, with source overrides executed only after successful exclusive creation. |

The reported WSL bootstrap/compatibility checks and final enabled PostgreSQL suite
are external execution evidence inspected during acceptance, not separately repeated
tests. The reported final suite is **111 passed in 49.88s, no skips**; exact
invocation timestamps were not supplied. Earlier Ruff, fixture and focused
reuse-test executions retain their original attribution. No fresh-environment
rebuild, remote CI or Git commit is claimed. `git status` still reports an
uninitialized repository in this original workspace; null commit and actual
content hashes remain explicit.

Final report, exposure/progress/decision logs, acceptance/preservation receipts
and Phase 4 checkpoint were inspected for consistency with the evidence above.
Subject to the documented delivery constraints, Phase 3's selected-base,
bounded-search, development-only fit and reproducible-artifact exit requirements
pass. The next separately scoped phase must keep this base and these reference
identities fixed. Calibration, policy-validation selection, SHAP and final-test
evaluation have not been performed by this acceptance and are outside this checkpoint
by its PASS disposition.
