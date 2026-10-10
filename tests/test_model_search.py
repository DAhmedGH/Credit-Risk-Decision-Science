"""Synthetic tests of the bounded search contract; no held-out outcomes."""

# ruff: noqa: E402
import copy
import json

import pytest

pytest.importorskip("sklearn", reason="Install pinned modeling dependencies first")

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone, is_classifier
from sklearn.exceptions import ConvergenceWarning

from credit_risk.artifacts import read_csv
from credit_risk.features import PREDICTORS, build_features
from credit_risk.models.evaluation import evaluate_variant
from credit_risk.models.pipelines import positive_probability
from credit_risk.models.search import (
    BUDGET_CEILINGS, SearchCandidate, frozen_cv, make_search_plan,
    run_family_search, select_base_candidate,
)
from credit_risk.splits import allocate_records
from fixtures.records import make_records


@pytest.fixture
def development():
    source = make_records(200)
    assignments, _ = allocate_records(source, "a" * 64)
    selected = {row["client_id"]: row for row in assignments
                if row["partition"] == "development"}
    return [{"client_id": row["client_id"], "fold": selected[row["client_id"]]["fold"],
             "fingerprint": selected[row["client_id"]]["fingerprint"],
             "default_next_month": row["default_next_month"], **build_features(row)}
            for row in source if row["client_id"] in selected]


def tiny_candidates():
    return make_search_plan(settings_per_family={"logistic": 1})["families"]["logistic"]["candidates"]


def test_plan_reproducible_matched_and_within_total_family_budgets():
    plan = make_search_plan()
    assert plan == json.loads(json.dumps(plan)) == make_search_plan()
    assert plan != make_search_plan(seed=43)
    assert plan["refit"] is False and plan["early_stopping"] is False
    for family, expected in (("logistic", 12), ("random_forest", 12), ("xgboost", 24)):
        declaration = plan["families"][family]
        candidates = declaration["candidates"]
        assert declaration["configurations"] == len(candidates) == expected
        assert declaration["cv_fits"] == len(candidates) * 5
        assert len(candidates) <= BUDGET_CEILINGS[family]
        for setting in {row["setting_id"] for row in candidates}:
            matched = [row for row in candidates if row["setting_id"] == setting]
            assert len(matched) == 4
            assert len({json.dumps(row["model_params"], sort_keys=True) for row in matched}) == 1
            assert {(row["feature_set"], row["weighting"]) for row in matched} == {
                (feature, weight) for feature in ("raw", "engineered")
                for weight in ("none", "balanced")}
    with pytest.raises(ValueError, match="budget"):
        make_search_plan(settings_per_family={"logistic": 4})
    with pytest.raises(ValueError, match="exactly"):
        make_search_plan(settings_per_family={"unknown": 1})


def test_frozen_cv_uses_exact_existing_rows_and_rejects_group_or_label_failure(development):
    folds = np.array([row["fold"] for row in development])
    for fold, (fit, validation) in enumerate(frozen_cv(development)):
        np.testing.assert_array_equal(fit, np.flatnonzero(folds != fold))
        np.testing.assert_array_equal(validation, np.flatnonzero(folds == fold))
        assert not set(fit) & set(validation)
    altered = copy.deepcopy(development)
    first = next(index for index, row in enumerate(altered) if row["fold"] != altered[0]["fold"])
    altered[first]["fingerprint"] = altered[0]["fingerprint"]
    with pytest.raises(ValueError, match="fingerprint"):
        frozen_cv(altered)
    altered = copy.deepcopy(development)
    for row in altered:
        if row["fold"] == 0:
            row["default_next_month"] = 0
    with pytest.raises(ValueError, match="both classes"):
        frozen_cv(altered)


