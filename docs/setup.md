# Setup and reproduction

The maintained source, synthetic fixtures and a small frozen scoring package
are prepared locally for repository distribution. Publication remains pending;
no repository or download URL has been published. Once this checkout is
published, its `bundles/` directory supplies everything needed for maintained
scoring. Raw data and full historical replay attachments remain separate.
For repository checks, install the pinned environment and run Ruff/fixture pytest.

| Workflow | Required inputs | Execution boundary |
| --- | --- | --- |
| Public clone checks | Source, committed lock, synthetic fixtures and included scoring package | No real dataset, private payload or training database |
| Maintained scoring | Publication source and included trusted public scoring package | Frozen prediction; no fitting, database or experiment store |
| Historical reporting/monitoring | Payload and complete accepted-source archive | Source-bound checks and new saved-evidence/synthetic reports |
| Historical core reproduction | Historical copy and pinned environment/container | Data/features/splits and saved-evaluation checks; zero model fits |

Run commands from the project root in Linux/WSL. Dependency installation needs
network access or a compatible package cache. Replace `/path/to/...` placeholders
with supplied files and new private destinations.

## Public clone checks

Python 3.12.11 and the preserved 72-pin lock are the recorded environment.
NumPy 2.2.6, pandas 2.3.3, sklearn 1.7.2, XGBoost CPU 3.0.5, SHAP 0.48.0,
Matplotlib 3.10.6 and PyArrow 21.0.0 are pinned. PyArrow added Parquet support
without changing the preceding 71 pins. An isolated Python 3.12.11 interpreter
is required; otherwise use Docker below.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m pip check
.venv/bin/ruff check . --no-cache
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m pytest -q -p no:cacheprovider
```

Some fixtures fit small synthetic estimators; they do not refresh portfolio
metrics. Live SQL is optional; see [testing and CI](ci_cd.md).

### Container checks

Docker must be installed and available to WSL. Build before network-disabled tests.
The Dockerfile pins the public ECR Python mirror digest
`sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7`.
Its build context excludes raw data, historical model stores, environments,
credentials and caches; the small public scoring package is included.
CI uses the exact lock, fixtures and an isolated PostgreSQL service. A reported
Actions run failed at an excluded historical receipt; the
[public smoke repair](ci_cd.md#public-smoke-repair) is locally verified, with remote
confirmation pending after the fix is pushed.

```bash
docker build -t credit-risk-public-scoring:local .
docker run --rm --network none credit-risk-public-scoring:local
docker run --rm --network none --read-only --tmpfs /tmp \
  credit-risk-public-scoring:local python scripts/verify_public_scoring.py
```

## Artifact restoration

The proposed repository distribution includes
[credit-risk-scoring-v1.tar.gz](../bundles/credit-risk-scoring-v1.tar.gz),
[checksum](../bundles/credit-risk-scoring-v1.sha256) and
[manifest](../bundles/credit-risk-scoring-v1.manifest.json).
Version: `public-scoring-v1`; archive size: 29,213 bytes.
No private payload or original repository is needed for this route. Availability
is currently local preparation only; do not interpret these files as a live
release download. The [distribution guide](../bundles/README.md) records contents,
identities and remaining publication steps.

From the publication checkout after installing the pinned environment:

```bash
(cd bundles && sha256sum -c credit-risk-scoring-v1.sha256)
.venv/bin/python -m credit_risk.scoring restore \
  --archive bundles/credit-risk-scoring-v1.tar.gz \
  --sha256 d2fb60ca57f3b8b39fc271b62a2f0386db35842a8389d3444a4e6d6af6ce1349 \
  --destination local/scoring-v1
.venv/bin/python -m credit_risk.scoring verify --artifacts local/scoring-v1
.venv/bin/python -m credit_risk.scoring score --trust-artifacts \
  --artifacts local/scoring-v1 --input examples/scoring_batch.csv \
  --output local/example-output --scenario base --policy empirical
