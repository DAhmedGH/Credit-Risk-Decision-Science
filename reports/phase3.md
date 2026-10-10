# Phase 3: bounded tuning and accepted base model

This report records the historical Phase 3 checkpoint. Phase status, Git
state and check counts below describe that execution, not the current publication
checkout. Use [modeling](../docs/modeling.md),
[setup](../docs/setup.md) and [final evaluation](results.md) for the completed
project's methods, execution boundaries and results.

**Exit gate: PASS.** The selected development-fitted base is
`xgboost_05_engineered_none`, selection run
`6a0725d18b164582938e0b07b2df6b27`. All Phase 3 scientific and artifact-delivery
requirements pass. `base_selected=true`; `champion_frozen=false` and
`complete_bundle_frozen=false`. No calibration, policy, SHAP or Phase 4 work
has run. The complete final bundle remains unfrozen.

## Scope and evidence attribution

Accepted Phase 2 parent `49c7344ca89440e9a458fa2849d9122d` remains unchanged.
All experiments use the same 18,000 development customers and five frozen
3,600-row validation folds, with identical financial profiles grouped together.
IDs, target, sex, age, education and marital status are excluded from predictors.
The contract remains `financial-row-v1.1`: 19 raw / 32 combined financial inputs.

Reported WSL execution completed dependency bootstrap, XGBoost profile/search,
selection and the final enabled PostgreSQL suite. This acceptance
independently audited their saved outputs; it repeated **zero fits and zero
tests**. The earlier logistic/forest searches were reused without duplication.
Exact test invocation times were not supplied. The prior blocked checkpoint
is retained in [phase3_pre_acceptance.md](phase3_pre_acceptance.md), the resume
receipt and decisions D014–D016; those blockers are resolved for this milestone.

Source workbook, full label export and split files were byte-hashed. Acceptance
interpreted only saved development outcomes, label-free assignments and financial
values for development IDs. No audit export or held-out outcome was opened for
interpretation. Original CSV-string routing is disclosed in
[the exposure log](../docs/test-exposure-log.md).

## Measured comparison

These are means across five development folds; AP SDs use `ddof=1`. Full means,
SDs, pooled scores, resolved settings and per-fold results remain in each search
run. They are tuning measurements, not independent test performance.

| Candidate / role | Mean AP ± SD | ROC-AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: |
| Logistic `00_engineered_none`, family AP leader | 0.54239 ± 0.02407 | 0.77195 | 0.43540 | 0.13601 |
| Forest `02_engineered_none`, family AP leader | 0.55781 ± 0.02347 | 0.78159 | 0.42817 | 0.13413 |
| XGBoost `04_engineered_none`, family/global AP leader | 0.56150 ± 0.02153 | 0.78405 | 0.42652 | 0.13376 |
| XGBoost `05_engineered_none`, selected base | 0.56125 ± 0.02210 | 0.78350 | 0.42652 | 0.13372 |

Pooled OOF AP is separately 0.54015 / 0.55488 / 0.55855 / 0.55897 in the
same order. Mean search-fold prediction times per 3,600 rows are 0.01229 /
0.04303 / 0.02601 / 0.02015 seconds. These depend on local workload and are not
isolated inference benchmarks. Mean fit times are 0.24664 / 21.95813 / 0.64871 /
0.37411 seconds per fold; later reconstruction timings are recorded separately.

The selected pipeline uses combined predictors, no weighting, 100 trees,
depth 3, learning rate 0.07, minimum child weight 5, row/column sampling 1.0,
L1 0.1 and L2 5.0. Seed 42, CPU histogram trees and one native thread are fixed;
no early stopping or external evaluation set was used. The AP-leading XGBoost
uses 200 trees, depth 3, learning rate 0.03, minimum child weight 1, row sampling
0.8, column sampling 1.0, L1 0 and L2 1. Logistic uses C=0.1; the forest leader
uses 200 trees, depth 6, minimum leaf 10 and max_features=0.8.

## Reproduced selection decision

