# Five-minute walkthrough

1. Start with the task: an existing Taiwan credit-card customer's next-month benchmark risk at a released month-end snapshot; six history columns are not six labeled observations.
2. Show source reconciliation and the frozen 60/15/10/15 fingerprint-group partitions. Explain the predictor allowlist, signed balances, special status codes and fit-only preprocessing.
3. Open the development comparison/ablation. Explain bounded AP searches and why the 100-tree XGBoost was retained using the declared practical tie/log-loss/simplicity rule.
4. Show separate calibration/policy-validation evidence. Raw validation log loss beat the mappings; fixing a classifier does not guarantee calibration helps.
5. Open final-test PR/reliability plots and intervals. AP 0.5642 beats the prior baseline; the forest's small numerical lead does not change the preselected champion. Paired group intervals condition on the fitted model.
6. Explain the policy equation with synthetic G 50/L 500/C 0. The empirical 0.085 cutoff accepts 1,028 records and yields 4.70 benchmark units/customer; analytic 5.0667 is reported honestly. This cannot establish real profit or a lending intervention effect.
7. Show sensitivity and the abstain-all G 25/L 750 case, fixed fraction cutoffs, and N/A for empty acceptance. Show exact raw-log-odds SHAP and the audit support limits.
8. Score the synthetic unlabeled batch, inspect its receipt/count reconciliation, then show synthetic monitoring distributions/corruption quarantine. Finish with the reproduction guide and limitations: no temporal/external, new-applicant, causal or fairness validation.