def test_search_fits_exact_budget_and_reconciles_saved_metrics_with_oof(development, tmp_path):
    candidates = tiny_candidates()
    result = run_family_search(development, "logistic", candidates, output=tmp_path / "search")
    assert result["fit_count"] == 20 and result["automatic_refits"] == 0
    assert len(result["candidates"]) == 4 and len(result["fold_metrics"]) == 20
    assert result["oof_coverage_and_metric_reconciliation"] == "passed"
    assert len(list((tmp_path / "search" / "oof").glob("*.csv"))) == 4
    assert len(result["oof_artifacts"]) == 4
    persisted = json.loads((tmp_path / "search" / "search.json").read_text())
    assert result == persisted
    assert len(read_csv(tmp_path / "search" / "candidate_metrics.csv")) == 4
    assert {row["candidate_id"] for row in result["candidates"]} == {
        row["candidate_id"] for row in candidates}
    for row in result["candidates"]:
        folds = [fold for fold in result["fold_metrics"]
                 if fold["candidate_id"] == row["candidate_id"]]
        for metric in ("average_precision", "roc_auc", "log_loss", "brier_score",
                       "fit_seconds", "predict_seconds"):
            assert row[f"{metric}_mean"] == pytest.approx(np.mean([f[metric] for f in folds]))
            assert row[f"{metric}_std"] == pytest.approx(np.std([f[metric] for f in folds], ddof=1))
            assert all(np.isfinite(f[metric]) and f[metric] >= 0 for f in folds)
    selected = result["candidates"][0]
    summary, _ = evaluate_variant(
        development, "logistic", selected["feature_set"], selected["weighting"],
        42, selected["model_params"], tmp_path / "oof")
    for metric in ("average_precision", "roc_auc", "log_loss", "brier_score"):
        assert selected[f"{metric}_mean"] == pytest.approx(summary[f"{metric}_mean"], abs=1e-12)
        assert selected[f"{metric}_pooled_oof"] == pytest.approx(
            summary[f"{metric}_pooled_oof"], abs=1e-12)


def test_search_rejects_over_budget_duplicate_or_failed_candidates(development):
    candidates = tiny_candidates()
    with pytest.raises(ValueError, match="budget"):
        run_family_search(development, "logistic", candidates * 4)
    with pytest.raises(ValueError, match="Duplicate"):
        run_family_search(development, "logistic", candidates + [candidates[0]])
    with pytest.raises(ValueError, match="worker"):
        run_family_search(development, "logistic", candidates, n_jobs=-1)
    invalid = copy.deepcopy(candidates[:1])
    invalid[0]["model_params"]["invalid_parameter"] = 3
    with pytest.raises(TypeError):
        run_family_search(development, "logistic", invalid)
    nonconvergent = copy.deepcopy(candidates[:1])
    nonconvergent[0]["model_params"]["max_iter"] = 1
    with pytest.raises((ConvergenceWarning, RuntimeError)):
        run_family_search(development, "logistic", nonconvergent)


def test_search_preprocessing_and_balanced_weights_are_fit_local(development, monkeypatch):
    observed = []
    original_fit = SearchCandidate.fit

    def capture_fit(self, X, y):
        fitted = original_fit(self, X, y)
        numeric = self.pipeline_.named_steps["preprocessor"].named_transformers_["numeric"]
        imputer = numeric.named_steps["imputer"]
        scaler = numeric.named_steps["scaler"]
        assert imputer.statistics_[0] == pytest.approx(np.nanmedian(X["limit_bal"]))
        assert scaler.mean_[0] == pytest.approx(
            X["limit_bal"].fillna(imputer.statistics_[0]).mean())
        np.testing.assert_array_equal(self.fit_class_counts_, np.bincount(y, minlength=2))
        assert self.pipeline_.named_steps["model"].class_weight == "balanced"
        observed.append((len(X), imputer.statistics_[0], tuple(self.fit_class_counts_)))
        return fitted

    monkeypatch.setattr(SearchCandidate, "fit", capture_fit)
    records = copy.deepcopy(development)
    for row in records:
        if row["fold"] == 0:
            row["limit_bal"] = 1e15
    candidate = [row for row in tiny_candidates()
                 if row["feature_set"] == "raw" and row["weighting"] == "balanced"]
    run_family_search(records, "logistic", candidate)
    assert len(observed) == 5
    assert all(fit_rows < len(records) and median < 1e15
               for fit_rows, median, _ in observed)
    assert len({counts for _, _, counts in observed}) > 1


