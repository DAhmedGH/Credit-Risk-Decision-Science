"""Fixed-model explanations and descriptive policy-validation diagnostics.

Only routed development and policy-validation frames enter this module. No model
is fitted here. SHAP explains the accepted tree's raw default log odds, including
its accepted preprocessing; it does not explain a fitted probability mapping.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss

from credit_risk.data.schema import STATUS_COLUMNS, audit_group

SEED = 42
CLASSIFICATION_THRESHOLD = 0.5
CASE_RULES = {
    "correct_default": (1, True, False),
    "correct_nondefault": (0, False, True),
    "missed_default": (1, False, True),
    "false_alarm": (0, True, False),
}


def _validate_probabilities(frame: pd.DataFrame, probabilities: Any) -> np.ndarray:
    p = np.asarray(probabilities, dtype=float)
    if p.shape != (len(frame),) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Probabilities must be finite, aligned, and in [0, 1]")
    if not frame["client_id"].is_unique:
        raise ValueError("Explanation IDs must be unique")
    if not frame["default_next_month"].isin([0, 1]).all():
        raise ValueError("Expected binary default labels with positive class 1")
    return p


def select_diagnostic_cases(frame: pd.DataFrame, probabilities: Any) -> dict[str, Any]:
    """Choose confident 0.5 classification examples; probability ties use lowest ID.

    Defaults/false alarms use highest probability; nondefaults/missed defaults
    use lowest probability. Exactly 0.5 predicts default. Missing categories are
    reported explicitly and never replaced with a different error category.
    """
    p = _validate_probabilities(frame, probabilities)
    candidates = frame[["client_id", "default_next_month"]].reset_index(drop=True).copy()
    candidates["probability"] = p
    candidates["predicted_default"] = p >= CLASSIFICATION_THRESHOLD
    result = {}
    for name, (target, prediction, ascending) in CASE_RULES.items():
        subset = candidates.loc[
            (candidates.default_next_month == target) &
            (candidates.predicted_default == prediction)
        ].sort_values(["probability", "client_id"], ascending=[ascending, True])
        if subset.empty:
            result[name] = {"available": False}
        else:
            row = subset.iloc[0]
            result[name] = {
                "available": True, "client_id": int(row.client_id),
                "default_next_month": int(row.default_next_month),
                "probability": float(row.probability),
                "predicted_default": int(row.predicted_default),
            }
    return result


def logistic_interpretation(pipeline: Any) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return per-training-SD numeric slopes and identified categorical contrasts.

    Accepted OHE keeps every category. Individual category coefficients are not
    reference contrasts; subtract the first learned category's coefficient.
    Numeric indicator slopes also use their fitted training standard deviation.
    """
    model = pipeline.named_steps["model"]
    if list(model.classes_) != [0, 1]:
        raise ValueError("Logistic explanation requires class order [0, 1]")
    preprocessor = pipeline.named_steps["preprocessor"]
    names = preprocessor.get_feature_names_out().tolist()
    coefficients = np.asarray(model.coef_)[0]
    if len(names) != len(coefficients):
        raise ValueError("Coefficient and transformed feature dimensions differ")
    numeric = list(preprocessor.transformers_[0][2])
    scaler = preprocessor.named_transformers_["numeric"].named_steps["scaler"]
    numeric_rows = [{
        "feature": feature, "transformed_feature": names[index],
        "coefficient_per_training_sd": float(coefficients[index]),
        "training_mean_after_imputation": float(scaler.mean_[index]),
        "training_sd": float(np.sqrt(scaler.var_[index])),
        "odds_multiplier_per_training_sd": float(np.exp(coefficients[index])),
        "constant_training_feature": bool(scaler.var_[index] == 0),
    } for index, feature in enumerate(numeric)]
    encoder = preprocessor.named_transformers_["categorical"].named_steps["encoder"]
    if encoder.drop is not None:
        raise ValueError("Accepted logistic explanation expects full one-hot encoding")
    categorical_rows = []
    offset = len(numeric)
    categorical = list(preprocessor.transformers_[1][2])
    for feature, categories in zip(categorical, encoder.categories_, strict=True):
        reference = float(categories[0])
        reference_coefficient = float(coefficients[offset])
        for index, category in enumerate(categories):
            contrast = float(coefficients[offset + index] - reference_coefficient)
            categorical_rows.append({
                "feature": feature, "category": float(category),
                "reference_category": reference,
                "transformed_feature": names[offset + index],
                "coefficient": float(coefficients[offset + index]),
                "log_odds_contrast": contrast, "odds_multiplier_vs_reference": float(np.exp(contrast)),
            })
        offset += len(categories)
    return pd.DataFrame(numeric_rows), pd.DataFrame(categorical_rows), {
        "output_scale": "default log odds", "positive_class": 1,
        "intercept": float(model.intercept_[0]),
        "numeric_scale": "one development-training standard deviation after median imputation",
        "category_reference_rule": "first (lowest) fitted category, explicit coefficient difference",
        "interpretation": "conditional associations in a regularized fitted model; not causal effects",
    }


