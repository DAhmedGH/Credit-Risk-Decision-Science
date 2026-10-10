# Credit Risk: Five-Week Phase Plan

**Project:** Credit Risk & Lending Decision Science Platform  
**Plan version:** 1.0, October 6, 2026  
**Specification:** `Credit-Risk-Design.md`  
**Effort target:** Approximately 65–90 focused hours, excluding substantial additional study time.

The weeks are delivery targets, not reasons to skip validation. Advance when the phase's exit gate passes.

## Exact dataset choice

Use **UCI Default of Credit Card Clients**, **dataset ID 350**, as the only real-data source for version 1.

| Property | Choice |
| --- | --- |
| Official dataset page | https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients |
| Official download | https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip |
| Workbook inside archive | `default of credit card clients.xls` |
| Published size | 30,000 customer records, 23 explanatory variables |
| Historical financial fields | April–September 2005 |
| Population | Taiwanese credit-card customers |
| License | CC BY 4.0; retain attribution |
| Dataset citation | Yeh, I. (2009). Default of Credit Card Clients. DOI: https://doi.org/10.24432/C55S3H |
| Modeling target | Released next-month default indicator; normalize to `default_next_month`, positive class `1` |

These source facts and the download are documented on the official UCI page. Verify the workbook's header layout, target column, and identifier during ingestion; do not assume a third-party CSV has the same schema.

### Acquisition decision

Use the **official ZIP/workbook**, rather than a Kaggle mirror or an unofficial cleaned CSV. It preserves a clear connection to the published data. Keep the ZIP and extracted workbook under ignored `data/raw/`; include the source URL, retrieval time, SHA-256 checksums, sheet/header selection, and attribution in a committed provenance manifest. Use an `.xls`-compatible reader such as `xlrd`, after confirming compatibility in the project environment.

Never invent a checksum in advance. Compute it from the downloaded bytes and pin the acquired version. If downloading is blocked, report that block and continue with infrastructure and synthetic test fixtures; do not substitute fabricated data for real-data results. The officially documented `ucimlrepo` import, ID 350, is a fallback only if the acquisition route and schema change are logged.

### Task framing

The model estimates **next-month default risk for existing accounts at a month-end snapshot**. Lending decisions are hypothetical payoff-based simulations. The dataset does not establish new-applicant approval outcomes or the causal effect of extending credit.

The published schema has one snapshot per customer with six history fields per financial sequence. It does not supply multiple independently labeled chronological cohorts. Consequently, version 1 uses frozen held-out customer partitions; it does not claim a chronological backtest or observed production drift.

## Working setup

The specification and phase plan accompany the `credit-risk-decision-science` repository:

```text
credit-risk-decision-science/
  Credit-Risk-Design.md
  Credit-Risk-Phase-Plan.md
```

Use an isolated Python environment, initially targeting Python 3.12, and Docker for local PostgreSQL. Keep your existing system Python unchanged. Verify package imports, a tiny fit, and serialization before locking versions. No paid cloud service, API key, GPU, or Microsoft Fabric access is required for the core project.

Maintain three lightweight progress records as implementation begins:

- `docs/progress.md`: completed work, current phase, validation evidence, next task.
- `docs/decision-log.md`: decisions, reasoning, affected artifacts, and experiment IDs.
- `docs/test-exposure-log.md`: any access to final-test outcomes and whether it was a frozen evaluation or accidental development exposure.


## Week 1 / Phase 1: Data contracts and a trustworthy modeling dataset

**Budget:** 12–16 hours.  
**Question:** What exactly are we predicting, and what information is valid at that time?

### Build sequence