def test_candidate_classifier_clone_and_save_load(development, tmp_path):
    frame = pd.DataFrame(development)
    X, y = frame.loc[:, list(PREDICTORS)], frame["default_next_month"]
    candidate = SearchCandidate("logistic", "engineered", "balanced", 42, {"C": 0.1})
    assert is_classifier(candidate)
    assert clone(candidate).get_params() == candidate.get_params()
    candidate.fit(X, y)
    path = tmp_path / "trusted-synthetic.joblib"
    joblib.dump(candidate, path)
    restored = joblib.load(path)
    np.testing.assert_array_equal(positive_probability(candidate, X), positive_probability(restored, X))


def candidate(identifier, model, ap, loss, feature_set="raw", weighting="none", **params):
    return {"candidate_id": identifier, "model": model, "average_precision_mean": ap,
            "log_loss_mean": loss, "feature_set": feature_set, "weighting": weighting,
            "model_params": params, "predict_seconds_mean": 0.01}


def test_selection_ap_gate_loss_gate_and_family_simplicity_are_separate():
    rows = [candidate("xgb", "xgboost", .56, .44),
            candidate("forest", "random_forest", .553, .425),
            candidate("logistic", "logistic", .55, .4258),
            candidate("outside", "logistic", .549, .40)]
    selection = select_base_candidate(rows)
    assert selection["ap_eligible_candidate_ids"] == ["forest", "logistic", "xgb"]
    assert selection["small_loss_candidate_ids"] == ["forest", "logistic"]
    assert selection["selected"]["candidate_id"] == "logistic"
    assert selection["tolerance_is_significance_test"] is False
    assert select_base_candidate(rows, log_loss_tolerance=0)["selected"]["candidate_id"] == "forest"
    assert select_base_candidate(rows, ap_tolerance=0)["selected"]["candidate_id"] == "xgb"


def test_selection_complexity_then_exact_loss_precedes_runtime():
    rows = [candidate("large", "xgboost", .56, .420, n_estimators=300, max_depth=3),
            candidate("small", "xgboost", .555, .4208, n_estimators=100, max_depth=2)]
    assert select_base_candidate(rows)["selected"]["candidate_id"] == "small"
    rows = [candidate("fast", "logistic", .56, .4208),
            candidate("slow", "logistic", .555, .4200)]
    rows[0]["predict_seconds_mean"] = .001
    rows[1]["predict_seconds_mean"] = .1
    assert select_base_candidate(rows)["selected"]["candidate_id"] == "slow"
    for invalid in ([], [candidate("bad", "logistic", np.nan, .4)]):
        with pytest.raises(ValueError):
            select_base_candidate(invalid)


def test_xgboost_search_and_oof_use_identical_positive_probability_metrics(development, tmp_path):
    pytest.importorskip("xgboost", reason="Install the pinned Phase 3 XGBoost dependency")
    chosen = [{"candidate_id": "tiny_xgb", "model": "xgboost", "feature_set": "raw",
               "weighting": "balanced", "model_params": {"n_estimators": 3, "max_depth": 2}}]
    result = run_family_search(development, "xgboost", chosen)
    summary, _ = evaluate_variant(development, "xgboost", "raw", "balanced", 42,
                                  chosen[0]["model_params"], tmp_path / "xgb_oof")
    for metric in ("average_precision", "roc_auc", "log_loss", "brier_score"):
        assert result["candidates"][0][f"{metric}_mean"] == pytest.approx(
            summary[f"{metric}_mean"], abs=1e-12)
