# Technical decisions

This presentation summary records the scientific and implementation choices.
Original dated execution records and historical receipt bytes remain preserved
privately. Measurements below describe the recorded study, not new computations.

## Data, prediction time and features — D001–D006

Use the supplied UCI dataset 350 workbook unchanged. Its SHA-256 is
`30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`.
The original official ZIP, download chain and retrieval time are unknown;
file timestamps do not establish them. The canonical reader is xlrd, sheet
`Data`, aliases in Excel row 1, headers in row 2, records from row 3.
Dataset attribution and CC BY 4.0 terms remain in the source manifest.
The subsequent official-source byte comparison is recorded separately in D029;
it does not reconstruct these original acquisition records.

Predict released next-month default for existing accounts at the retrospective
month-end snapshot. September history availability is an explicit assumption.
Six monthly history fields are one customer snapshot, not six labeled observations.
Keep demographic fields outside the primary predictor allowlist, without claiming
that exclusion establishes fairness.

Phase 1 performed import/data serialization checks without predictive fitting.
Labels were used for source integrity and group stratification; held-out outcome
summaries were withheld. Initial network, Docker-socket and Git-write failures
left corresponding execution checks pending. Standard-library diagnostics were
qualified as diagnostic evidence until canonical-reader and SQL agreement existed.

Preserve negative balances and special repayment codes. Undefined denominators
produce missing proxies and explicit flags. Financial ratios are proxies, not
contractual repayment fractions or debt-to-income. Numeric-storage/arithmetic
findings led to exact SQL numeric storage, finite-arithmetic quarantine,
persisted-value checks and versioned feature/schema provenance. No arbitrary
amount cutoff, whole-population imputation or learned vocabulary was introduced.

Freeze seed-42 60/15/10/15 group-disjoint partitions and five development folds
using fingerprints of the 19 raw financial predictors without labels. Identical
profiles stay together; different customers are retained. The assignment SHA is
`775f9862fb5b97095c81fdae440d4acb7fd52f692a216b6284e879db5e4d5e4c`.

## Environment, SQL and tracking — D007–D013

Ruff's initial 3,337 diagnostics came from installed code: 2,697 in `.tools/`
and 640 in `.cache/`. Explicit generated-path exclusions preserve maintained-code
coverage and selected rules; no blanket unsafe fixes were applied.

Reported Phase 1 WSL verification reconciled 30,000 source/curated/audit/exported
rows, zero rejections and two already-ingested no-ops; four enabled SQL tests
passed in 2.37 seconds. This establishes stability of reingestion, without
claiming a fresh-empty-database load in that execution. Exact timestamps and a
complete console log were not supplied. Separate recorded import/hash checks
and the 47-pass fixture run with one SQL skip remain distinct evidence.

Model preprocessing uses fold-fitted pipelines: median imputation, logistic
scaling, categorical mode imputation and unknown-safe one-hot encoding. The nine
baseline variants share frozen folds: prior dummy and logistic/forest crossed
with raw/combined predictors and unweighted/fold-local balanced fits. All 45
fits completed. No held-out rows fitted transforms or selected baseline choices.

MLflow 3.3.2's supported artifact layout resolved a repeated-store failure.
Legacy stores were preserved; guards reject incompatible layouts. Fold-null
representation and NaN parameter serialization were corrected. Failed checks
and their resolution remain in private execution evidence and the phase report.
Phase 2 acceptance reloaded all 45 saved pipelines without refitting; predictions
and metrics agreed within 1.11e-16. The original 11-pin lock remains archived.

## Bounded model comparison and selection — D014–D017

AP scoring and frozen five-fold assignments govern the searches. Completed
budgets were logistic 12 configurations/60 fits, forest 12/60, and XGBoost 24/120.
Search fitting took 533.733963917 seconds. Additional development computation
was five profile fits, 25 preserved-candidate OOF refits and five final-development
refits: 275 real development fits total. Synthetic smoke fits are separate.

Selection uses maximum mean development AP, a 0.01 practical AP tolerance,
then log loss with the declared 0.001 small-loss tolerance and simplicity. These
tolerances are not significance tests. Seventeen candidates met the AP floor;
two XGBoost candidates met the small-loss ceiling. The 100-tree model
`xgboost_05_engineered_none` was retained over the 200-tree candidate.

All 24 matched engineered-feature contrasts improved AP/log loss/Brier;
weighting worsened log loss/Brier in all 24 contrasts. No XGBoost-win requirement
was imposed. Five-fold 864,000 search OOF rows and all 35 saved fold/development
pipelines were verified; original-to-final reuse retained numerical/source identities.
The durable Phase 3 inventory contains 2,682 files, 131,298,257 bytes.

## Calibration, policy and explanations — D018–D022

The base model fits development only. Sigmoid/isotonic mappings fit the separate
4,500-row calibration partition; 3,000 policy-validation rows select the mapping
and cutoffs. Raw probabilities win the 0.005 log-loss/simplicity rule:
0.4329887140 versus sigmoid 0.4362283190 and isotonic 0.4559940960.
No full-data base refit inherits the old calibration evidence.

