# Project status

All five phases are complete on the recorded local evidence. The study uses
30,000 historical customer snapshots, four frozen fingerprint-group partitions
(18,000/4,500/3,000/4,500 rows), and five development folds. Source attribution,
unknown original acquisition details, prediction-time assumptions and limitations
are documented in the [model card](model-card.md) and [data contract](data-contract.md).

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
Remote GitHub Actions has not been observed.

The publication source includes software corrections for malformed batches,
missing-value routing, monitoring output preservation, and command validation.
Accepted model, split, prediction, policy, manifest and historical receipt bytes
are preserved. This documentation is a presentation summary; exact historical
receipt/source attachments are retained privately.

Restoration and scoring require the trusted private payload; a source-only clone
cannot load the frozen model. Follow [reproduction and scoring](reproduction-phase5.md).
No further modeling phase is pending. No push, public artifact hosting or deployment
has occurred. Historical Taiwan data, absent temporal/external validation,
synthetic utility and conditional uncertainty remain material limitations.
