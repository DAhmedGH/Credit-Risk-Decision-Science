# Frozen scoring distribution

`public-scoring-v1` is prepared locally for inclusion in the publication repository.
No remote repository, release or public download URL has been published. At
29,213 bytes, the archive is small enough for ordinary Git distribution; no
separate release asset or large-file service is needed. Once the reviewed local
commit is pushed to a public repository, a clone supplies the package.

| File | Purpose |
| --- | --- |
| [credit-risk-scoring-v1.tar.gz](credit-risk-scoring-v1.tar.gz) | Five-member inference-only archive |
| [credit-risk-scoring-v1.sha256](credit-risk-scoring-v1.sha256) | Measured archive checksum |
| [credit-risk-scoring-v1.manifest.json](credit-risk-scoring-v1.manifest.json) | Versioned inventory, content hashes, runtime compatibility and model lineage |

Archive SHA-256:
`d2fb60ca57f3b8b39fc271b62a2f0386db35842a8389d3444a4e6d6af6ce1349`.
Delivery content SHA-256:
`a2a9b2883f5543a1d4da2d8026f79e4ef60be79b97343357e946f3c7a906d40c`.
The latter hashes canonical manifest content excluding its own identity field.
It is separately pinned by the public loader and differs from the archive SHA.

## Contents and scientific lineage

| Archive member | Bytes | Description |
| --- | ---: | --- |
| `pipeline.joblib` | 148,534 | Byte-identical fitted financial selector, preprocessing and selected 100-tree XGBoost |
| `feature_schema.json` | 8,018 | Unchanged accepted financial-row-v1.1 contract |
| `policy.json` | 20,763 | Exact projection of the 88 frozen policies across 11 scenarios; no evaluation tables |
| `NOTICE.md` | 2,016 | Dataset attribution, license links, derivation and dependency notices |
| `manifest.json` | 2,594 | New distribution identity, hashes and runtime/transform compatibility |

The pipeline is `xgboost_05_engineered_none`, selected in the original study,
with raw probability mapping. Phase 4 run:
`9ca62eca2665438c9c97b4889413acfa`. Original freeze content:
`89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b`.
Original probability bundle:
`45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd`.
Distributed fitted pipeline:
`265db2cbe02e88ca7c75c29f39b5c0230a29ba40e4735ea808aea08df4a5e83c`.
These identify different objects. The probability bundle includes unnecessary
reference models and metadata; its accepted selected pipeline is copied without
reserialization. The new manifest is not an original acceptance receipt.

No raw data, labels, customer-level evaluation records, SHAP samples, review
narratives, source archives, credentials, private settings, environments or MLflow
stores are included. Required code and dependencies are supplied by the installed
publication checkout. [Inventory rationale](../docs/scoring-package-inventory.md).

## Install, verify and score

Follow [setup](../docs/setup.md) to install the pinned Linux/WSL Python environment,
verify the archive and restore into a new chosen directory. Use only this trusted
package with its matching publication code. `--trust-artifacts` is explicit
because joblib can execute code; integrity checks do not make arbitrary models safe.
The [batch guide](../docs/batch_scoring.md) documents exact commands, schema,
counts, IDs, outputs and frozen policy behavior.

Restoration checks the archive SHA, streams only permitted regular members with
decompression bounds, rejects traversal/links/special/duplicate members, verifies
all file hashes and refuses existing destinations. Before model loading, the
scorer checks the pinned delivery contract, runtime versions and financial source
hashes. Absolute artifact/input/output paths work from any directory. No labels,
database, tracking store or original repository is required.

The unchanged saved example output retains the original scientific model identity.
New output receipts separately identify the actual distributed pipeline and
delivery manifest. Historical evaluation/training replay still needs the original
source, inputs and accepted evidence; this package supports frozen inference.
The [verification report](../reports/public-scoring-delivery.json) records local
checks, independent review and their boundaries.
Its Git and availability fields describe the verification checkpoint before
local commit; they are preserved as evidence of that execution.

## Maintainer packaging and publication

The existing model was packaged with `scripts/package_scoring.py`, using an
explicit read-only accepted Phase 4 directory. Packaging verifies the complete
historical freeze/review binding before copying allowlisted artifacts, compares
financial transformation hashes and produces deterministic tar/gzip bytes.
It refuses an existing output directory. This operator route requires original
accepted artifacts; end-user restoration and scoring do not.

```bash
.venv/bin/python scripts/package_scoring.py \
  --accepted-directory /path/to/accepted/phase4/run \
  --output /path/to/new/scoring-distribution
```

The concrete publication steps remaining after local review and commit are:

1. Choose/create the GitHub repository and public visibility; set its actual remote URL.
2. Push the reviewed `main` branch and confirm GitHub Actions; no remote result is yet observed.
3. Verify the archive checksum and documented route from a fresh public clone.

No tag or release is required for this small repository-distributed package.
Do not invent a repository URL or report these publication steps as complete.