The unchanged content-addressed declaration is
`9927448bbd9535fec4922a39d218ee745b77156e73e42ee071c05f9669d9c88a`.
D014 declared the 0.001 log-loss simplicity tolerance before any search.
D015 restricts selection to all 48 declared Phase 3 configurations, rather
than only family AP leaders or every earlier Phase 2 configuration.

Highest mean AP is **0.5615037770790678** for `xgboost_04_engineered_none`.
The 0.01 AP practical-tie boundary is **0.5515037770790678**, leaving these
17 candidates:

| AP-eligible candidate | Mean AP | Mean log loss |
| --- | ---: | ---: |
| `xgboost_04_engineered_none` | 0.56150378 | 0.42652373 |
| `xgboost_05_engineered_none` | 0.56125274 | 0.42652077 |
| `xgboost_05_engineered_balanced` | 0.55996875 | 0.54540922 |
| `xgboost_04_engineered_balanced` | 0.55940490 | 0.54522068 |
| `random_forest_02_engineered_none` | 0.55780845 | 0.42817119 |
| `random_forest_02_engineered_balanced` | 0.55703592 | 0.53547227 |
| `xgboost_00_engineered_balanced` | 0.55676307 | 0.52711661 |
| `xgboost_01_engineered_balanced` | 0.55660693 | 0.53609387 |
| `random_forest_00_engineered_none` | 0.55656945 | 0.42767858 |
| `xgboost_02_engineered_none` | 0.55640670 | 0.42799742 |
| `xgboost_03_engineered_none` | 0.55516598 | 0.42786770 |
| `random_forest_00_engineered_balanced` | 0.55489907 | 0.51910434 |
| `xgboost_00_engineered_none` | 0.55463988 | 0.43003563 |
| `xgboost_01_engineered_none` | 0.55326087 | 0.42948140 |
| `xgboost_02_engineered_balanced` | 0.55322960 | 0.54426895 |
| `xgboost_04_raw_none` | 0.55220238 | 0.43079710 |
| `xgboost_05_raw_none` | 0.55181725 | 0.43047688 |

Minimum eligible log loss is **0.4265207738885099**. The declared 0.001 tolerance
sets a ceiling of **0.4275207738885099**. Only two candidates remain:

| Candidate | Log loss | Trees | Depth |
| --- | ---: | ---: | ---: |
| `xgboost_04_engineered_none` | 0.4265237316157985 | 200 | 3 |
| `xgboost_05_engineered_none` | 0.4265207738885099 | 100 | 3 |

The prespecified simplicity order compares family, tree count, depth, raw versus
combined, weighting, exact log loss, measured inference time, AP and stable ID.
Both finalists are XGBoost; **100 versus 200 trees resolves the choice** in favor
of `xgboost_05_engineered_none`. It also has marginally lower log loss and lower
measured inference time, although neither is needed after the tree-count tie-break.
Its AP trails the maximum by only **0.0002510326078937**.

No logistic configuration reaches AP eligibility. The lowest-loss eligible
forest is `random_forest_00_engineered_none`, log loss **0.4276785804369312**,
which exceeds the small-loss ceiling by 0.0001578065484213. Thus no forest enters
the final simplicity set. These tolerances are project choices, **not significance
tests**. Independent recomputation from saved results exactly reproduces the
eligible sets and selected candidate; no rule was changed after results.
[All 48 decisions](phase3_selection_candidates.csv) and
[original selection](phase3_runs/6a0725d18b164582938e0b07b2df6b27/selection.json)
retain the complete evidence.

## Feature and weighting findings

The matched plan pairs each sampled setting across raw/combined ×
unweighted/fold-local balanced variants, all counted within each family budget.

| Family | Combined-minus-raw AP range | Balanced-minus-unweighted AP range | Weighting log-loss increase |
| --- | ---: | ---: | ---: |
| Logistic (6 contrasts each) | +0.00442 to +0.00701 | −0.00352 to +0.00027 | +0.12547 to +0.12705 |
| Forest (6 contrasts each) | +0.00560 to +0.00880 | −0.00634 to +0.00010 | +0.09143 to +0.12284 |
| XGBoost (12 contrasts each) | +0.00475 to +0.01092 | −0.00570 to +0.00335 | +0.09708 to +0.12330 |

