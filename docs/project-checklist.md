# Project acceptance checklist

The checklist applies to the accepted frozen historical benchmark. Unknown original source-download chain, absent temporal/external validation and unobserved remote CI are disclosed limitations. Source attribution/checksum/schema documentation is qualified rather than invented. Local CI-equivalent and fresh-container execution provide the observed delivery checks.

| Design requirement | Evidence | Gate |
| --- | --- | --- |
| Source, attribution, checksum, schema documented | artifacts/source_manifest.json; docs/data-contract.md; supplied-workbook qualification | PASS |
| Existing-account next-month task/availability | docs/model-card.md; docs/leakage-audit.md | PASS |
| Source/curated/rejected/export counts reconcile | reports/database_reconciliation.json; reproduction_receipt.json:30000/30000/0/30000 | PASS |
| ID/target/audit columns excluded | feature_contract_v1_1.json; fixture schema rejection tests | PASS |
| Four partitions/five folds frozen/disjoint | split_manifest.csv; original/split reproduction SHA775f9862... | PASS |
| Learned preprocessing fit-only | earlier leakage sentinel tests; frozen source/reference identities | PASS |
| Dummy/logistic/forest/XGBoost evaluated | reports/phase5/models.csv;6 frozen rows | PASS |
| Bounded search/feature ablation | reports/phase3.md;48 configs/240 search fits;24 matched contrasts | PASS |
| Declared development selection | reports/phase3.md; selected100-tree model unchanged | PASS |
| Separate calibration fit/selection | reports/phase4.md;4500 calibration/3000 PV | PASS |
| Payoffs/policies/ties frozen before test | Phase 4 complete manifest; readiness/exposure receipts;88 rows | PASS |
| Honest final metrics/paired uncertainty | reports/phase5/results.json;1000 paired clusters;341 statistics independently reproduced | PASS |
| SHAP exact model/scale and noncausal scope | Phase 4 explanations/review; raw log odds;100 background rows | PASS |
| Hypothetical utility and sensitivity | all 88 policies; abstain-all retained; reports/results.md | PASS |
| Synthetic monitoring with no temporal claim | docs/monitoring-report.md;6 scenarios;198 distributions | PASS |
| Unlabeled saved bundle without fit/DB | batch_receipt.json;12/12; network-disabled container; quarantine tests | PASS |
| Behavioral tests, CI and fresh container |207 local SQL checks;206 container fixtures+SQL skip; configured Actions; fresh core exact evidence; remote CI unobserved | PASS (local evidence) |
| Portfolio/docs complete | README; results/model card/leakage/monitoring/walkthrough/reproduction | PASS |
| Durable acquisition/restoration | artifact_delivery.json; archive exact hash; restoration_check | PASS |

All design requirements pass on the recorded evidence. Independent scientific/code/report review is PASS; all 174 restored payload hashes and byte-exact standalone scoring were verified. Original acceptance/provenance is preserved in historical receipts; the public reports summarize their findings. Remote CI remains unobserved, with local fixture/SQL/container execution reported explicitly. No minimum AUC, XGBoost-win or profit criterion is used.
