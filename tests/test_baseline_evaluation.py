"""Synthetic integration checks; no dataset acquisition or real-model searches."""

# ruff: noqa: E402
import json

import pytest

pytest.importorskip("sklearn", reason="Phase 2 model runtime not installed")

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from credit_risk.artifacts import read_csv
from credit_risk.features import build_features
from credit_risk.models.evaluation import _jsonable, evaluate_variant, probability_metrics, summarize_oof
from credit_risk.models.pipelines import build_pipeline
from credit_risk.models.inputs import validate_oof
from credit_risk.phase2 import comparisons
from credit_risk.splits import allocate_records
from fixtures.records import make_records


@pytest.fixture
def development():
    source = make_records(200)
    assignments, _ = allocate_records(source, "a" * 64)
    selected = {row["client_id"]: row for row in assignments if row["partition"] == "development"}
    return [{"client_id": row["client_id"], "fold": selected[row["client_id"]]["fold"],
             "fingerprint": selected[row["client_id"]]["fingerprint"],
             "default_next_month": row["default_next_month"], **build_features(row)}
            for row in source if row["client_id"] in selected]


@pytest.mark.parametrize("model,weighting", [("dummy", "none"), ("logistic", "balanced"),
                                           ("random_forest", "balanced")])
def test_five_fold_workflow_reconciles_saved_predictions(development, model, weighting, tmp_path):
    params = {"n_estimators": 3} if model == "random_forest" else {}
    output = tmp_path / model
    summary, folds = evaluate_variant(development, model, "engineered", weighting, 42, params, output)
    predictions = read_csv(output / "oof_predictions.csv")
    assert validate_oof(predictions, development)
    assert len(folds) == 5
    assert all(row["fit_rows"] + row["validation_rows"] == len(development) for row in folds)
    recomputed = summarize_oof(predictions, folds)
    for metric in ("average_precision", "roc_auc", "log_loss", "brier_score"):
        assert summary[f"{metric}_mean"] == recomputed[f"{metric}_mean"]
        assert summary[f"{metric}_std"] == pytest.approx(np.std([row[metric] for row in folds], ddof=1))
    y = np.array([int(row["default_next_month"]) for row in predictions])
    p = np.array([float(row["p_default"]) for row in predictions])
    assert summary["average_precision_pooled_oof"] == pytest.approx(average_precision_score(y, p))
    assert summary["roc_auc_pooled_oof"] == pytest.approx(roc_auc_score(y, p))
    assert summary["log_loss_pooled_oof"] == pytest.approx(log_loss(y, p, labels=[0, 1]))
    assert summary["brier_score_pooled_oof"] == pytest.approx(brier_score_loss(y, p, pos_label=1))
    evidence = json.loads((output / "fold_evidence.json").read_text())
    assert all(row["serialization_predictions_match"] for row in evidence)
    assert len(list(output.glob("fold_*.joblib"))) == 5
    if model == "dummy":
        reference = json.loads((output / "majority_hard_reference.json").read_text())
        assert all(row["fit_majority_class"] == 0 and row["recall_positive"] == 0 for row in reference)
    altered = [dict(row) for row in predictions]
    altered[0]["p_default"] = 0.99 if float(altered[0]["p_default"]) < 0.5 else 0.01
    with pytest.raises(ValueError, match="metric mismatch"):
        summarize_oof(altered, folds)


def test_metrics_fail_on_invalid_inputs_and_separate_pooled_from_fold_average():
    for y, p in (([0, 0], [0.1, 0.2]), ([0, 1], [0.2, np.nan]), ([0, 1], [0.2, 1.2])):
        with pytest.raises(ValueError):
            probability_metrics(y, p)
    # An unchanged within-fold ranking can coexist with cross-fold score offsets.
    rows, folds = [], []
    for fold in range(5):
        p = np.array([0.1, 0.2]) + fold * 0.15
        folds.append({"fold": fold, **probability_metrics([0, 1], p),
                      "fit_seconds": 0.0, "predict_seconds": 0.0})
        rows += [{"fold": fold, "default_next_month": y, "p_default": float(value)}
                 for y, value in zip([0, 1], p, strict=True)]
    summary = summarize_oof(rows, folds)
    assert summary["average_precision_mean"] == 1.0
    assert summary["average_precision_pooled_oof"] < 1.0


def test_controlled_comparison_signs():
    summaries = []
    for model in ("logistic", "random_forest"):
        for feature in ("raw", "engineered"):
            for weighting in ("none", "balanced"):
                value = 1.0 + int(feature == "engineered") + 2 * int(weighting == "balanced")
                summaries.append({"model": model, "feature_set": feature, "weighting": weighting,
                                  **{f"{metric}_mean": value for metric in
                                     ("average_precision", "roc_auc", "log_loss", "brier_score")}})
    contrasts = comparisons(summaries)
    assert len(contrasts) == 8
    for row in contrasts:
        assert row["average_precision_mean_delta"] == (1 if row["comparison"] == "engineered_minus_raw" else 2)


def test_resolved_imputer_parameters_have_strict_json_representation():
    params = build_pipeline("logistic", "engineered", "none").get_params(deep=True)
    restored = json.loads(json.dumps(_jsonable(params), allow_nan=False))
    assert restored["preprocessor__numeric__imputer__missing_values"] == "nan"
    assert restored["model__C"] == 1.0