cmp local/example-output/scored.csv examples/scoring_output.csv
```

Choose new installation/output directories. Restoration checks the archive SHA,
streams only the five permitted regular members with size bounds, rejects unsafe
members and refuses an existing destination. It then checks the separately pinned
delivery manifest and all member hashes. Verification checks financial module
hashes and runtime compatibility without deserializing. Scoring requires explicit
`--trust-artifacts`: checksums establish integrity, not safety of arbitrary joblib
objects. Artifact, input and output paths may be absolute, so scoring works from
any directory with the installed publication code.

The synthetic example produces 12 scored rows, zero quarantines and byte-identical
`scored.csv` relative to the accepted saved example. Its probabilities, actions,
utilities, IDs and ordering remain unchanged. The output receipt has new delivery
metadata; `model_version` retains the original accepted probability-bundle hash.
See [batch scoring](batch_scoring.md) for contracts and meanings.

The UCI workbook comparison at `2026-10-10T18:00:23.006402Z` remains recorded in
[the provenance receipt](../reports/provenance/uci350-official-comparison-20261010T180023Z.json).
The original acquisition date/download chain remain unknown. This package
contains no workbook or labels and does not change that provenance history.

## Artifact identities

| Identity | SHA-256 |
| --- | --- |
| Freeze content | `89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b` |
| Freeze manifest file | `0cd8c5c63e90ffc159acfa5fb63d10affeda015f885171e3bde9b4c08402e6f1` |
| Probability bundle | `45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd` |
| 72-pin lock | `c1a5bad0f66c43644ed3f63fa083e5b992d219fff57b4b9374784f337e02c2c3` |
| Historical source/test map | `816b8cce9ecd1327f94d971d0922b45d22671b1a9a4a1c085360c491f56f0130` |
| Saved final predictions | `144e6861e40c65ed7871844a0dbf80a8ec707bdab38dcc863cdeea2fec8cf23c` |
| Bootstrap plan | `18ecf64cac061d62831872327e7bd08d5d2e3e4902acac4086529b879e61b447` |

## Historical reproduction

Historical replay uses a separate private 174-file payload,
`credit-risk-phase5-artifacts.tar.gz` (9,819,660 bytes), SHA-256
`0a4f075b34257eb651f10cf1edcdaf5852aeb3fb76629af0a6c90b3f090a49c2`.
Its original bundle includes reference models, review/evaluation evidence and
source/input attachments. This public five-member scoring package cannot replace
that historical payload. Preserve its original identities and use only a trusted
copy. [Original delivery inventory](../reports/phase5/artifact_delivery.json).

Historical preflight/report/monitoring/core reproduction bind exact original source/test
hashes. Maintained software corrections deliberately fail those historical source
guards. Presentation changes do not replace the original accepted documents or
receipt bytes. Historical manifests retain their original identities; this new
publication history has a separate source commit.

Exact historical replay additionally requires the private
`credit-risk-accepted-source.tar`, exported from the accepted source commit
`fb022d9dca79d6aee1a565a62c36df33ece743e2`. Its SHA-256 is
`aea2618455b8cd99ebc6123bc6ae730ecfd55dc7d1c86cd18c8066aa9a2a537d`. This full source/configuration/receipt archive is preserved
separately and is not uploaded with the publication checkout. The scientific
payload's 48-file source snapshot alone is not the complete historical checkout.

Verify the accepted-source digest against the recorded value before extraction.

```bash
sha256sum /path/to/credit-risk-accepted-source.tar
.venv/bin/python scripts/restore_phase5.py /path/to/credit-risk-phase5-artifacts.tar.gz \
  --sha256 0a4f075b34257eb651f10cf1edcdaf5852aeb3fb76629af0a6c90b3f090a49c2 \
  --destination /path/to/private/credit-risk-historical
