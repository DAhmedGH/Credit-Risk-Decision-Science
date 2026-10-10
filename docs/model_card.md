# Model card and intended use

The frozen model predicts released next-month default for existing accounts.
Its intended use is education and benchmark research.

## Frozen model

The selected `xgboost_05_engineered_none` uses 100 trees, no class weighting and 32 combined financial predictors under `financial-row-v1.1`. Selected by development CV AP/practical tie/log loss/simplicity; raw mapping selected by policy-validation log loss. Phase 4 run 9ca62eca2665438c9c97b4889413acfa, bundle SHA 45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd. No refitting after freeze.

## Task and intended use

The target is the released next-month default indicator, class 1, for existing Taiwanese credit-card accounts at the released month-end snapshot. April–September 2005 history is assumed available, including all September fields. One row is one customer snapshot. Intended use is education and benchmark research; hypothetical policy simulation has no validated loan-origination interpretation.

## Dataset and attribution

The supplied workbook contains 30,000 UCI 350 records, attributed to Yeh (2009), DOI 10.24432/C55S3H, CC BY 4.0. Workbook hash 30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933. It was subsequently verified byte-for-byte against the official UCI archive retrieved at `2026-10-10T18:00:23.006402Z`; all three workbook hashes agree. [Verification receipt](../reports/provenance/uci350-official-comparison-20261010T180023Z.json). Original acquisition date, download chain and original archive checksum remain unknown. Source/curated/exported counts 30,000; exclusions 0. Preserve signed bills and special repayment codes.

## Feature contract

The feature contract includes 19 raw financial predictors plus 13 deterministic row proxies. No IDs, target, sex, age, education or marital status in the primary contract. Payment/balance ratios are proxies, not contractual repayment or debt-to-income. Frozen development-fitted medians/vocabularies and preprocessing are packaged with the model. Unknown statuses use frozen all-zero one-hot handling; row overflow/nonfinite/nonnumeric/invalid payment or limit is quarantined.

## Validation and selection

Frozen development/calibration/policy-validation/test counts are 18,000/4,500/3,000/4,500. Seed 42 is fixed, and identical financial fingerprints stay together across partitions and five development folds. Test has 4,378 clusters. Calibration uses 4,500 rows excluded from base fitting; policy selection uses 3,000 different rows. Raw/sigmoid/isotonic validation log loss 0.43299/0.43623/0.45599. No test evidence changes selection.

## Final evaluation and uncertainty

| Final-test metric | Estimate | 95% interval |
| --- | ---: | --- |
| AP | 0.56422 | [0.53375, 0.59580] |
| ROC-AUC | 0.79398 | [0.77763, 0.80965] |
| Log loss | 0.42331 | [0.40652, 0.44119] |
| Brier score | 0.13320 | [0.12662, 0.14062] |

The 1,000 seed-42 paired fingerprint-group draws and 95% percentile intervals describe sample uncertainty conditional on fixed models/policies. They omit model-development uncertainty and temporal/external robustness. Forest AP 0.56636 does not replace the frozen champion. [Full comparisons](../reports/results.md).

## Simulated policy

Acceptance requires `p < cutoff`; ties abstain. Base payoffs G 50/L 500/C 0 are dimensionless synthetic utility units. Frozen empirical cutoff 0.085 accepts 1,028/4,500 accounts (22.844%), 55 defaults (5.350% accepted default rate), and yields 21,150 benchmark units, 4.70/customer [2.9012,6.3711]. Analytic cutoff 50/550 yields 5.0667/customer; empirical-minus-analytic interval includes zero. All 88 policy/scenario rows are published, including abstain-all at G 25/L 750 and accept-none default rate N/A. No profit, avoided-loss or causal claim.

## Explanations and descriptive audit

SHAP explains the selected raw XGBoost's default log odds with fixed development background and preselected policy-validation cases, not causation or intervention effects. Demographic summaries are descriptive policy-validation audits, suppressed at n<100 or fewer than 20 of either class. No group-specific optimization or fairness certification; excluded demographics may still have financial proxies.

## Scoring and monitoring

Unlabeled CSV/Parquet scoring preserves IDs, rejects target/extra/fatal schemas, quarantines row errors and reconciles counts. No fit or database access. Synthetic unchanged-record mix shifts retain meaningful benchmark labels; corruption removes labels. Development PSI bins include tails/missingness and epsilon 1e-6; warnings are heuristics, not observed temporal or concept drift. No automatic retraining.

## Limitations

The historical Taiwan existing-account sample supplies no new-applicant or contemporary Canadian representativeness, lifetime-default prediction, temporal/external cohort validation or observed intervention evidence. No production deployment is claimed. A full-data refit is a new bundle requiring new evidence. Trusted local serialized files only. [Provenance/exposure](test-exposure-log.md), [reproduction](setup.md), [leakage audit](leakage_audit.md).