All **24** combined-feature contrasts improve AP, log loss and Brier. Weighting
improves AP in only four of 24 contrasts and worsens log loss and Brier in all
24. For XGBoost, weighted-fit ratios come only from the corresponding fit labels;
this changes the training objective and does not guarantee better probabilities.
[All 48 contrasts](phase3_controlled_comparisons_accepted.csv) retain exact values.
These are descriptive development findings. The selected model exceeds the
Phase 2 forest incumbent's AP 0.55279, but no statistical-significance or
held-out-generalization claim follows from tuning results.

## Compute accounting and identifiable runs

| Purpose | Configurations | Actual fits | Runtime / accounting |
| --- | ---: | ---: | --- |
| Logistic search | 12 of ceiling 12 | 60 | 19.948072020 s search.fit |
| Forest search | 12 of ceiling 15 | 60 | 438.547289794 s search.fit |
| XGBoost search | 24 of ceiling 25 | 120 | 75.238602103 s search.fit |
| XGBoost 30-tree development profile | separate | 5 | 2.397282702 s evaluation; mean fit 0.249354031 s |
| Selected/reference OOF reconstruction | separate, five bundles × five folds | 25 | 123.949352730 s evaluation; 119.523241819 s fit sum |
| All-development selected/reference refits | separate | 5 | 29.952690597 s fit sum |

The final searches total **48 configurations / 240 CV fits**, exactly the declared
plan, with zero automatic refits, failed/interrupted fits or duplicate searches.
Profile and preservation add 30 fits, then five development refits: **275 real
development fits total**. Bootstrap separately performs two synthetic XGBoost
and three synthetic Phase 2 compatibility fits; fixture-test training is not
part of the scientific search budget and was not individually enumerated.

Combined search.fit runtime is **533.733963917 seconds**; actual search fit sum is
523.676203757 seconds. Selection orchestration takes **155.700583981 seconds**,
including OOF reconstruction, development fits, reconciliation and serialization.
Profile + search + selection recorded evaluation/orchestration times sum to
691.831830600 seconds; dependency setup and test-suite time are separate.
MLflow parent elapsed times including logging total **704.154 seconds**.
The profile's linear tree-count planning estimate was 299.22 seconds versus
75.24 measured XGBoost search.fit; it was explicitly an estimate, not a bound.
Measured profiling supported retaining one worker/thread and bounded 100–300
search trees/depths 2–4. All ranges, sampled candidates and seeds preceded fits.

| Run | MLflow ID |
| --- | --- |
| Logistic search | `0c41719e0c73482f875a4015477a03c6` |
| Forest search | `e055463d1abd40f3bcdd6a2bd47f82a8` |
| XGBoost profile | `80034d2113a04f6ab978837a292e294c` |
| XGBoost search | `6c2fee1f9e5e4bfeab64e9bcda9ffed6` |
| Selection/reference preservation | `6a0725d18b164582938e0b07b2df6b27` |

All **53** relevant MLflow records (48 search children + three search parents +
profile + selection) are FINISHED. Child IDs are in family manifests. The
accepted Phase 2 MLflow implementation was preserved.

## Saved models, provenance and durability

Five development-fitted bundles are explicitly preserved: selected
`xgboost_05_engineered_none`; reference `xgboost_04_engineered_none`,
`random_forest_02_engineered_none`, `logistic_00_engineered_none` and `dummy_prior`.
Each has an 18,000-row development training-ID hash, schema/encoded names,
parameters, seed, source/split/code/environment hashes, fit-local preprocessing,
OOF pipelines/predictions and save/load evidence. No calibration or
policy-validation rows enter base/reference fitting.

Independent recomputation of fingerprints from the 19 raw financial fields for
all 18,000 development IDs agrees with frozen assignments: 17,508 distinct
financial-profile groups, no cross-fold groups and exactly 3,600 rows per fold.
This check opens no label file and converts no held-out financial values.

