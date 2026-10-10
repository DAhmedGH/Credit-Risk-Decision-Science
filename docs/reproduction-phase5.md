# Reproduce the frozen study and score an unlabeled batch

The maintained source and synthetic fixtures are public. Raw data, serialized
models and exact historical execution attachments are private local files.
No public model download endpoint is provided: a clone alone cannot score.
Use only a trusted copy of the payload below. For source-only checks, install
the pinned environment and run Ruff/fixture pytest; no dataset or bundle is needed.

## Environment and source-only checks

Python 3.12.11 and the preserved 72-pin lock are the recorded environment.
NumPy 2.2.6, pandas 2.3.3, sklearn 1.7.2, XGBoost CPU 3.0.5, SHAP 0.48.0,
Matplotlib 3.10.6 and PyArrow 21.0.0 are pinned. PyArrow added Parquet support
without changing the preceding 71 pins. An isolated Python 3.12.11 interpreter
is required; otherwise use Docker below.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/ruff check . --no-cache
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m pytest -q -p no:cacheprovider
```

The Dockerfile pins the public ECR Python mirror digest
`sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7`.
Its build context excludes raw data, models, environments, credentials and caches.
CI uses the exact lock, fixtures and an isolated PostgreSQL service. No remote
GitHub Actions result has been observed.

```bash
docker build -t credit-risk-phase5:local .
docker run --rm --network none credit-risk-phase5:local
```

## Restore the private payload for maintained-code scoring

Obtain the original local `credit-risk-phase5-artifacts.tar.gz` separately from
its owner. The 9,819,660-byte archive contains 174 payload files: the full frozen
bundle with its required original review evidence, pinned input manifests and
workbook/exports, saved evaluation/source snapshots and the synthetic example.
It excludes credentials, environments, caches and tracking stores. Keep the
archive and restored outputs private; do not add them to a publication package.
Exact inventory: [artifact_delivery.json](../reports/phase5/artifact_delivery.json).

SHA-256: `0a4f075b34257eb651f10cf1edcdaf5852aeb3fb76629af0a6c90b3f090a49c2`.
The original workbook was supplied locally. Its official ZIP/download chain and
original retrieval time remain unknown; a fresh download is not an interchangeable
input for claiming identical experiments.

From the committed publication checkout, restore into a new private directory,
then add the maintained source. The restorer checks the digest and rejects
traversal, links, special entries and existing destinations. The source archive
overlays only identical payload manifest/example files; model evidence is retained.

```bash
python3 scripts/restore_phase5.py /path/to/credit-risk-phase5-artifacts.tar.gz \
  --sha256 0a4f075b34257eb651f10cf1edcdaf5852aeb3fb76629af0a6c90b3f090a49c2 \
  --destination /path/to/private/credit-risk-restored
git archive HEAD | tar -x -C /path/to/private/credit-risk-restored
cd /path/to/private/credit-risk-restored
# Restored copies contain no environment; use the setup commands above here.
```

Standalone scoring verifies all 106 frozen artifact hashes and the original
review binding before trusted local deserialization. It also verifies the feature
schema and imported financial transformation hashes. It requires no training
database or raw labels and performs no fitting. Do not remove required original
review evidence or reseal the manifest to match presentation documents.

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
.venv/bin/python -m credit_risk.phase5 score \
  --input examples/scoring_batch.csv --output artifacts/runtime/my_batch \
  --scenario base --policy empirical
```

Choose a new output directory. Outputs are `scored.csv`, `quarantined.csv` and
`receipt.json`. Input is `record_id` plus exactly 19 raw financial columns;
target, audit, engineered and extra columns are forbidden. Fatal schema/identity
errors reject the batch. Missing cells and unseen integral status codes use
frozen preprocessing. Nonnumeric/nonfinite values, nonpositive provided limits,
negative payments, nonintegral statuses and feature overflows quarantine rows.
Signed balances are valid. CSV preserves leading-zero IDs, rejects malformed
widths/quoting/NUL bytes; NUL IDs are also fatal in Parquet. Header-only batches
reconcile zero rows.

Output preserves IDs, probability, simulated action, chosen-action expected
utility, model hash, scenario/policy IDs and validation status. Abstention has
zero utility. The example is synthetic and unlabeled: recorded results are
12 scored, zero quarantined, with [saved output](../examples/scoring_output.csv)
and [receipt](../reports/phase5/batch_receipt.json). Local 3,000-row throughput
4,126.70 rows/s excludes model loading/I/O and is not production evidence.

