# Public scoring package inventory

The existing scoring command loads the Phase 4 probability bundle through
`verify_freeze`, requiring 106 frozen artifacts, original review binding and
three `completion_source` copies. Those checks protect historical evaluation,
but unnecessarily couple inference to reference models, SHAP samples, review
narratives and historical directory layouts. They remain unchanged.

The public package has a separate `public-scoring-v1` delivery contract. This
inventory was recorded before implementing that loader and packager.

| Distributed member | Source and purpose |
| --- | --- |
| `pipeline.joblib` | Byte-identical accepted `xgboost_05_engineered_none/development_pipeline.joblib`; fitted selection, preprocessing and XGBoost; 148,534 bytes |
| `feature_schema.json` | Unchanged accepted financial-row-v1.1 schema, formulas, allowlist and availability assumptions |
| `policy.json` | Exact projection of accepted base policies and ten sensitivity scenario/policy lists; 88 definitions; excludes selection/evaluation result tables |
| `NOTICE.md` | UCI creator/citation/license link, derivation statement, no endorsement and warranty notice; dependency notice |
| `manifest.json` | New delivery version and content identity; file sizes/hashes, original model/freeze/bundle lineage, class mapping, runtime pins and accepted transformation hashes |

The selected mapping is raw, so the accepted fitted pipeline is also the
probability estimator. No sigmoid/isotonic artifact or reference model is needed.
Original fitted pipeline SHA-256:
`265db2cbe02e88ca7c75c29f39b5c0230a29ba40e4735ea808aea08df4a5e83c`.
The original probability bundle SHA-256 remains
`45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd`;
it identifies scientific provenance, not the new archive bytes.

The installed publication code supplies financial transformations, positive-class
probability mapping, input validation, scoring and policy arithmetic. The public
loader binds the unchanged feature, schema, pipeline and policy modules by hash
and requires the supported Python and inference dependency versions. Models are
loaded only with explicit trust, after manifest, artifact and compatibility checks.

Exclude workbooks, labels, customer records, SHAP samples, reference models,
MLflow stores, environments, caches, configurations, source archives and private
review narratives. Distribution metadata contains no original filesystem paths.
The archive is intended for repository distribution if its measured size remains
small. It has not been published; full historical replay remains a separate
workflow with additional original inputs and source/evidence attachments.