The accepted full lock SHA is
`31e7241f3499567f92579f1381892351dcd433faf219fe8b0be70321937e6b57`;
the accepted code tree is
`bcad5c99614b24044c72f904ce1a73c2552d82528b50d90679478cec3f50a44f`.
The old Phase 2 lock remains archived as `requirements-phase2.lock`, with SHA
`b8f4f36250c998b0d9850d8d99d6968b6810c244c06aa7c1262bb28d91c00fd5`.
The original Phase 1 lock, workbook and split hashes remain unchanged.

Logistic/forest reuse proofs were independently reproduced against all 36
original source/config/lock snapshots and their original dependencies. All
existing packages and numerical source agree; only `xgboost-cpu==3.0.5`, the
validated new lock and reviewed runner/CLI changes differ. The proofs match
those saved by selection exactly and record zero additional search fits.
Each final bundle distinguishes original search provenance from final refit
provenance. Git commit remains null; content hashes identify code honestly.

The accepted durable root is:

```text
/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime
```

The preserved copy contains **2,682 regular files / 131,298,257 bytes** of model,
OOF, compact evidence, original provenance and tracking records, byte-equivalent
to the intact original runtime. The earlier `phase3-20261008-194353` backup is
retained but lacks the final selection; it is not the Phase 4 loading root.
[Preservation inventory](phase3_preservation_inventory.csv) records every verified
file/hash/size. No original runtime, backup, manifest or tracking record was moved,
rewritten or deleted.

Some input/source/config links in the backup still target the project. They are
not advertised as independent archived bytes. The 36 materialized original
source files plus the three materialized accepted runner/CLI/lock overrides in
`reports/phase3_source_snapshots/accepted/` reconstruct the accepted code tree
exactly; this was verified. Frozen input links remain bound to their pinned
hashes and original immutable project files.

Copied MLflow metadata retains absolute `/tmp/credit-risk-phase3-real-03kpjn82`
artifact URIs. Phase 4 **loads the verified durable pipeline directly**, without
MLflow lookup or retraining. Historical MLflow artifact APIs require the original
runtime path; if absent, restore the backup to that exact path without altering
metadata. Detailed loading, integrity, restoration and source-reconstruction
commands are in [reproduction-phase3.md](../docs/reproduction-phase3.md) and
`docs/phase4-checkpoint.md` (private historical evidence).

## Acceptance checks and gate

Reported WSL execution evidence: bootstrap compatibility verified and lock updated; **110
passed**, live SQL disabled. Final project PostgreSQL was ready at
127.0.0.1:55432; `CREDIT_RISK_SQL_TEST=1 .venv/bin/python -m pytest -q -p no:cacheprovider`
returned **111 passed in 49.88s, no skips**. Family and selection artifact/tracking
verification passed. These are reported WSL executions; acceptance did not repeat them. Bootstrap includes Ruff and import/fit/save/load smoke checks.

Read-only verification reconciled all **864,000 search OOF rows**, **240
fold results**, five preserved candidates' **90,000 OOF rows**, fold means/SDs,
pooled metrics, all 53 tracking records, source/input/lock hashes and durable
copies. Maximum metric difference was **0.0**. Selection was independently
reproduced without calling the production selector.

The separate validation reloaded all **35** trusted saved fold/development
pipelines (25 selection folds + five development + five profile), verified their
fit-local medians/modes/vocabularies/scaling, weights, ID hashes, names, exclusions,
positive-class mapping and save/load predictions without fitting. All saved OOF
predictions agree within **1e-12**; the retained XGBoost/profile maximum
difference is **9.71445×10⁻¹⁷**. A global observed maximum was not retained.
Batch/single and repeated-load predictions agree for all five development bundles.
Review: [validation-phase3-acceptance.md](../docs/validation-phase3-acceptance.md).
Receipt: `reports/phase3_acceptance.json` (private historical evidence).

All Phase 3 exit requirements pass; no scientific or artifact-delivery blocker
remains. Git initialization/commit and remote/fresh-environment reproduction are
not claimed and remain general delivery work, not Phase 3 scientific blockers.
Subsequent calibration and policy selection used this exact fixed base.
See [Phase 4](phase4.md).