1. Read the project design. Inspect the repository and environment.
2. Create the package skeleton, project configuration, dependency lock, ignore rules, and `.env.example`.
3. Acquire the official workbook; retain original bytes, checksums, attribution, and source metadata.
4. Validate IDs, target, types, category codes, signed balances, and financial-history month mapping.
5. Implement local PostgreSQL ingestion, curated tables, concise SQL feature export, and count reconciliation.
6. Implement deterministic row-level features, with tests for missing/zero denominators and special repayment codes.
7. Freeze split assignments before modeling EDA: development 60%, calibration 15%, policy validation 10%, final test 15%.
8. Keep exact financial-profile fingerprints in the same partition and CV fold. Generate five development folds with stratified group-aware allocation and record actual sizes.
9. Perform development-only EDA; write the data contract and leakage audit.

Learned imputation, scaling, category vocabularies, and distribution-based thresholds belong in fold-fitted preprocessing. They are not learned from a whole-data SQL export.

### Deliverables

- Working ingestion/validation/features/split commands.
- Source manifest and row-count reconciliation.
- `sql/001_schema.sql`, `002_curated.sql`, `003_feature_export.sql`.
- Versioned predictor allowlist, feature definitions, and split/fold manifest.
- `docs/data_contracts.md` and `docs/leakage_audit.md`.
- Relevant data, feature, and split tests.

### Exit gate

Source-to-export counts reconcile. IDs and target are valid. Month mappings are tested. Predictors exclude ID, target, and audit-only demographics. Partitions and fingerprint groups are disjoint. No final-test outcome analysis has influenced development. Reingestion of the same source cannot duplicate rows.

**Methodological questions:** Why is this an existing-account task? Why is ID not a timestamp? Which preprocessing operations could leak information?

## Week 2 / Phase 2: Baselines and fold-safe machine learning

**Budget:** 12–16 hours.  
**Question:** How much can a simple, well-validated model achieve?

### Build sequence

1. Create logistic and tree preprocessing pipelines with explicit feature names and unknown-category handling.
2. Fit a constant-prior dummy and report a majority-class hard-prediction reference separately.
3. Implement regularized logistic regression and random forest.
4. Establish fold-wise average precision, ROC-AUC, log loss, Brier score, and runtime reports.
5. Integrate MLflow, source/split hashes, Git commit, resolved parameters, and artifacts.
6. Compare raw financial predictors against raw plus engineered predictors on the same development folds.
7. Compare unweighted fits with fold-local class weighting; inspect development errors and convergence.

### Deliverables

- Baseline training/evaluation pipeline with saved run metadata.
- Development CV model comparison and feature ablation.
- MLflow runs and compact exported result tables.
- Behavioral tests confirming fold-safe fitting and positive-class mapping.

### Exit gate

All baseline models train from the CLI. Imputation/scaling/category fitting occurs only on fit rows. Fold metrics reconcile with saved predictions. No test, calibration, or policy-validation rows are used to select baseline features or hyperparameters.

**Methodological questions:** Why is accuracy misleading here? What does logistic regularization do? How can class weighting affect probability estimates?

## Week 3 / Phase 3: XGBoost, bounded tuning, and base-model selection

**Budget:** 14–18 hours.  
**Question:** Does a more complex model improve enough to justify using it?

### Build sequence

1. Smoke-test XGBoost on development data with a small configuration.
2. Run `RandomizedSearchCV` using the frozen development folds and average precision as the search score.
3. Use these initial ceilings: logistic regression 12 configurations, random forest 15, XGBoost 25, each with five folds.
4. Tune bounded tree counts without early stopping in the core implementation. Control worker and library-thread concurrency.
5. Complete raw/engineered and weighting comparisons within the declared experiment budget.
6. Apply the design's base-model rule: highest mean CV AP; consider candidates within 0.01 absolute AP practically close, then compare CV log loss and simplicity.
7. Fit the selected pipeline on all development rows and preserve frozen reference candidates for final comparison.

### Deliverables

- Full search configuration/results and comparable fold metrics.
- Selected base model with source, feature, split, and environment hashes.
- Written champion/challenger decision and feature-ablation conclusion.
- Saved development-only fitted pipeline.

### Exit gate