def utilization_band_definition(development: pd.DataFrame) -> dict[str, Any]:
    """Learn fixed quartile edges on development only, preserving signed values."""
    values = development["latest_utilization_proxy"].to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        raise ValueError("No finite development utilization values")
    return {
        "feature": "latest_utilization_proxy", "fit_partition": "development",
        "minimum": float(finite.min()), "maximum": float(finite.max()),
        "quartiles": [float(value) for value in np.quantile(finite, [0.25, 0.5, 0.75])],
        "tie_rule": "cutpoint values go to the higher band; duplicate quartiles may yield empty bands",
        "overflow_rule": "explicit below_development_min/above_development_max; nonfinite missing",
    }


def utilization_bands(values: Any, definition: dict[str, Any]) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    bands = np.asarray(["missing"] * len(values), dtype=object)
    finite = np.isfinite(values)
    indices = np.searchsorted(definition["quartiles"], values[finite], side="right")
    bands[finite] = np.asarray([f"quartile_{index + 1}" for index in indices])
    bands[finite & (values < definition["minimum"])] = "below_development_min"
    bands[finite & (values > definition["maximum"])] = "above_development_max"
    return bands


def _slice_rows(attribute: str, groups: Any, labels: np.ndarray, p: np.ndarray,
                suppress: bool) -> list[dict[str, Any]]:
    rows = []
    groups = np.asarray(groups, dtype=object)
    for group in sorted(set(groups)):
        mask = groups == group
        y, q = labels[mask], p[mask]
        n = len(y)
        defaults, nondefaults = int(sum(y == 1)), int(sum(y == 0))
        supported = n >= 100 and defaults >= 20 and nondefaults >= 20
        suppressed = suppress and not supported
        predicted = q >= CLASSIFICATION_THRESHOLD
        row = {
            "attribute": attribute, "group": str(group), "n": n,
            "default_count": defaults, "nondefault_count": nondefaults,
            "suppressed": suppressed,
            "suppression_reason": "n<100 or defaults<20 or nondefaults<20" if suppressed else "",
            "target_prevalence": None, "mean_predicted_risk": None, "recall": None,
            "false_positive_rate": None, "mean_risk_minus_prevalence": None,
            "brier": None, "log_loss": None,
        }
        if not suppressed:
            row.update({
                "target_prevalence": float(y.mean()), "mean_predicted_risk": float(q.mean()),
                "recall": float(predicted[y == 1].mean()) if defaults else None,
                "false_positive_rate": float(predicted[y == 0].mean()) if nondefaults else None,
                "mean_risk_minus_prevalence": float(q.mean() - y.mean()),
                "brier": float(brier_score_loss(y, q)),
                "log_loss": float(log_loss(y, q, labels=[0, 1])),
            })
        rows.append(row)
    return rows


