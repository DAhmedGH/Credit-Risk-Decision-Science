# Phase 3: bounded tuning and base-model selection

**Status: incomplete; exit gate blocked.** Phase 3 software and independent
fixture review are implemented. Real logistic/forest searches run on the
accepted development partition; XGBoost installation, compatibility smoke,
profiling and its final search cannot run in the original environment. No base
model or calibrated/policy bundle is selected or frozen. Phase 4 has not begun.

## Accepted starting point and boundaries

Phase 2 parent `49c7344ca89440e9a458fa2849d9122d` remains accepted. Its nine
baseline comparisons used 18,000 development rows and five frozen 3,600-row
folds. The combined, unweighted forest led baseline AP at 0.55279 with log loss
0.43000; combined unweighted logistic had AP 0.54076 and log loss 0.43627.
These are prior measured results, not a previously frozen champion.

All Phase 3 data loading reuses those exact folds, source bytes, profile groups,
feature formulas and allowlists. IDs, target and audit-only fields cannot enter
model matrices. Audit exports are not opened. Full CSV strings are traversed
for routing; only development financial/outcome values are interpreted, as
disclosed in [the exposure log](../docs/test-exposure-log.md). No calibration,
policy-validation or final-test outcome analysis occurs.

## Implemented method

`models/search.py` samples settings reproducibly, pairs each across raw/combined
and unweighted/balanced variants, then evaluates the declared finite candidates
through `RandomizedSearchCV` on the frozen indices. AP is the primary ranking
metric; the same positive-class prediction produces ROC-AUC, log loss and Brier.
All preprocessing and categorical vocabularies are fit-local. The XGBoost
wrapper computes negative/positive class ratio from its own fit labels and uses
CPU histogram trees, one thread, bounded tree counts and no early stopping.

Every search candidate preserves OOF predictions without an extra fit, reloads
them, verifies customer/fold/fingerprint coverage and recomputes fold metrics.
Pooled OOF metrics are named separately. Timing distinguishes actual model fit,
prediction, sklearn fit overhead and scoring (which includes metric computation).
Sample fold SD uses `ddof=1`; neither SD nor tuning differences are confidence
intervals or evidence of statistical significance.

The accepted local MLflow implementation remains intact. New searches reuse its
explicit local client, supported FileStore layout, legacy-layout guard and
exception-preserving failure cleanup. Each candidate has an identifiable child
run, resolved settings, partition-named metrics and provenance. Compact parent
artifacts retain full sklearn results, candidate/fold tables and manifests.

## Declared search budget

Plan identity:
`9927448bbd9535fec4922a39d218ee745b77156e73e42ee071c05f9669d9c88a`.
[Complete declaration](../artifacts/phase3_plans/9927448bbd9535fec4922a39d218ee745b77156e73e42ee071c05f9669d9c88a.json)
was persisted before fitting. Seed 42; one search worker and one native thread.
All four feature/weight variants count within each family's ceiling.

| Family | Ceiling | Declared configurations | Completed CV fits | Remaining planned fits |
| --- | ---: | ---: | ---: | ---: |
| Logistic | 12 | 3 settings × 4 variants = 12 | 60 | 0 |
| Forest | 15 | 3 settings × 4 variants = 12 | 60 | 0 |
| XGBoost | 25 | 6 settings × 4 variants = 24 | 0 | 120 |

Resume inspection verified **120 completed, zero interrupted/failed real fits**.
No search remains active, and no duplicate search was launched. The five XGBoost
profile fits and two synthetic compatibility fits have not run. All-development
and OOF reconstruction refits remain zero; search OOF capture adds no fits.

Logistic sampled `C=0.1,100,1`. Forest sampled:

| Setting | Trees | Depth | Minimum leaf | Feature sampling |
| --- | ---: | ---: | ---: | --- |
| 0 | 100 | 10 | 10 | sqrt |
| 1 | 100 | 6 | 5 | sqrt |
| 2 | 200 | 6 | 10 | 0.8 |

Full spaces and XGBoost samples are in the declaration and
`configs/phase3.toml`. Phase 2 timings informed the modest forest ranges.
XGBoost's proposed 100–300 trees/depth 2–4 remain provisional until its separate
five-fit, 30-tree development profile succeeds and runtime is inspected. A
profile/space/code/input/environment identity mismatch prevents its final search.

## Measured partial comparison