Hypothetical utility is `(1-p)*gain - p*loss - processing_cost` for acceptance,
zero for abstention. Base gain 50/loss 500/cost 0 gives analytic threshold
50/550; empirical cutoff 0.085 is selected only on policy validation. Freeze all
11 scenarios/eight policies, scalar cutoffs and ties before final evaluation.
Retain abstain-all winners and N/A accepted default rates for empty acceptance.

SHAP explains the selected raw tree's default log odds, with 100 fixed development
background rows, 996 development explanation rows and four preselected validation
cases. Maximum additivity residual is 1.43148e-06. Demographic slices are
support-limited descriptive checks. Neither SHAP nor slices establish causality
or fairness. Operational path corrections and failed scratch assertions did not
change fitted objects, scenarios, source inputs or accepted result bytes.

The complete freeze binds 106 artifacts, including original review evidence.
Content SHA: `89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b`.
Bundle SHA: `45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd`.

## Final evaluation and delivery — D023–D025

The frozen evaluation `faa4d59ec05c408aacd3bd6560678c76` ran once on 4,500
accounts in 4,378 profile groups. Saved evidence supports six model rows,
88 policy/scenario rows, 396,000 decisions and 341 interval statistics.
Use 1,000 seed-42 paired fingerprint-group bootstrap draws with 95% percentile
intervals conditional on the fitted models/policies. No test-driven reselection
or new exploratory final-test comparisons were performed.

The local 207-pass SQL suite, 206-pass container suite with one SQL skip,
114.778-second zero-fit fresh-core reproduction and 174-file archive restoration
are separate execution records. Earlier fixture serialization failures, two Docker
Hub 504 responses, an offline missing-contourpy resolution failure and an omitted
container input file were corrected before delivery checks passed.

Interrupted delivery retained successful restoration receipts rather than repeating
scientific execution. Scalar MLflow logging was stopped and resumed with batched
writes in the same run `61449a81592f446281de1f939fc8badd`; FINISHED status and
541 aggregate metric values were verified. No second run or model/policy change
resulted. Remote CI remains unobserved.

## Software corrections and subsequent checks — D026–D027

The completed-project checks resolved eight findings: strict CSV widths/quoting/NUL
and cross-format identity checks; canonical missing-value routing; preservation of
monitoring outputs; optimized-Python reproduction refusal; required CLI paths;
root-relative readiness; historical-document context; and exact-source restoration.
Twenty-four focused regressions supplement the original tests. The live-SQL suite
recorded 231 passes, zero skips, 82.04 seconds. Separately reported rebuilt-container
verification recorded 230 passes, one expected SQL skip, 48.75 seconds, without a
supplied raw terminal log. These checks changed no accepted scientific result.

Source-bound historical preflight/report guards still reject maintained fixes.
Current scoring uses the unchanged frozen financial transforms; exact historical
replay uses preserved private source. Original evidence is never resealed to match
presentation edits. See [software findings and checks](../reports/project-audit.md).

## Design and delivered-documentation reconciliation — D028

The documentation comparison preserves original design/plan files, scientific
artifacts and historical receipts. It clarifies delivered behavior without changing
models, cutoffs or acceptance evidence.

| Difference | Classification | Documentation consequence |
| --- | --- | --- |
| Original ZIP, retrieval time and acquisition checksums unavailable | Recorded D002 deviation; subsequent official byte comparison recorded in D029 | Preserve unknown original acquisition records; distinguish the later verification |
| 12/12/24 searches under 12/15/25 ceilings; 0.001 log-loss tie and 48-candidate scope | Consistent budgets and recorded D014/D015 refinement | Explain paired variants and full tie order in modeling |
| YAML sketch/unified commands and notebook tree differ from delivered modules/TOML | Delivered interface variation; proposed notebook layout not implemented | Document actual entry points and data-only `reproduce` boundary |
| Monitoring thresholds have no configuration argument | Planned configuration interface not implemented | Identify fixed module constants and heuristic scope |
| Nominal exposure is not a scorer field | Delivered representation of planned synthetic payoffs | State that scenario G/L/C fully determine utility |
| Canonical source and scoring validators differ for limits, categories, payment signs and text | Omitted contract explanation | Keep both delivered contracts explicit without changing either validator |
| Initial manifests retain pending reader/hash annotations and null Git commits | Preserved historical evidence | Link later canonical validation; do not overwrite early receipts or infer retroactive commits |
| Blanket design-completion language and restoration interpreter ambiguity | Documentation errors | Qualify completion, distinguish public/private workflows and use the pinned interpreter |

Reliability bins, payoff guards, SHAP/case selection and descriptive slice definitions
were added to their topic guides from existing implementation/evidence. No new
scientific execution is represented by these explanations. The source-download
chain remains unresolved; private artifact access and remote CI remain explicit
reproduction/verification limitations.

## Subsequent official-source comparison — D029