def descriptive_slices(development: pd.DataFrame, validation: pd.DataFrame,
                       probabilities: Any) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Descriptive diagnostics at 0.5, separate from payoff acceptance decisions."""
    p = _validate_probabilities(validation, probabilities)
    y = validation.default_next_month.to_numpy(dtype=int)
    definition = utilization_band_definition(development)
    status = validation[list(STATUS_COLUMNS)].to_numpy(dtype=float)
    delinquency = np.full(len(validation), "no_positive_delay", dtype=object)
    delinquency[(status > 0).any(axis=1)] = "any_positive_delay"
    delinquency[~np.isfinite(status).all(axis=1)] = "missing_history"
    behavioral = _slice_rows("delinquency_history", delinquency, y, p, False)
    behavioral += _slice_rows("latest_utilization_proxy",
                              utilization_bands(validation.latest_utilization_proxy, definition),
                              y, p, False)
    demographic = []
    for column in ("sex", "education", "marriage"):
        groups = [audit_group(column, value) for value in validation[column]]
        demographic += _slice_rows(column, groups, y, p, True)
    age = validation.age.to_numpy(dtype=float)
    age_groups = np.full(len(age), "unknown", dtype=object)
    age_groups[np.isfinite(age) & (age < 30)] = "under_30"
    age_groups[np.isfinite(age) & (age >= 30) & (age < 40)] = "30_to_39"
    age_groups[np.isfinite(age) & (age >= 40) & (age < 50)] = "40_to_49"
    age_groups[np.isfinite(age) & (age >= 50)] = "50_plus"
    demographic += _slice_rows("age_band", age_groups, y, p, True)
    return pd.DataFrame(behavioral), pd.DataFrame(demographic), {
        "utilization_bands": definition, "partition": "policy_validation",
        "classification_rule": "predicted default iff chosen probability >= 0.5",
        "recall_definition": "predicted defaults / observed defaults",
        "false_positive_rate_definition": "predicted defaults / observed nondefaults",
        "calibration_summary": "mean predicted risk minus observed prevalence (calibration in the large)",
        "demographic_support": {"minimum_n": 100, "minimum_each_class": 20},
        "suppressed_fields": "all rates and probability summaries; retain counts",
        "age_bands": ["under_30", "30_to_39", "40_to_49", "50_plus", "unknown"],
        "limitations": "historical descriptive associations; neither fairness nor causal evidence",
    }


def _sample_rows(frame: pd.DataFrame, count: int, seed: int = SEED) -> pd.DataFrame:
    ordered = frame.sort_values("client_id").reset_index(drop=True)
    indices = np.random.default_rng(seed).choice(len(ordered), min(count, len(ordered)), replace=False)
    return ordered.iloc[np.sort(indices)].copy()


def verify_shap_additivity(values: Any, expected_value: float, raw_margins: Any,
                          transformed_shape: tuple[int, int]) -> float:
    """Reject shape/nonfinite failures or contributions on the wrong output scale."""
    values = np.asarray(values, dtype=float)
    margins = np.asarray(raw_margins, dtype=float)
    if values.shape != transformed_shape or margins.shape != (transformed_shape[0],):
        raise ValueError("Unexpected SHAP shape for the selected binary XGBoost model")
    if not np.isfinite(values).all() or not np.isfinite(margins).all() or not np.isfinite(
        expected_value
    ):
        raise ValueError("SHAP values, base value and margins must be finite")
    sums = values.sum(axis=1) + expected_value
    if not np.allclose(sums, margins, atol=1e-5, rtol=1e-5):
        raise ValueError("SHAP contributions do not reconstruct the accepted raw margin")
    return float(np.abs(sums - margins).max())


def run_descriptive_analysis(logistic: Any, development: pd.DataFrame,
                             policy_validation: pd.DataFrame, chosen_probability: Any,
                             output_dir: str | Path, *, reference_identity: str | None = None
                             ) -> dict[str, Any]:
    """Write non-SHAP diagnostic evidence independently of optional plot packages."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    if not development.client_id.is_unique or not policy_validation.client_id.is_unique:
        raise ValueError("Explanation partition IDs must be unique")
    if set(development.client_id) & set(policy_validation.client_id):
        raise ValueError("Development and policy-validation IDs overlap")
    cases = select_diagnostic_cases(policy_validation, chosen_probability)
    numeric, categorical, logistic_metadata = logistic_interpretation(logistic)
    numeric.to_csv(destination / "logistic_numeric_coefficients.csv", index=False)
    categorical.to_csv(destination / "logistic_categorical_contrasts.csv", index=False)
    logistic_metadata["reference_identity"] = reference_identity
    behavior, demographic, slice_metadata = descriptive_slices(
        development, policy_validation, chosen_probability)
    behavior.to_csv(destination / "behavioral_slices.csv", index=False)
    demographic.to_csv(destination / "demographic_audit.csv", index=False)
    metadata = {
        "logistic": logistic_metadata, "slices": slice_metadata,
        "diagnostic_cases": cases,
        "case_selection_rule": "0.5 classification; highest p for correct default/false alarm, lowest p for correct nondefault/missed default; ties lowest client_id",
        "artifacts": ["logistic_numeric_coefficients.csv", "logistic_categorical_contrasts.csv",
                      "behavioral_slices.csv", "demographic_audit.csv", "descriptive_metadata.json"],
    }
    (destination / "descriptive_metadata.json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n")
    return metadata