Both searches completed 12 configurations × 5 folds. Their AP leaders are
`logistic_00_engineered_none` (`C=0.1`) and
`random_forest_02_engineered_none` (200 trees, depth 6, minimum leaf 10,
feature sampling 0.8). Both use combined predictors and no class weighting.

| Mean development CV measurement | Logistic | Forest |
| --- | ---: | ---: |
| AP ± sample SD | 0.54239 ± 0.02407 | 0.55781 ± 0.02347 |
| ROC-AUC | 0.77195 | 0.78159 |
| Log loss | 0.43540 | 0.42817 |
| Brier score | 0.13601 | 0.13413 |
| Fit seconds per fold | 0.24664 | 21.95813 |
| Prediction seconds per 3,600-row fold | 0.01229 | 0.04303 |
| Pooled OOF AP (separate from fold mean) | 0.54015 | 0.55488 |

Across its six matched comparisons, combined predictors increase AP by
0.00442–0.00701 and reduce log loss by 0.00296–0.00445. Across six weighting
comparisons, AP changes −0.00352 to +0.00027, while log loss increases
0.12547–0.12705 and Brier increases 0.04815–0.04878. Weighting changes the
objective and is not automatically a probability-quality improvement.

Forest's six matched feature contrasts increase AP by 0.00560–0.00880, reduce
log loss by 0.00470–0.01594 and reduce Brier by 0.00138–0.00587. Its six
weighting contrasts change AP by −0.00634 to +0.00010, increase log loss by
0.09143–0.12284 and increase Brier by 0.03513–0.04875. Across both families,
all 12 matched feature comparisons favor combined predictors on these metrics;
all 12 weighting comparisons worsen log loss/Brier. The complete 24 contrasts
are in [phase3_controlled_comparisons.csv](phase3_controlled_comparisons.csv).

The tuned forest improves on the accepted Phase 2 forest descriptively by
about 0.00502 AP and 0.00183 lower log loss. These are development comparisons,
not significance claims or independent generalization estimates. No XGBoost
score is available; this table does not establish a complete base winner.

## Selection rule and preserved-model contract

Decisions D014/D015 specify the candidate universe and resolve the design's
unspecified 'small' log-loss difference **before running searches**. Evaluate
every declared Phase 3 configuration, not only family AP maxima:

1. Keep candidates within 0.01 absolute AP of the best mean development AP.
2. Keep those within 0.001 absolute log loss of the minimum eligible mean loss.
3. Prefer logistic, forest, then XGBoost; fewer/shallower trees; raw features;
   no weighting; exact lower log loss; measured inference time; higher AP; ID.

The tolerances are practical project choices, not significance tests. Fixture
tests demonstrate both that log loss can change the AP-only winner and that
simplicity can change the minimum-loss choice within its declared tolerance.
**No real selection decision or tie-break has executed**, because all three
families with matching scientific provenance are required. Already, the current
forest AP sets a minimum AP eligibility boundary of 0.54781; all 12 logistic
trials fall below it. Adding XGBoost under the unchanged plan cannot lower that
boundary. This explains the rule's effect without freezing a partial winner.
The limited search universe does not automatically include every earlier
Phase 2 configuration; compare its results honestly with the prior incumbent
and do not claim 'best across all evaluated models'.

Once complete evidence exists, the selection workflow preserves the chosen
base, each family's AP leader and a prior dummy, deduplicated to four or five
pipelines. It reconstructs/checks their development OOF evidence, then fits each
on development only, rejecting nonconverged fits. Metadata includes preprocessing,
allowlists, encoded names, class mapping, resolved parameters, seeds,
training-ID/source/split/code/environment hashes and save/load agreement.
Actual model/OOF reconstruction refits so far: **zero**. No selected-base model
binary exists. Selection still does not freeze the full final bundle.

## Runtime, runs and artifact locations

Logistic parent: **`0c41719e0c73482f875a4015477a03c6`**; 60 real CV fits,
zero automatic refits, search.fit runtime **19.95 seconds**. All 12 children
and its parent are FINISHED. Candidate IDs are mapped to child IDs in
[its manifest](phase3_runs/0c41719e0c73482f875a4015477a03c6/manifest.json).

Forest parent: **`e055463d1abd40f3bcdd6a2bd47f82a8`**; 60 real CV fits,
zero automatic refits, search.fit runtime **438.55 seconds**. Its parent and
12 children are FINISHED; child IDs/settings are in
[its manifest](phase3_runs/e055463d1abd40f3bcdd6a2bd47f82a8/manifest.json).

