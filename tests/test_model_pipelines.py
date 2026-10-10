"""Synthetic behavioral checks for the Phase 2 scientific fit boundary."""

# Dependency skip must precede imports of optional Phase 2 packages.
# ruff: noqa: E402

from __future__ import annotations

import copy

import pytest

# Missing Phase 2 dependencies are an explicit pending check, never a pass.
pytest.importorskip("sklearn", reason="Install the pinned Phase 2 dependencies first")

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.utils.class_weight import compute_class_weight

from credit_risk.data.schema import BILL_COLUMNS, RAW_PREDICTORS, STATUS_COLUMNS
from credit_risk.features import PREDICTORS, build_features
from credit_risk.models.pipelines import (
    build_pipeline,
    feature_columns,
    fold_class_weights,
    positive_probability,
)
from fixtures.records import make_record


def financial_frame(count=12):
    rows = []
    for index in range(count):
        row = make_record(index + 1, int(index % 4 == 0))
        row["limit_bal"] = 1000 + index * 100
        for column in STATUS_COLUMNS:
            row[column] = (-2, -1, 0, 1)[index % 4]
        row.update(build_features(row))
        rows.append(row)
    return pd.DataFrame(rows)


def test_feature_allowlists_are_fresh_canonical_and_exclude_metadata():
    assert feature_columns("raw") == list(RAW_PREDICTORS)
    assert feature_columns("engineered") == list(PREDICTORS)
    columns = feature_columns("raw")
    columns.append("age")
    assert feature_columns("raw") == list(RAW_PREDICTORS)
    assert not {"client_id", "default_next_month", "sex", "age", "education", "marriage"} & set(
        feature_columns("engineered")
    )
    with pytest.raises(ValueError, match="feature_set"):
        feature_columns("unrestricted")


def test_training_only_median_scaling_and_vocabulary_survive_heldout_sentinel():
    train = financial_frame(8)
    train.loc[0, "limit_bal"] = np.nan
    pipeline = build_pipeline("logistic", "raw", "none").fit(
        train, train["default_next_month"]
    )
    preprocessor = pipeline.named_steps["preprocessor"]
    numeric = preprocessor.named_transformers_["numeric"]
    categorical = preprocessor.named_transformers_["categorical"]
    medians = numeric.named_steps["imputer"].statistics_.copy()
    scaler_mean = numeric.named_steps["scaler"].mean_.copy()
    categories = copy.deepcopy(categorical.named_steps["encoder"].categories_)
    assert medians[0] == np.nanmedian(train["limit_bal"])
    expected_mean = train["limit_bal"].fillna(medians[0]).mean()
    assert scaler_mean[0] == pytest.approx(expected_mean)
    heldout = train.iloc[[0]].copy()
    heldout["limit_bal"] = 1e20
    heldout.loc[:, list(STATUS_COLUMNS)] = 9
    probabilities = positive_probability(pipeline, heldout)
    assert np.isfinite(probabilities).all()
    np.testing.assert_array_equal(medians, numeric.named_steps["imputer"].statistics_)
    np.testing.assert_array_equal(scaler_mean, numeric.named_steps["scaler"].mean_)
    for before, after in zip(categories, categorical.named_steps["encoder"].categories_, strict=True):
        np.testing.assert_array_equal(before, after)
        assert 9 not in after
    transformed = pipeline[:-1].transform(heldout)
    assert transformed.filter(like="categorical__").to_numpy().sum() == 0


@pytest.mark.parametrize("model", ["dummy", "logistic", "random_forest"])
@pytest.mark.parametrize("feature_set", ["raw", "engineered"])
def test_names_missing_values_unknown_categories_and_serialization(model, feature_set, tmp_path):
    train = financial_frame()
    train.loc[0, BILL_COLUMNS[0]] = np.nan
    train.loc[1, STATUS_COLUMNS[0]] = np.nan
    parameters = {"n_estimators": 5} if model == "random_forest" else None
    pipeline = build_pipeline(model, feature_set, "none", model_params=parameters)
    pipeline.fit(train, train["default_next_month"])
    scored = train.iloc[[0, 1]].copy()
    scored[STATUS_COLUMNS[0]] = 9
    transformed = pipeline[:-1].transform(scored)
    assert isinstance(transformed, pd.DataFrame)
    assert list(transformed) == list(pipeline[:-1].get_feature_names_out())
    assert np.isfinite(transformed.to_numpy()).all()
    numeric = [column for column in feature_columns(feature_set) if column not in STATUS_COLUMNS]
    assert list(transformed)[:len(numeric)] == [f"numeric__{column}" for column in numeric]
    assert not any(
        excluded in column
        for column in transformed
        for excluded in ("client_id", "default_next_month", "education", "marriage", "sex")
    )
    reordered = scored.loc[:, list(reversed(scored.columns))]
    expected = positive_probability(pipeline, scored)
    np.testing.assert_array_equal(expected, positive_probability(pipeline, reordered))
    altered_metadata = scored.copy()
    altered_metadata[["client_id", "default_next_month", "sex", "age", "education", "marriage"]] = 999
    np.testing.assert_array_equal(expected, positive_probability(pipeline, altered_metadata))
    path = tmp_path / "trusted-fixture.joblib"
    joblib.dump(pipeline, path)
    restored = joblib.load(path)
    np.testing.assert_array_equal(expected, positive_probability(restored, scored))
    np.testing.assert_allclose(
        expected, [positive_probability(restored, scored.iloc[[row]])[0] for row in range(len(scored))]
    )


