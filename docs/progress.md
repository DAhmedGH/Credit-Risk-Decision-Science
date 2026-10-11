# Project status

All five phases reached their recorded local acceptance checkpoints. Completion
is qualified by unknown original acquisition records, historical replay
dependencies; the [checklist](project-checklist.md) distinguishes these from
passed local checks and [observed remote fixture CI](ci_cd.md#observed-github-status).
The study uses
30,000 historical customer snapshots, four frozen fingerprint-group partitions
(18,000/4,500/3,000/4,500 rows), and five development folds. Source attribution,
unknown original acquisition details, prediction-time assumptions and limitations
are documented in the [model card](model_card.md) and [data contract](data_contracts.md).

The supplied workbook was subsequently verified byte-for-byte against the official
UCI archive retrieved at `2026-10-10T18:00:23.006402Z`. Recorded accepted,
existing-local and official-member hashes all agree. The
[new provenance receipt](../reports/provenance/uci350-official-comparison-20261010T180023Z.json)
records this separate comparison; the original acquisition date/download chain
remain unknown. During that provenance-only task, only public provenance
documentation and this new receipt changed. No packaging, fitting, search,
calibration or final-test evaluation ran during that task.
The receipt was independently rechecked against retained HTTP records, archive
bytes and the unchanged local workbook. All 94 local documentation link targets
resolve; Git whitespace checks pass. Original workbook bytes/mtime, historical
manifests/receipts and both staging indexes are preserved.

Development comparison completed 48 bounded configurations and 240 search fits.
The development-selected 100-tree XGBoost remains fixed. Policy validation
retained raw probabilities: log loss 0.4329887140, versus 0.4362283190 for
sigmoid and 0.4559940960 for isotonic calibration.

The frozen final evaluation scored 4,500 accounts in 4,378 profile groups.
Selected-model AP is 0.56421764 [0.53375142, 0.59580369], ROC-AUC
0.79398201 [0.77762987, 0.80964561], log loss 0.42331366
[0.40652328, 0.44119251], and Brier score 0.13319703
[0.12662097, 0.14062259]. The empirical base policy accepts 1,028 accounts,
with 55 defaults and 4.70 hypothetical utility units per customer. All 88 frozen
policy/scenario results and 341 interval statistics are retained in
[the results](../reports/results.md).

Recorded delivery checks include 207 SQL-enabled tests; 206 container tests
with one expected SQL skip; 114.778-second fresh-core reproduction with zero
fits; 174 restored payload hashes; and byte-exact synthetic batch scoring.
The subsequent software checks recorded 231 SQL-enabled passes in 82.04 seconds
and a separately reported rebuilt-container result of 230 passes, one SQL skip
in 48.75 seconds. The reported container execution had no supplied raw terminal
log. These are distinct executions, not a combined suite or new presentation checks.
A subsequent remote Actions failure was reported in the public Phase 4 smoke:
it tried to read an excluded historical acceptance receipt. The fixture smoke
now retains calibration/TreeSHAP/plot/save-load coverage without historical inputs;
the original acceptance guards remain unchanged. See
[CI repair evidence](../reports/public-ci-smoke-fix.json). The repair was subsequently
pushed as `412dd68`, and its
[remote run succeeded](https://github.com/DAhmedGH/Credit-Risk-Decision-Science/actions/runs/38112715548).
The following README revision also passed; see
[observed GitHub status](ci_cd.md#observed-github-status). Historical test counts
above and the earlier local receipt remain unchanged.
The repair's rebuilt-container checks ran all three actual CI smokes and Ruff;
`pytest -q` passed 270 tests with one expected SQL skip in 51.50 seconds.
The separate SQL step passed four tests in 0.24 seconds against a new marked
disposable database. Two new regressions verify receipt-free fixture smoke and
continued rejection by the historical guard. A bare-pytest fixture import was
also corrected; no accepted scientific workflow was run.

The publication source includes software corrections for malformed batches,
missing-value routing, monitoring output preservation, and command validation.
Accepted model, split, prediction, policy, manifest and historical receipt bytes
are preserved. This documentation is a presentation summary; exact historical
receipt/source attachments are retained privately.

Maintained scoring now uses the separately versioned
[public package](../bundles/README.md), available in the public repository. It
contains the unchanged selected fitted pipeline and frozen definitions, with
no private-payload dependency. Historical replay still requires additional
original inputs and source/evidence attachments. Follow [reproduction and scoring](setup.md).
The subsequent public-delivery task prepared a 29,213-byte `public-scoring-v1`
archive and verified restoration/scoring in an offline container with no host
mounts. The synthetic example scored 12/12 rows with zero quarantines and
byte-identical saved output; all 88 frozen policy definitions were checked.
Focused tests passed 55 cases in 5.60 seconds. The rebuilt container passed
268 tests with one expected live-SQL skip in 50.45 seconds; Ruff passed.
Installed-package scoring also passed from a different directory with
`PYTHONPATH` removed. See the [delivery evidence](../reports/public-scoring-delivery.json)
and [focused review](../reports/public-scoring-review.md). No accepted model was
fitted and no scientific evaluation was rerun.
No further modeling phase is pending. The repository and scoring package are
published on GitHub, with successful fixture CI observed for the revisions above.
No production deployment is claimed. Historical Taiwan data, absent temporal/external validation,
synthetic utility and conditional uncertainty remain material limitations.