The base model is chosen entirely from development evidence. No XGBoost-win requirement is imposed. Search costs are recorded. Saved predictions and metadata identify the exact experiment. The model is not refitted on calibration or policy-validation data.

**Methodological questions:** What did boosting add? What made the comparison fair? Why was the winner selected, including any near tie?

## Week 4 / Phase 4: Calibration, policy simulation, and explanations

**Budget:** 14–18 hours.  
**Question:** Are probabilities useful enough to support explicit decisions?

### Build sequence

1. Fit sigmoid and isotonic calibration mappings on the calibration partition, holding the development-trained base model fixed.
2. Compare raw/sigmoid/isotonic probabilities on policy validation. Select by log loss with the design's 0.005 simplicity tolerance.
3. Produce reliability diagrams with fixed bins/counts, Brier score, and probability-quality comparisons.
4. Implement the synthetic payoff model: nondefault gain 50, default loss 500, processing cost 0 utility units. The analytic acceptance threshold is approximately 0.0909.
5. Compare accept-all/none, low-risk-fraction, 0.5 reference, analytic, and validation-selected cutoff policies.
6. Run the predefined gain/loss sensitivity grid. Select any empirical cutoff only on policy validation.
7. Produce logistic interpretations, SHAP for the development-selected tree candidate, validation error cases, and descriptive slices.
8. Freeze the complete bundle, reference models, calibration choice, scenario configurations, cutoffs, and report definitions.

### Deliverables

- Calibration comparison and selection rationale.
- Tested payoff calculations and policy tables.
- Validation sensitivity report and explanations.
- Versioned champion bundle with preprocessing, calibration, schema, model metadata, and policy configuration.
- Pre-test freeze manifest and independent scientific review.

### Exit gate

Calibration-fit, probability-selection, and test rows are separate. Cost assumptions are explicitly synthetic. No policy is selected on final-test labels. SHAP names its explained model and output scale. The selected bundle and reporting definitions are fixed before final evaluation.

**Methodological questions:** How can a high-AUC model have poor probabilities? What determines the payoff threshold? Why is simulated utility not evidence of actual profit?

## Week 5 / Phase 5: Final evaluation and reproducible delivery

**Budget:** 13–18 hours.  
**Question:** Can another person verify the results and use the saved pipeline?

### Build sequence

1. Review the freeze manifest and perform the frozen final-test evaluation.
2. Report AP, ROC-AUC, log loss, Brier score, confusion/decision metrics, and policy outcomes. Do not reselect the champion from test rankings.
3. Produce paired 95% bootstrap intervals using 1,000 fixed-seed repetitions; resample fingerprint groups when relevant.
4. Implement batch scoring of unlabeled data without fitting or training-database access.
5. Demonstrate monitoring on labeled synthetic mix shifts and separate corruption scenarios; do not claim observed temporal drift.
6. Finish Docker, fixture-based pytest/Ruff checks, and GitHub Actions.
7. Reproduce the core workflow from a fresh environment using the same source version and configuration.
8. Complete README, results report, model card, reproduction guide, and a short walkthrough.

### Deliverables

- Final-test tables and uncertainty estimates.
- Batch scorer, example input/output, and save/load checks.
- Simulated monitoring report.
- CI and documented fresh-environment reproduction.
- Finished portfolio documentation and measured project findings.

### Exit gate

The design's completion checklist passes. All headline numbers link to saved artifacts. Test results are reported honestly, including an unhelpful calibration method, a losing XGBoost model, or an abstain-all winning scenario. Batch counts reconcile. Synthetic scenarios are clearly labeled. No unsupported production/profit/temporal claim appears in the README.

**Methodological questions:** What uncertainty do the intervals cover? What can monitoring establish without labels? Which findings would require new data before real use?

## Reference

Dataset information, attribution, download, and published import instructions: [UCI Default of Credit Card Clients](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients), checked October 6, 2026. Model methods, selection tolerances, partition proportions, costs, and effort estimates follow the project design; they are project decisions rather than UCI requirements.