def test_all_missing_training_columns_remain_present_and_impute_deterministically():
    train = financial_frame()
    train[BILL_COLUMNS[0]] = np.nan
    train[STATUS_COLUMNS[0]] = np.nan
    pipeline = build_pipeline("logistic", "raw", "none").fit(train, train["default_next_month"])
    transformed = pipeline[:-1].transform(train)
    assert f"numeric__{BILL_COLUMNS[0]}" in transformed
    assert np.isfinite(transformed.to_numpy()).all()
    assert (transformed[f"numeric__{BILL_COLUMNS[0]}"] == 0).all()
    assert f"categorical__{STATUS_COLUMNS[0]}_0.0" in transformed


def test_missing_duplicate_invalid_and_unnamed_predictor_schema_rejected():
    train = financial_frame()
    pipeline = build_pipeline("dummy", "raw", "none").fit(train, train["default_next_month"])
    with pytest.raises(ValueError, match="Missing financial"):
        positive_probability(pipeline, train.drop(columns=[BILL_COLUMNS[0]]))
    with pytest.raises(ValueError, match="duplicate"):
        positive_probability(pipeline, pd.concat([train, train[["limit_bal"]]], axis=1))
    with pytest.raises(ValueError, match="DataFrame"):
        positive_probability(pipeline, train.to_numpy())
    invalid = train.copy()
    invalid["limit_bal"] = "invalid"
    with pytest.raises(ValueError, match="numeric"):
        positive_probability(pipeline, invalid)
    invalid["limit_bal"] = np.inf
    with pytest.raises(ValueError, match="finite"):
        positive_probability(pipeline, invalid)


@pytest.mark.parametrize("model", ["logistic", "random_forest"])
def test_balanced_weights_are_recomputed_from_each_fit_labels(model):
    train = financial_frame()
    parameters = {"n_estimators": 5} if model == "random_forest" else None
    for fit_rows in (list(range(8)), list(range(1, 12))):
        fit = train.iloc[fit_rows]
        labels = fit["default_next_month"]
        weights = fold_class_weights(labels)
        expected = compute_class_weight("balanced", classes=np.array([0, 1]), y=labels)
        np.testing.assert_array_equal(list(weights.values()), expected)
        balanced = build_pipeline(model, "raw", "balanced", model_params=parameters)
        explicit = clone(balanced).set_params(model__class_weight=weights)
        balanced.fit(fit, labels)
        explicit.fit(fit, labels)
        np.testing.assert_allclose(
            positive_probability(balanced, train), positive_probability(explicit, train)
        )
        assert balanced.named_steps["model"].class_weight == "balanced"
    assert fold_class_weights(train.iloc[:8]["default_next_month"]) != fold_class_weights(
        train.iloc[1:12]["default_next_month"]
    )


def test_balanced_weights_validate_labels_and_protected_settings():
    for labels in ([0, 0], [1, 2], [[0], [1]], [0, np.nan]):
        with pytest.raises(ValueError, match="Fit labels"):
            fold_class_weights(labels)
    with pytest.raises(ValueError, match="unweighted"):
        build_pipeline("dummy", "raw", "balanced")
    for override in ({"class_weight": {0: 1, 1: 2}}, {"n_jobs": -1}, {"random_state": 4}):
        with pytest.raises(ValueError, match="protected"):
            build_pipeline("logistic", "raw", "none", model_params=override)


def test_positive_probability_uses_class_mapping_and_rejects_invalid_output():
    class ReversedEstimator:
        classes_ = np.array([1, 0])

        def predict_proba(self, X):
            return np.array([[0.8, 0.2], [0.3, 0.7]])

    estimator = ReversedEstimator()
    np.testing.assert_array_equal(positive_probability(estimator, [1, 2]), [0.8, 0.3])
    estimator.classes_ = np.array([0, 2])
    with pytest.raises(ValueError, match="binary classes"):
        positive_probability(estimator, [1, 2])
    estimator.classes_ = np.array([0, 1])
    with pytest.raises(ValueError, match="shape"):
        positive_probability(estimator, [1])
    estimator.predict_proba = lambda X: np.array([[np.nan, 0.2], [0.3, 0.7]])
    with pytest.raises(ValueError, match="finite probability"):
        positive_probability(estimator, [1, 2])


def test_dummy_returns_training_prior_and_forest_keeps_one_worker():
    train = financial_frame()
    dummy = build_pipeline("dummy", "raw", "none").fit(train, train["default_next_month"])
    np.testing.assert_array_equal(
        positive_probability(dummy, train), np.full(len(train), train["default_next_month"].mean())
    )
    forest = build_pipeline("random_forest", "raw", "none")
    assert forest.named_steps["model"].n_jobs == 1
    assert "scaler" not in dict(forest.named_steps["preprocessor"].transformers[0][1].steps)
