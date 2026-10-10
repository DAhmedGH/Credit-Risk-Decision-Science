# Credit Risk & Lending Decision Science

Estimate next-month default risk for existing credit-card accounts using UCI Default of Credit Card Clients (30,000 historical Taiwan snapshots, April–September 2005). This is a reproducible modeling study with hypothetical allocation policies.

- Frozen test AP **0.5642 [0.5338–0.5958]**, versus **0.2213** for the prior baseline; ROC-AUC **0.7940 [0.7776–0.8096]**. The forest's AP is slightly higher, 0.5664; the development-selected XGBoost stays frozen.
- Held-out policy-validation calibration did not improve log loss: **raw 0.4330**, sigmoid 0.4362, isotonic 0.4560. Raw probabilities were retained.
- The fixed empirical policy accepts **22.84%** of test accounts, with **5.35%** accepted default rate. Benchmark utility is **4.70 [2.90–6.37] units/customer** under explicitly synthetic gain 50/loss 500/cost 0 assumptions. These are dimensionless simulations, not actual profit or causal effects.

[Full results and figures](reports/results.md) · [Model card](docs/model-card.md) · [Reproduce and score](docs/reproduction-phase5.md) · [Synthetic monitoring](docs/monitoring-report.md) · [Walkthrough](docs/walkthrough.md)

[Completed-project audit](reports/project-audit.md) documents verified evidence,
software corrections, regression checks and remaining limitations. Accepted
scientific artifacts are preserved; exact historical replay uses the preserved private
accepted-source archive.

Four frozen group-disjoint partitions (60/15/10/15), five development folds, fold-fitted preprocessing, bounded logistic/forest/XGBoost searches, calibration separation and 1,000 paired fingerprint-group bootstrap repetitions protect the scientific sequence. The exact saved bundle scores unlabeled CSV/Parquet inputs without fitting or a training database.

The workbook was supplied locally; its checksum/schema are documented, but the original official ZIP/download chain and retrieval time are unknown. Attribution: Yeh, I. (2009), UCI Machine Learning Repository, DOI 10.24432/C55S3H, CC BY 4.0. [Source evidence](artifacts/source_manifest.json).

There is no temporal/external validation, validated new-applicant underwriting, contemporary Canadian population claim, production deployment or fairness certification. Demographics are audit-only; exclusion does not remove proxies. Uncertainty is conditional on fitted models.

```bash
# Existing isolated Python 3.12 environment; exact restored bundle required.
.venv/bin/python -m credit_risk.phase5 score \
  --input examples/scoring_batch.csv --output artifacts/runtime/my_batch
```

The example is synthetic and unlabeled. For a fresh environment, Docker, trusted artifact restoration, checks and evidence-only reporting, follow the [Phase 5 reproduction guide](docs/reproduction-phase5.md). Raw data, credentials, tracking stores and large binaries stay outside Git. Selected compact evidence is versioned; original execution attachments remain private. A source-only clone supports fixture checks. Frozen scoring additionally requires the trusted private payload; no public model download is provided.