tar -xf /path/to/credit-risk-accepted-source.tar -C /path/to/private/credit-risk-historical
cd /path/to/private/credit-risk-historical
# Create this copy's pinned environment with the venv/pip commands above.
.venv/bin/python -m credit_risk.phase5 preflight
```

Preflight writes `reports/phase5_preflight.json`; it is not read-only.

Historical source attachments may contain local execution notes and must remain
private. Earlier phase recipes require their original locks, receipts and private
Phase 3 backup; see [the historical checkpoint recipes](#historical-checkpoint-guides). Do not recreate a receipt or copy
presentation text over a required historical file to make a hash check pass.

### Saved-evidence reporting and monitoring

Normally inspect saved reports rather than run evaluation again. In the private
historical copy, existing reporting refuses overwrite; preserve tracked aggregates
in a sibling first. Log saved-outcome access before any replay.

```bash
mv reports/phase5 reports/phase5_preserved
.venv/bin/python -m credit_risk.phase5 report
.venv/bin/python -m credit_risk.phase5 monitor --output reports/monitoring_new
```

Monitoring uses seed-42 unchanged-row policy-validation composition demos
(weight multiplier 3, 3,000 draws) and separate unlabeled corruptions. Development
PSI bins include tails/missingness, epsilon 1e-6 and renormalization. These are
synthetic shifts, not observed temporal/concept drift. Maintained monitoring
refuses existing receipts/nonempty outputs; use new paths for historical code too.

The delivered fresh-core reproduction checks accepted fitted identities and
saved outcomes. It is not a fresh retraining of all model searches/calibration.
Earlier fitting recipes also depend on checkpoint-specific inputs and the private
development-model backup referenced by `configs/phase4.toml`; the final payload
alone does not supply a portable complete training history.

### Fresh-core container reproduction

Build the fixture image first. The host `artifacts/runtime/phase5` directory must
exist; choose an output name that does not exist.
For the recorded fresh-core container reproduction, mount the private historical
checkout read-only and use a new writable output mount. Record saved-outcome
access first. This command reuses accepted fitted identities; it does not rerun
searches, base fitting or calibration.

```bash
docker run --rm --network none -e PYTHONPATH=/project/src \
  -v "$PWD:/project:ro" -v "$PWD/artifacts/runtime/phase5:/delivery" \
  credit-risk-public-scoring:local python /project/scripts/reproduce_phase5.py \
  --root /project --output /delivery/reproduction_new
```

The original evaluation command is
`python -m credit_risk.phase5 evaluate --readiness reports/phase5_readiness.json`.
The accepted workspace refuses a second evaluation directory. Preserve accepted
evidence and do not rerun it as a setup or presentation check.

## Verification boundaries

The recorded core reproduction validated 30,000 rows, byte-identical splits/folds,
exact saved metrics/341 intervals/plan and synthetic scoring within 1e-12.
Feature error 1.1641532182693481e-10 met
`abs(error) <= 1e-10 + 1e-12*abs(reference)`.
[Reproduction receipt](../reports/phase5/reproduction_receipt.json).

Original delivery, subsequent software checks and publication restoration checks
are separate evidence in [testing and CI](ci_cd.md#recorded-verification-provenance).
Historical passes are not newly executed documentation checks. Original failure
records remain in private historical attachments and the
[delivery report](../reports/phase5.md); no accepted scientific result changed.

The historical population, unknown original acquisition chain, absent temporal
and external validation, synthetic utility/monitoring, conditional intervals and
unconfirmed successful remote CI limit interpretation. No profit, causal lending impact,
new-applicant validation, fairness certification or production deployment is claimed.

## Historical checkpoint guides

These are checkpoint recipes, not fresh-clone onboarding steps. Keep their own
source, locks, inputs and required original receipts together in a private copy.

| Recorded checkpoint | Preserved recipe |
| --- | --- |
| Data validation, ingestion and features | [Data workflow](reproduction.md) |
| Baseline models and pipelines | [Baseline workflow](reproduction-phase2.md) |
| Bounded search and selection | [Model search](reproduction-phase3.md) · [checkpoint history](reproduction-phase3-history.md) |
| Calibration, explanations and freeze | [Bundle freeze](reproduction-phase4.md) |
