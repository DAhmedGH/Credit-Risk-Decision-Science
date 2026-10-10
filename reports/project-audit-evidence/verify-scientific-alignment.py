if not __debug__:
    raise RuntimeError("Run this audit check without Python -O; assertions verify integrity")

import hashlib
from credit_risk.artifacts import json_bytes
from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
from credit_risk.splits.allocation import financial_fingerprint
from credit_risk.models.pipelines import positive_probability

root = Path(__file__).resolve().parents[2]
model = root / "artifacts/models/phase4/9ca62eca2665438c9c97b4889413acfa"
assign = pd.read_csv(root / "artifacts/split_manifest.csv", keep_default_na=False)
financial = pd.read_csv(
    root / "data/processed/financial_features_v1.csv", float_precision="round_trip"
).set_index("client_id")
assert assign.client_id.is_unique and financial.index.is_unique
assert set(assign.client_id) == set(financial.index)
for row in assign.itertuples(index=False):
    assert financial_fingerprint(financial.loc[row.client_id].to_dict()) == row.fingerprint

assert assign.groupby("fingerprint").partition.nunique().max() == 1
assert assign.groupby("fingerprint").fold.nunique().max() == 1
print("financial_profiles_verified", len(assign), "groups", assign.fingerprint.nunique())
shap = np.load(model / "explanations/shap_values.npz")
parts = assign.set_index("client_id").partition
assert all(parts.loc[k] == "development" for k in shap["background_client_id"])
assert all(parts.loc[k] == p for k, p in zip(shap["client_id"], shap["partition"], strict=True))
ids = assign.loc[assign.partition == "development", "client_id"].sort_values().to_numpy()
rng = np.random.default_rng(42)
expected_background = ids[np.sort(rng.choice(len(ids), 100, replace=False))]
expected_sample = ids[np.sort(np.random.default_rng(42).choice(len(ids), 996, replace=False))]
assert np.array_equal(expected_background, shap["background_client_id"])
assert np.array_equal(expected_sample, shap["client_id"][:996])
pipeline = joblib.load(
    model / "accepted_models/xgboost_05_engineered_none/development_pipeline.joblib"
)
transformed = pipeline[:-1].transform(financial.loc[shap["client_id"]])
assert transformed.columns.tolist() == shap["feature_names"].tolist()
assert np.allclose(transformed.to_numpy(), shap["transformed_data"], atol=1e-12, rtol=0)
margin = pipeline.named_steps["model"].estimator_.predict(transformed, output_margin=True)
assert np.array_equal(margin, shap["raw_margin"])
importance = pd.read_csv(model / "explanations/shap_development_importance.csv").set_index(
    "feature"
)
expected_abs = np.abs(shap["values"][:996]).mean(axis=0)
assert np.allclose(
    importance.loc[shap["feature_names"], "mean_absolute_shap_log_odds"],
    expected_abs,
    atol=1e-12,
    rtol=0,
)
print("shap_sample_background_features_model_margin_importance_verified", transformed.shape)
fit = json.loads((model / "calibration_fit_evidence.json").read_text())

for partition, key in [
    ("development", "development"),
    ("calibration", "calibration"),
    ("policy_validation", "policy"),
]:
    ids = assign.loc[assign.partition == partition, "client_id"].sort_values().tolist()
    assert hashlib.sha256(json_bytes(ids)).hexdigest() == fit[key + "_ids_sha256"]
variants = joblib.load(model / "calibration_variants.joblib")
assert variants["sigmoid"].estimator.estimator is variants["raw"]
assert variants["isotonic"].estimator.estimator is variants["raw"]
npz = np.load(model / "policy_predictions.npz")
for name, estimator in variants.items():
    p = positive_probability(estimator, financial.loc[npz["client_id"]])
    assert np.array_equal(p, npz[name])
print("calibration_ids_frozen_base_aliases_mapping_predictions_verified")