def run_explanations(base: Any, logistic: Any, development: pd.DataFrame,
                     policy_validation: pd.DataFrame, chosen_probability: Any,
                     output_dir: str | Path, *, selected_model_identity: str | None = None,
                     reference_identity: str | None = None) -> dict[str, Any]:
    """Write fixed-model explanation artifacts; never fit or reselect a model."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    descriptive = run_descriptive_analysis(
        logistic, development, policy_validation, chosen_probability, destination,
        reference_identity=reference_identity)
    cases = descriptive["diagnostic_cases"]

    background = _sample_rows(development, 100)
    explained_development = _sample_rows(development, 996)
    available_cases = {name: record for name, record in cases.items() if record["available"]}
    case_ids = [record["client_id"] for record in available_cases.values()]
    local = policy_validation.set_index("client_id", drop=False).loc[case_ids].reset_index(drop=True)
    explanation_rows = pd.concat([explained_development, local], ignore_index=True)
    preprocessor = base[:-1]
    transformed_background = preprocessor.transform(background)
    transformed = preprocessor.transform(explanation_rows)
    feature_names = transformed.columns.tolist()
    estimator = base.named_steps["model"].estimator_
    if list(estimator.classes_) != [0, 1]:
        raise ValueError("SHAP default log odds require class mapping [0, 1]")
    explainer = shap.TreeExplainer(
        estimator, data=transformed_background, feature_perturbation="interventional",
        model_output="raw", feature_names=feature_names)
    values = np.asarray(explainer.shap_values(transformed, check_additivity=True), dtype=float)
    expected_value = float(np.asarray(explainer.expected_value).reshape(-1)[0])
    margins = np.asarray(estimator.predict(transformed, output_margin=True), dtype=float)
    maximum_residual = verify_shap_additivity(values, expected_value, margins, transformed.shape)
    n_dev = len(explained_development)
    importance = np.abs(values[:n_dev]).mean(axis=0)
    order = sorted(range(len(feature_names)), key=lambda i: (-importance[i], feature_names[i]))
    dependence_indices = order[:2]
    pd.DataFrame({"feature": feature_names, "mean_absolute_shap_log_odds": importance}).sort_values(
        ["mean_absolute_shap_log_odds", "feature"], ascending=[False, True]).to_csv(
            destination / "shap_development_importance.csv", index=False)
    np.savez_compressed(
        destination / "shap_values.npz", values=values, expected_value=expected_value,
        transformed_data=transformed.to_numpy(), raw_margin=margins,
        client_id=explanation_rows.client_id.to_numpy(dtype=np.int64),
        feature_names=np.asarray(feature_names, dtype=str),
        partition=np.asarray(["development"] * n_dev + ["policy_validation"] * len(local)),
        background_client_id=background.client_id.to_numpy(dtype=np.int64))

    plt.figure()
    shap.summary_plot(values[:n_dev], transformed.iloc[:n_dev], feature_names=feature_names,
                      show=False, max_display=20)
    plt.title("Development SHAP: selected XGBoost default log odds")
    plt.tight_layout()
    plt.savefig(destination / "shap_global.png", dpi=140, bbox_inches="tight")
    plt.close("all")
    for rank, feature_index in enumerate(dependence_indices, 1):
        # No automatic interaction choice that might use validation cases.
        shap.dependence_plot(feature_index, values[:n_dev], transformed.iloc[:n_dev],
                             feature_names=feature_names, interaction_index=None, show=False)
        plt.title(f"Development dependence: {feature_names[feature_index]} (raw log odds)")
        plt.tight_layout()
        plt.savefig(destination / f"shap_dependence_{rank}.png", dpi=140, bbox_inches="tight")
        plt.close("all")
    for index, name in enumerate(available_cases):
        row_index = n_dev + index
        explanation = shap.Explanation(values=values[row_index], base_values=expected_value,
                                       data=transformed.iloc[row_index].to_numpy(),
                                       feature_names=feature_names)
        shap.plots.waterfall(explanation, max_display=12, show=False)
        plt.title(f"{name}: ID {case_ids[index]}; raw default log odds")
        plt.tight_layout()
        plt.savefig(destination / f"shap_local_{name}.png", dpi=140, bbox_inches="tight")
        plt.close("all")

    metadata = {
        **descriptive,
        "shap": {
            "model_identity": selected_model_identity, "shap_version": shap.__version__,
            "output_scale": "raw default log odds", "model_output": "raw",
            "feature_perturbation": "interventional", "check_additivity": True,
            "seed": SEED, "background_partition": "development",
            "background_client_ids": [int(value) for value in background.client_id],
            "development_client_ids": [int(value) for value in explained_development.client_id],
            "policy_validation_client_ids": case_ids,
            "explained_row_count": len(explanation_rows), "feature_names": feature_names,
            "expected_raw_log_odds": expected_value,
            "maximum_absolute_additivity_residual": maximum_residual,
            "dependence_features": [feature_names[index] for index in dependence_indices],
            "dependence_selection": "top two mean absolute SHAP values on fixed development sample; feature name tie break",
            "limitations": "Correlated histories may share attribution. SHAP is not causal and raw-tree values do not explain the chosen probability mapping.",
        },
        "artifacts": sorted(path.name for path in destination.iterdir() if path.is_file()),
    }
    (destination / "metadata.json").write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n")
    return metadata