The supplied workbook was verified byte-for-byte against the official UCI 350
archive retrieved at `2026-10-10T18:00:23.006402Z`. The current official page's
download link was confirmed over certificate-verified HTTPS. The archive was
downloaded into an isolated temporary directory, and its unique expected workbook
member was read directly without extraction or cell decoding. The recorded
accepted, independently measured local and official-member SHA-256 hashes all
match; full workbook byte equality was also checked.

The [new verification receipt](../reports/provenance/uci350-official-comparison-20261010T180023Z.json)
records requested/final URLs, actual UTC retrieval time, archive/member lengths
and hashes, available HTTP metadata and the three-way comparison. The original
acquisition date, download chain and original archive checksum remain unknown;
this verification does not reconstruct them. Historical source manifests,
acceptance receipts and execution records remain unchanged. Changes are limited
to this new receipt and maintained public provenance documentation. No artifact
packaging or scientific workflow ran.

## Public frozen-scoring delivery — D030

The maintained scoring route now uses a separate `public-scoring-v1` package.
The accepted selected pipeline and feature-schema bytes are copied unchanged;
the raw mapping requires no fitted calibrator. Policies are an exact projection
of all 88 frozen definitions across 11 scenarios. Historical review attachments,
reference estimators and evaluation records remain outside this inference-only
package. The original freeze, probability bundle and acceptance receipts retain
their identities and bytes.

The new distribution manifest records its own content identity, actual member
hashes, accepted lineage, runtime versions and financial transformation hashes.
The public loader verifies that contract before deserializing trusted artifacts.
Restoration checks the archive digest, bounds decompression, rejects unsafe
members and refuses an existing installation. Historical loading retains its
original complete-freeze verification contract.

At 29,213 bytes the archive is suitable for ordinary Git distribution; no release
asset is needed. It remains locally prepared; publication is pending. The saved example
retains its original `model_version` and byte-identical scientific outputs;
new receipts separately identify the distributed pipeline and delivery manifest.
The [delivery evidence](../reports/public-scoring-delivery.json) and
[focused review](../reports/public-scoring-review.md) record offline verification,
regression checks and preserved limitations. No training, refitting, calibration,
selection or accepted final-test evaluation ran.

## Public CI fixture boundary — D031

A reported Actions run failed because `scripts/phase4_smoke.py` called
`accepted_integrity` before its synthetic fit. That historical guard requires
excluded original receipts, inputs, source attachments and accepted artifacts.
The fixture smoke now omits that unrelated call while retaining version checks,
disjoint synthetic calibration, raw-margin TreeSHAP additivity, plotting and exact
save/load probability agreement. Historical integrity functions, Phase 4 commands
and the bootstrap's explicit integrity step remain unchanged and fail for missing
evidence. Regression tests exercise both boundaries without private inputs.

The exact public CI sequence also exposed `tests.fixtures.records` under bare
`pytest`, because `tests` is not a package. The monitoring fixture now imports
`fixtures.records` consistently with other tests. Workflow commands, dependency
locks, financial transformations and scoring-package bytes remain unchanged.

[Local repair evidence](../reports/public-ci-smoke-fix.json) records all three
CI smokes, Ruff, 270 passes/one expected SQL skip and the separate four-test SQL
check in a rebuilt isolated container containing tracked public files only.
The reported remote failure and pending remote confirmation are distinct from
these locally executed checks. No accepted-model fitting, real-data calibration,
search or final-test evaluation ran; earlier scientific receipts are preserved.

## Public availability and observed remote CI — D032

The public repository and scoring package are now hosted on
[GitHub](https://github.com/DAhmedGH/Credit-Risk-Decision-Science). A separate
documentation status check observed GitHub's public API on
`2026-10-11T05:08:56Z`: the pushed CI repair
`412dd680c842061663fdfc5223ccd28fd5433221` has a completed, successful
[fixture run](https://github.com/DAhmedGH/Credit-Risk-Decision-Science/actions/runs/38112715548).
The subsequent README-only revision
`b037c814dc5d70057d20c612b42815f91179fdf5`, then remote `main`, also has a
[successful run](https://github.com/DAhmedGH/Credit-Risk-Decision-Science/actions/runs/38113711472).
The repair's smoke, Ruff, pytest and separate SQL steps were observed as successful.

The published archive, checksum and manifest sidecars were retrieved over
certificate-verified HTTPS at that README revision and match the preserved local
files byte-for-byte. Archive SHA-256 remains
`d2fb60ca57f3b8b39fc271b62a2f0386db35842a8389d3444a4e6d6af6ce1349`.
See [observed status](ci_cd.md#observed-github-status). Maintained frozen scoring
uses this public package without the private payload; historical replay still
requires additional original inputs and source/evidence attachments.

These current-status observations supersede the earlier pending availability and
remote-confirmation wording for the maintained route. D028–D031 and historical
receipts retain their original checkpoint descriptions. No installation, scoring,
tests, training or scientific evaluation were rerun during this documentation
check; no historical evidence or artifact hashes were changed.
