# Project walkthrough

This sequence connects the prediction task, model evidence and simulated policy
interpretation. Scoring is optional and uses the included
[public scoring package](../bundles/README.md). The linked figures, aggregates
and frozen scoring workflow are available from a public clone.

| Step | What to inspect | Interpretation |
| --- | --- | --- |
| Prediction task | [Data contracts](data_contracts.md) | One historical existing-account snapshot; all included September histories must be available |
| Data and isolation | [Architecture](architecture.md) · [modeling](modeling.md) | Row reconciliation, financial allowlist and 60/15/10/15 grouped partitions protect the stated contract |
| Development selection | [Modeling findings](modeling.md#selection-and-measured-development-findings) | Bounded AP searches and the declared practical-tie/log-loss/simplicity rule selected 100-tree XGBoost |
| Probability assessment | [Calibration](calibration_policies.md#probability-fitting-and-selection) | Separate fit/selection partitions retained raw probabilities; calibration did not improve validation log loss |
| Final evaluation | [Results and intervals](../reports/results.md) | AP 0.5642 improves on the prior baseline; the forest's numerical lead does not replace the preselected model |
| Hypothetical decisions | [Policies](calibration_policies.md) | Cutoff 0.085 accepts 1,028 records and yields 4.70 synthetic units/customer; analytic 5.0667 is also reported |
| Diagnostics | [Explanations](explanations.md) · [monitoring](monitoring.md) | Raw-log-odds associations, suppressed descriptive slices and synthetic shifts do not establish causation or fairness |
| Optional scoring | [Batch runbook](batch_scoring.md) · [setup](setup.md#artifact-restoration) | Restore the included package and inspect synthetic output/receipt reconciliation; no private payload or fitting is required |

The gain-25/loss-750 scenario retains abstain-all, and an empty accepted set has
default rate N/A. Conditional group-bootstrap intervals omit model-development
uncertainty. No temporal/external, new-applicant or intervention validation is
claimed. These limitations belong beside the figures and measurements.
