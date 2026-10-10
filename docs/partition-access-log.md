

This is a presentation copy of the access record. Original dated evidence is
preserved privately; wording edits do not change access times, scopes or outcomes.
## Phase 4 acceptance review — 2026-10-09T16:39:10 UTC

Permitted access: saved calibration/policy-validation and SHAP artifacts, trusted
models and input hashes, label-free assignments, and financial values for the
100 development background IDs and 996 development explanation IDs only.
Route customer IDs before converting financial values. Technical review may check
all saved raw margins and additivity and recompute TreeSHAP for 14 fixed rows.
No fits, raw label CSV decoding, final-test outcome/value interpretation or
Phase 5 work is permitted. This record precedes the new financial-value review.

```json
{
  "utc": "2026-10-09T16:03:32.613056+00:00",
  "stage": "calibration and policy simulation",
  "permitted": {
    "development": "background/explanations; base never fitted",
    "calibration": "fit mappings only",
    "policy_validation": "mapping/policy selection and descriptions",
    "final_test": "assignment IDs and byte hashes only"
  },
  "routing": "Full CSV row strings traversed; route by ID before numeric/outcome conversion",
  "final_test_outcomes_interpreted": false,
  "input_hashes": {
    "artifacts/feature_contract_v1_1.json": "4adb6745e582e551239b9e999d0128649fdaff0b1f63deebfea6f538ecc2eeae",
    "artifacts/phase1_export_manifest.json": "6157949db2e77b548d7de831f196b5d6506bd9c8e28dc3bd6290401f2be0e81a",
    "artifacts/split_checks/840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537.json": "840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537",
    "artifacts/split_manifest.csv": "775f9862fb5b97095c81fdae440d4acb7fd52f692a216b6284e879db5e4d5e4c",
    "data/processed/financial_features_v1.csv": "4dc8498776fbe56b64d75ff3cd79257275ad7657cc133aaa08457b27c1cc6e7e",
    "data/processed/labels.csv": "ecb12689643cb256d1707338f695d22fe8c28bce70c985f7c2fd6247e8080f2f",
    "data/raw/default of credit card clients.xls": "30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933",
    "data/processed/audit_attributes.csv": "54f7869afe47e2a65e138fcf71b5ab0f69c60e7413875b76498e6df82a1f3204"
  },
  "accepted_selection_manifest_sha256": "17239cecdbc8754cdd6cdef129d550385f62dc591dc0218ddb08fffb0d06f0fb",
  "accepted_code_tree_sha256": "bcad5c99614b24044c72f904ce1a73c2552d82528b50d90679478cec3f50a44f",
  "accepted_lock_sha256": "31e7241f3499567f92579f1381892351dcd433faf219fe8b0be70321937e6b57",
  "model_sha256": {
    "dummy_prior": "cf92e3a562ba1ecd4f591b44e85ddbeec678f29f00b4e368576a8799a98b185d",
    "logistic_00_engineered_none": "0f0e88ef743f82a48d7198b6c35b9f45cab54887a584b760ce00d2776c817e0e",
    "random_forest_02_engineered_none": "fcc1f8123934f005a1caf4ab553db63df52111f5a5aa1a030b090d497ad7158e",
    "xgboost_04_engineered_none": "4d0bbdfc3968d932d19fac801757ef23ed59407dbdf9b1560773888b563f2198",
    "xgboost_05_engineered_none": "265db2cbe02e88ca7c75c29f39b5c0230a29ba40e4735ea808aea08df4a5e83c"
  },
  "partition_sizes": {
    "development": 18000,
    "calibration": 4500,
    "policy_validation": 3000,
    "final_test": 4500
  },
  "selection_run": "6a0725d18b164582938e0b07b2df6b27",
  "selected_candidate": "xgboost_05_engineered_none",
  "durable_model_root": "/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime"
}
```

