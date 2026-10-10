# Batch scoring

The scorer loads the accepted fitted pipeline from the separately versioned
public package and produces default probabilities and hypothetical actions for
unlabeled CSV/Parquet records. It never fits, reads labels or uses PostgreSQL,
MLflow, the original repository or a private payload. The
[distribution](../bundles/README.md) is prepared locally for repository inclusion;
public availability remains pending publication. [Setup](setup.md#artifact-restoration)
provides installation and digest-checked restoration.

## Prerequisites and command

Use the validated Linux/WSL Python 3.12.11 environment and pinned dependencies,
including PyArrow for Parquet. Restore `public-scoring-v1` into a chosen new
local directory. From the publication checkout:

```bash
.venv/bin/python -m credit_risk.scoring score --trust-artifacts \
  --artifacts local/scoring-v1 \
  --input examples/scoring_batch.csv \
  --output local/example-output \
  --scenario base --policy empirical
```

Use absolute artifact, input and output paths to run from any working directory
with the installed package. Relative paths resolve from the current directory.
Choose a new output directory. All three path arguments and explicit artifact
trust are required. `--scenario` and `--policy` select already frozen definitions;
they do not tune a cutoff. CSV and Parquet share the same financial contract.
The legacy `credit_risk.phase5 score` loader remains for historical full bundles;
it is separate from this portable public command.

## Input contract

| Field group | Required columns | Meaning |
| --- | --- | --- |
| Identity | `record_id` | Nonempty unique record ID; string formatting is preserved |
| Credit limit | `limit_bal` | Finite positive value when supplied |
| Repayment history | `pay_status_2005_04` through `pay_status_2005_09` | Six integral category values in chronological order |
| Bill history | `bill_amt_2005_04` through `bill_amt_2005_09` | Six signed bill balances |
| Payment history | `pay_amt_2005_04` through `pay_amt_2005_09` | Six nonnegative payments |

The header must contain exactly these 20 columns. Target, audit, alternate ID,
engineered and extra fields are forbidden. The scorer computes row features
internally using the [versioned financial contract](data_contracts.md).

| Condition | Behavior |
| --- | --- |
| Missing/extra/duplicate headers; empty/duplicate/NUL IDs | Reject the batch |
| Malformed CSV widths, quoting or NUL bytes | Reject before pandas can shift/truncate identities or values |
| Header-only CSV | Valid empty batch; zero rows reconcile |
| Missing financial cells | Use frozen preprocessing; no new imputation fit |
| Unseen integral repayment categories | Score with the frozen unknown-safe encoder; business validity remains unestablished |
| Boolean/nonnumeric/nonfinite values, supplied nonpositive limit, negative payment, nonintegral status, arithmetic overflow | Quarantine the affected row with a reason |
| Negative bill balances | Preserve legitimate signed values |

CSV preserves leading-zero IDs and explicitly empty cells. A truncated record is
a malformed schema, not an equivalent missing cell. Parquet IDs also reject NUL
characters before output. Accepted and quarantined rows retain identity, with
input/scored/quarantined counts reconciled.

## Outputs and integrity

| Output | Contents |
| --- | --- |
| `scored.csv` | `record_id`, `p_default`, `decision_simulated`, `expected_utility`, `model_version`, scenario/policy IDs and validation status |
| `quarantined.csv` | Rejected row identity, input position, validation status and reason |
| `receipt.json` | Counts, input/bundle/manifest hashes, chosen scenario/policy, no-fit/no-database declarations |

Expected utility describes the chosen action; abstention is zero. Actions are
`accept_simulated` or `abstain_simulated`, not real approval decisions. See
[policy assumptions](calibration_policies.md).

The public package contains the unchanged selected pipeline and financial schema,
all 88 frozen policy definitions across 11 scenarios, a notice and a new manifest.
Before deserializing, the loader verifies the pinned delivery content hash, exact
file inventory, sizes/checksums, supported dependency versions and hashes of the
unchanged financial schema/feature/pipeline/policy modules. It also checks class-1
mapping and the financial allowlist. Missing, corrupted or incompatible packages
fail; explicit trust is still required. Original historical freeze/review checks
remain in their separate loader.

`model_version` and `bundle_sha256` retain the original accepted probability-bundle
SHA-256 `45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd`.
The receipt additionally records the actual unchanged fitted pipeline SHA,
original freeze SHA, `distribution_version`, `delivery_sha256` and the new manifest
file SHA. The new archive, manifest and receipt identities are distribution
metadata, not original acceptance receipts. No scientific output identity field
or expected saved output was changed.

## Recorded example and limits

The [example input](../examples/scoring_batch.csv) is synthetic and unlabeled;
it contributes no real-data performance evidence. Recorded scoring produced
12 outputs and zero quarantines, with save/load and single-row/batch agreement.
The [saved output](../examples/scoring_output.csv) and
[receipt](../reports/phase5/batch_receipt.json) retain the evidence. The public package verification is separate evidence in
[the local delivery report](../reports/public-scoring-delivery.json).
Its expected output is byte-identical: all 12 synthetic rows abstain with zero
chosen-action expected utility. These software examples supply no real-data
performance measurements.

The 3,000-row local benchmark measured about 4,126.7 rows/s for
validation/features/prediction, excluding loading and I/O. It is neither production
throughput nor population performance. Record fields must satisfy the historical
availability contract; successful scoring alone does not establish new-applicant
validity, fairness or contemporary lending applicability.