Combined search.fit runtime is **458.50 seconds**; actual fit-time sum is
453.29 seconds. MLflow parent elapsed times, including reconciliation/artifact
logging after search.fit, are 23.185 and 441.579 seconds (464.764 total).
These timings depend on local workload and are not isolated speed benchmarks.

Compact results are preserved in `reports/phase3_runs/<parent-id>/`. The original
shell mounts the project read-only, so actual OOF and local tracking outputs use
**`/tmp/credit-risk-phase3-real-03kpjn82`**. Input/source/config links are read-only;
outputs and a separate FileStore are writable there. OOFs live under
`artifacts/models/phase3/<parent-id>/oof/`, tracking under `mlruns/` in that root.
Copied compact manifests retain their original runtime-relative artifact paths;
they are not evidence that those customer files have been copied into the
project. See the exact preservation/restore commands in the reproduction guide
before `/tmp` cleanup. No durable archive has been created by the original execution environment.

## Checks actually executed

- Final resumed fixture suite: **108 passed, 3 skipped in 46.38 seconds**.
  Earlier implementation checkpoint: 91 passed, 3 skipped in 46.09 seconds.
  Skips: two
  real-XGBoost integrations and live PostgreSQL. No enabled SQL pass is claimed.
- Ruff and bootstrap shell syntax: passed.
- Existing installed dependency consistency: 59 distributions checked, passed;
  this is the Phase 2 closure, not validated XGBoost installation.
- Phase 2 synthetic smoke: three import/fit/save/load checks and actual local
  MLflow status check passed. Phase 3 synthetic smoke/profile stopped before
  fitting because XGBoost is absent.
- Independent scientific/code review inspected implementation and executed
  fixture checks. It identified and verified corrections for final-refit
  convergence enforcement, stale profile provenance and runtime-estimate wording.
- Independent real review verified both runs' hashes, **432,000 OOF rows**,
  all **120 fold metrics**, means/sample SDs and pooled scores, with maximum
  fold metric difference **0.0**. All **26** tracking records are FINISHED;
  warnings empty. Resume checks also verified byte-equivalent compact copies.

Receipts: [verification](phase3_verification.json),
[resume audit](phase3_resume_audit.json),
[independent review](../docs/validation-phase3.md). The original workbook, frozen
split, accepted lock and archived Phase 1 lock hashes remain unchanged.

## Blockers and continuation

PyPI DNS fails in the original shell, so `xgboost-cpu==3.0.5` cannot install.
Project shell writes, Docker access and Git initialization are also blocked.
Editor-mediated implementation/compact-document updates remain available.
The accepted environment and locks are preserved; no replacement lock is
published as validated. Git commit remains explicitly null with content hashes.

Exact setup/search/verification commands, profile inspection, model locations,
partial-runtime preservation and local Git instructions are in
[reproduction-phase3.md](../docs/reproduction-phase3.md). From ordinary WSL,
run bootstrap, profile, declare and all three bounded family searches under the
final environment, then select and verify for a fresh reproduction. **For this
resume, reuse the two verified completed runs and execute only XGBoost's pending
profile/search**, then select and verify. Exact resume commands are separately
identified in the guide. No second logistic/forest search is required merely
to install XGBoost.

The added reuse guard compares frozen inputs/plan/config, numerical source,
Python/platform and every pre-existing distribution version exactly. It permits
only the pinned CPU XGBoost addition with a matching updated full lock, plus
reviewed runner/CLI changes. Original source snapshots protect input routing,
selection/reference logic, frame/X/y assignments and numerical final-fit
statements. Original manifests remain immutable; a new reuse proof enumerates
old/current identities and zero additional search fits. Each future bundle
distinguishes its original search provenance from its refit environment.
The current orchestration-only reuse audit is in
[phase3_reuse_audit.json](phase3_reuse_audit.json); actual additive-XGBoost
validation remains pending installation. This supersedes the earlier blanket
same-lock rerun instruction without changing the selection rule or search plan.

**Phase 3 exit gate does not pass.** Required missing evidence is real XGBoost
compatibility/profile/search, complete base selection, development-only model
and reference refits/save-load verification, and independent review of those
artifacts. Phase 4 checkpoint is conditional: after completing that gate, load the
fixed development-fitted base/references, fit mappings only on calibration rows,
then select calibration/policies on policy validation. No Phase 4 work ran.
