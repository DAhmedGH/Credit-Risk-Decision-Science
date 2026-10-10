# Synthetic scoring example

The unlabeled batch exercises the frozen scorer's financial contract and record-ID
preservation. It is a software example, not a source of real-data measurements.

| File | Contents |
| --- | --- |
| [scoring_batch.csv](scoring_batch.csv) | 12 synthetic records; `record_id` plus 19 normalized raw financial fields |
| [scoring_output.csv](scoring_output.csv) | Previously verified probabilities, simulated actions, expected utility and model/policy identities |
| [Batch receipt](../reports/phase5/batch_receipt.json) | Recorded 12 scored rows, zero quarantines and source/model hashes |

Follow [artifact restoration](../docs/setup.md#artifact-restoration) and
[batch scoring](../docs/batch_scoring.md) before running the CLI. The included
[public scoring package](../bundles/README.md) replaces the private-payload
dependency for maintained scoring. Publication is pending; the package is
prepared locally. The unchanged saved output retains historical evidence and
is the comparison target for [public delivery checks](../reports/public-scoring-delivery.json).