## Identities and historical replay

| Identity | SHA-256 |
| --- | --- |
| Freeze content | `89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b` |
| Freeze manifest file | `0cd8c5c63e90ffc159acfa5fb63d10affeda015f885171e3bde9b4c08402e6f1` |
| Probability bundle | `45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd` |
| 72-pin lock | `c1a5bad0f66c43644ed3f63fa083e5b992d219fff57b4b9374784f337e02c2c3` |
| Historical source/test map | `816b8cce9ecd1327f94d971d0922b45d22671b1a9a4a1c085360c491f56f0130` |
| Saved final predictions | `144e6861e40c65ed7871844a0dbf80a8ec707bdab38dcc863cdeea2fec8cf23c` |
| Bootstrap plan | `18ecf64cac061d62831872327e7bd08d5d2e3e4902acac4086529b879e61b447` |

Historical preflight/report/core reproduction bind exact original source/test
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

```bash
sha256sum /path/to/credit-risk-accepted-source.tar
python3 scripts/restore_phase5.py /path/to/credit-risk-phase5-artifacts.tar.gz \
  --sha256 0a4f075b34257eb651f10cf1edcdaf5852aeb3fb76629af0a6c90b3f090a49c2 \
  --destination /path/to/private/credit-risk-historical
tar -xf /path/to/credit-risk-accepted-source.tar -C /path/to/private/credit-risk-historical
cd /path/to/private/credit-risk-historical
# Install its pinned environment using the no-fit setup above.
.venv/bin/python -m credit_risk.phase5 preflight
```

Historical source attachments may contain local execution notes and must remain
private. Earlier phase recipes require their original locks, receipts and private
Phase 3 backup; see the phase-specific guides. Do not recreate a receipt or copy
presentation text over a required historical file to make a hash check pass.

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

For the recorded fresh-core container reproduction, mount the private historical
checkout read-only and use a new writable output mount. Record saved-outcome
access first. This command reuses accepted fitted identities; it does not rerun
searches, base fitting or calibration.

```bash
docker run --rm --network none -e PYTHONPATH=/project/src \
  -v "$PWD:/project:ro" -v "$PWD/artifacts/runtime/phase5:/delivery" \
  credit-risk-phase5:local python /project/scripts/reproduce_phase5.py \
  --root /project --output /delivery/reproduction_new
```

The original evaluation command is
`python -m credit_risk.phase5 evaluate --readiness reports/phase5_readiness.json`.
The accepted workspace refuses a second evaluation directory. Preserve accepted
evidence and do not rerun it as a setup or presentation check.

## Recorded checks and limits

Historical delivery: focused 24 tests in 32.60s; 207 SQL-enabled tests in 87.89s;
206 container tests with one expected SQL skip in 54.31s; fresh-core reproduction
in 114.778s, zero fits. The reproduction validated 30,000 rows, regenerated
features, byte-identical splits/folds, exact saved metrics/341 intervals/plan,
and synthetic scoring within 1e-12. Feature error 1.1641532182693481e-10 met
`abs(error) <= 1e-10 + 1e-12*abs(reference)`. All 174 payload hashes and byte-exact
restored scoring were verified. These are historical checks, not newly repeated
presentation work. [Reproduction receipt](../reports/phase5/reproduction_receipt.json).

Subsequent software checks recorded 231 live-SQL passes in 82.04s and separately
reported 230 rebuilt-container passes/one SQL skip in 48.75s. No raw terminal
log accompanied the latter reported execution. [Corrections and checks](../reports/project-audit.md).
The original Docker Hub/offline-cache/context and fixture failures are retained
in private historical checks and the phase report. No accepted scientific result
was changed to resolve them.

```bash
# Optional isolated SQL fixture checks: verify disposable project identity first.
python3 scripts/dev_db.py up
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CREDIT_RISK_SQL_TEST=1 \
  .venv/bin/python -m pytest -q -p no:cacheprovider
```

The historical population, unknown original acquisition chain, absent temporal
and external validation, synthetic utility/monitoring, conditional intervals and
unobserved remote CI limit interpretation. No profit, causal lending impact,
new-applicant validation, fairness certification or production deployment is claimed.