```json
{
  "utc": "2026-10-09T16:07:16.590602+00:00",
  "stage": "resume explanations (zero mapping/base fits)",
  "permitted": {
    "development": "background/explanations; base never fitted",
    "calibration": "fit mappings only",
    "policy_validation": "mapping/policy selection and descriptions",
    "final_test": "assignment IDs and byte hashes only"
  },
  "routing": "Full CSV row strings traversed; route by ID before numeric/outcome conversion",
  "final_test_outcomes_interpreted": false,
  "input_hashes": {
    "artifacts/feature_contract_v1_1.json": "4adb6745e582e551239b9e999d0128649fdaff0b1f63deebfea6f538ecc2eeae",
    "artifacts/phase1_export_manifest.json": "6157949db2e77b548d7de831f196b5d6506bd9c8e28dc3bd6290401f2be0e81a",
    "artifacts/split_checks/840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537.json": "840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537",
    "artifacts/split_manifest.csv": "775f9862fb5b97095c81fdae440d4acb7fd52f692a216b6284e879db5e4d5e4c",
    "data/processed/financial_features_v1.csv": "4dc8498776fbe56b64d75ff3cd79257275ad7657cc133aaa08457b27c1cc6e7e",
    "data/processed/labels.csv": "ecb12689643cb256d1707338f695d22fe8c28bce70c985f7c2fd6247e8080f2f",
    "data/raw/default of credit card clients.xls": "30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933",
    "data/processed/audit_attributes.csv": "54f7869afe47e2a65e138fcf71b5ab0f69c60e7413875b76498e6df82a1f3204"
  },
  "accepted_selection_manifest_sha256": "17239cecdbc8754cdd6cdef129d550385f62dc591dc0218ddb08fffb0d06f0fb",
  "accepted_code_tree_sha256": "bcad5c99614b24044c72f904ce1a73c2552d82528b50d90679478cec3f50a44f",
  "accepted_lock_sha256": "31e7241f3499567f92579f1381892351dcd433faf219fe8b0be70321937e6b57",
  "model_sha256": {
    "dummy_prior": "cf92e3a562ba1ecd4f591b44e85ddbeec678f29f00b4e368576a8799a98b185d",
    "logistic_00_engineered_none": "0f0e88ef743f82a48d7198b6c35b9f45cab54887a584b760ce00d2776c817e0e",
    "random_forest_02_engineered_none": "fcc1f8123934f005a1caf4ab553db63df52111f5a5aa1a030b090d497ad7158e",
    "xgboost_04_engineered_none": "4d0bbdfc3968d932d19fac801757ef23ed59407dbdf9b1560773888b563f2198",
    "xgboost_05_engineered_none": "265db2cbe02e88ca7c75c29f39b5c0230a29ba40e4735ea808aea08df4a5e83c"
  },
  "partition_sizes": {
    "development": 18000,
    "calibration": 4500,
    "policy_validation": 3000,
    "final_test": 4500
  },
  "selection_run": "6a0725d18b164582938e0b07b2df6b27",
  "selected_candidate": "xgboost_05_engineered_none",
  "durable_model_root": "/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime"
}
```

```json
{
  "utc": "2026-10-09T16:10:09.422813+00:00",
  "stage": "resume explanations (zero mapping/base fits)",
  "permitted": {
    "development": "background/explanations; base never fitted",
    "calibration": "fit mappings only",
    "policy_validation": "mapping/policy selection and descriptions",
    "final_test": "assignment IDs and byte hashes only"
  },
  "routing": "Full CSV row strings traversed; route by ID before numeric/outcome conversion",
  "final_test_outcomes_interpreted": false,
  "input_hashes": {
    "artifacts/feature_contract_v1_1.json": "4adb6745e582e551239b9e999d0128649fdaff0b1f63deebfea6f538ecc2eeae",
    "artifacts/phase1_export_manifest.json": "6157949db2e77b548d7de831f196b5d6506bd9c8e28dc3bd6290401f2be0e81a",
    "artifacts/split_checks/840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537.json": "840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537",
    "artifacts/split_manifest.csv": "775f9862fb5b97095c81fdae440d4acb7fd52f692a216b6284e879db5e4d5e4c",
    "data/processed/financial_features_v1.csv": "4dc8498776fbe56b64d75ff3cd79257275ad7657cc133aaa08457b27c1cc6e7e",
    "data/processed/labels.csv": "ecb12689643cb256d1707338f695d22fe8c28bce70c985f7c2fd6247e8080f2f",
    "data/raw/default of credit card clients.xls": "30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933",
    "data/processed/audit_attributes.csv": "54f7869afe47e2a65e138fcf71b5ab0f69c60e7413875b76498e6df82a1f3204"
  },
  "accepted_selection_manifest_sha256": "17239cecdbc8754cdd6cdef129d550385f62dc591dc0218ddb08fffb0d06f0fb",
  "accepted_code_tree_sha256": "bcad5c99614b24044c72f904ce1a73c2552d82528b50d90679478cec3f50a44f",
  "accepted_lock_sha256": "31e7241f3499567f92579f1381892351dcd433faf219fe8b0be70321937e6b57",
  "model_sha256": {
    "dummy_prior": "cf92e3a562ba1ecd4f591b44e85ddbeec678f29f00b4e368576a8799a98b185d",
    "logistic_00_engineered_none": "0f0e88ef743f82a48d7198b6c35b9f45cab54887a584b760ce00d2776c817e0e",
    "random_forest_02_engineered_none": "fcc1f8123934f005a1caf4ab553db63df52111f5a5aa1a030b090d497ad7158e",
    "xgboost_04_engineered_none": "4d0bbdfc3968d932d19fac801757ef23ed59407dbdf9b1560773888b563f2198",
    "xgboost_05_engineered_none": "265db2cbe02e88ca7c75c29f39b5c0230a29ba40e4735ea808aea08df4a5e83c"
  },
  "partition_sizes": {
    "development": 18000,
    "calibration": 4500,
    "policy_validation": 3000,
    "final_test": 4500
  },
  "selection_run": "6a0725d18b164582938e0b07b2df6b27",
  "selected_candidate": "xgboost_05_engineered_none",
  "durable_model_root": "/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime"
}
```

## Independent Phase 4 review, October 9, 2026 (initial blocked checkpoint)

Reviewed saved policy-validation predictions/outcomes, allowed development/PV
explanation artifacts, label-free assignments, accepted fitted models and hashes.
No raw label CSV or final-test outcome was opened by this review; zero real fits.
Exact individual review invocation timestamps were not retained. See
`docs/validation-phase4-blocked.md` for inspected paths and recomputed evidence.

```json
{
  "utc": "2026-10-09T16:29:26.906188+00:00",
  "stage": "resume explanations (zero mapping/base fits)",
  "permitted": {
    "development": "background/explanations; base never fitted",
    "calibration": "fit mappings only",
    "policy_validation": "mapping/policy selection and descriptions",
    "final_test": "assignment IDs and byte hashes only"
  },
  "routing": "Full CSV row strings traversed; route by ID before numeric/outcome conversion",
  "final_test_outcomes_interpreted": false,
  "input_hashes": {
    "artifacts/feature_contract_v1_1.json": "4adb6745e582e551239b9e999d0128649fdaff0b1f63deebfea6f538ecc2eeae",
    "artifacts/phase1_export_manifest.json": "6157949db2e77b548d7de831f196b5d6506bd9c8e28dc3bd6290401f2be0e81a",
    "artifacts/split_checks/840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537.json": "840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537",
    "artifacts/split_manifest.csv": "775f9862fb5b97095c81fdae440d4acb7fd52f692a216b6284e879db5e4d5e4c",
    "data/processed/financial_features_v1.csv": "4dc8498776fbe56b64d75ff3cd79257275ad7657cc133aaa08457b27c1cc6e7e",
    "data/processed/labels.csv": "ecb12689643cb256d1707338f695d22fe8c28bce70c985f7c2fd6247e8080f2f",
    "data/raw/default of credit card clients.xls": "30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933",
    "data/processed/audit_attributes.csv": "54f7869afe47e2a65e138fcf71b5ab0f69c60e7413875b76498e6df82a1f3204"
  },
  "accepted_selection_manifest_sha256": "17239cecdbc8754cdd6cdef129d550385f62dc591dc0218ddb08fffb0d06f0fb",
  "accepted_code_tree_sha256": "bcad5c99614b24044c72f904ce1a73c2552d82528b50d90679478cec3f50a44f",
  "accepted_lock_sha256": "31e7241f3499567f92579f1381892351dcd433faf219fe8b0be70321937e6b57",
  "model_sha256": {
    "dummy_prior": "cf92e3a562ba1ecd4f591b44e85ddbeec678f29f00b4e368576a8799a98b185d",
    "logistic_00_engineered_none": "0f0e88ef743f82a48d7198b6c35b9f45cab54887a584b760ce00d2776c817e0e",
    "random_forest_02_engineered_none": "fcc1f8123934f005a1caf4ab553db63df52111f5a5aa1a030b090d497ad7158e",
    "xgboost_04_engineered_none": "4d0bbdfc3968d932d19fac801757ef23ed59407dbdf9b1560773888b563f2198",
    "xgboost_05_engineered_none": "265db2cbe02e88ca7c75c29f39b5c0230a29ba40e4735ea808aea08df4a5e83c"
  },
  "partition_sizes": {
    "development": 18000,
    "calibration": 4500,
    "policy_validation": 3000,
    "final_test": 4500
  },
  "selection_run": "6a0725d18b164582938e0b07b2df6b27",
  "selected_candidate": "xgboost_05_engineered_none",
  "durable_model_root": "/home/danieal/credit-risk-backups/phase3-20261008-195946/runtime"
}
```


## Completed Phase 4 acceptance — 2026-10-09T16:57:32.920585+00:00

Independent review used saved allowed-partition artifacts and 1,089 unique selected
development financial records only, as scoped before access. Finalization/loading
use no outcomes. Complete freeze `89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b` passes with 106 hashed files. Review
receipt reports/phase4_review_receipt.json. No final-test interpretation/evaluation
or Phase 5 work; no fits during acceptance. Reported WSL smoke/tests/resume retain
separate attribution in reports/phase4_user_verification.json.

## Post-seal verification and operational incident, October 9, 2026

Guarded loading used frozen models/manifests without outcomes. A documentation-
shell quoting failure unintentionally started bootstrap integrity checks;
the stage byte-hashed accepted inputs and read label-free assignments/models,
then failed at report writing before any routing, installation, smoke, fitting
or test. D022 records the stopped attempt. Independent rechecks confirm all
106 artifact hashes, source, lock and review identities unchanged.
No final-test financial values/outcomes were interpreted or evaluated.
