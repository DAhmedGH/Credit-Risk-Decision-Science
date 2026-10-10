"""Synthetic checks for explained scales, reference contrasts and audit support."""

import json

import numpy as np
import pandas as pd
import pytest

from credit_risk.data.schema import STATUS_COLUMNS
from credit_risk.explanations import (
    _sample_rows,
    descriptive_slices,
    logistic_interpretation,
    run_descriptive_analysis,
    select_diagnostic_cases,
    utilization_band_definition,
    utilization_bands,
    verify_shap_additivity,
)
from credit_risk.features import build_features
from credit_risk.models.pipelines import build_pipeline, positive_probability
from fixtures.records import make_record


def frame(count=120, first_id=1):
    rows = []
    for index in range(count):
        record = make_record(first_id + index, index % 3 == 0)
        record["limit_bal"] = 1000 + 20 * index
        record["sex"] = 1 if index % 2 else 2
        for column in STATUS_COLUMNS:
            record[column] = (-2, -1, 0, 1)[index % 4]
        record.update(build_features(record))
        rows.append(record)
    return pd.DataFrame(rows)


def test_case_rules_preserve_category_confidence_ties_and_missing_categories():
    validation = pd.DataFrame({"client_id": [9, 2, 3, 4, 5, 6],
                               "default_next_month": [1, 1, 0, 1, 0, 0]})
    p = np.array([0.9, 0.9, 0.1, 0.01, 0.95, 0.5])
    cases = select_diagnostic_cases(validation, p)
    assert cases["correct_default"]["client_id"] == 2
    assert cases["correct_nondefault"]["client_id"] == 3
    assert cases["missed_default"]["client_id"] == 4
    assert cases["false_alarm"]["client_id"] == 5
    no_errors = select_diagnostic_cases(validation.iloc[:3], [0.9, 0.9, 0.1])
    assert no_errors["missed_default"] == {"available": False}
    assert no_errors["false_alarm"] == {"available": False}
    # The 0.5 diagnostic boundary predicts default, independently of payoff ties.
    tied = select_diagnostic_cases(validation.iloc[[5]], [0.5])
    assert tied["false_alarm"]["available"]


@pytest.mark.parametrize("probabilities", [[0.1], [0, 2], [np.nan, 0], [0, np.inf]])
def test_invalid_case_probabilities_are_rejected(probabilities):
    validation = pd.DataFrame({"client_id": [1, 2], "default_next_month": [0, 1]})
    with pytest.raises(ValueError, match="Probabilities"):
        select_diagnostic_cases(validation, probabilities)


def test_logistic_contrasts_match_exact_fitted_log_odds_and_do_not_refit():
    train = frame()
    pipeline = build_pipeline("logistic", "engineered", "none").fit(
        train, train.default_next_month)
    before = positive_probability(pipeline, train)
    numeric, categorical, metadata = logistic_interpretation(pipeline)
    transformed = pipeline[:-1].transform(train)
    reconstructed = np.full(len(train), metadata["intercept"])
    for row in numeric.itertuples():
        reconstructed += transformed[row.transformed_feature] * row.coefficient_per_training_sd
    for row in categorical.itertuples():
        reconstructed += transformed[row.transformed_feature] * row.coefficient
        baseline = categorical.loc[
            (categorical.feature == row.feature) &
            (categorical.category == row.reference_category), "coefficient"].iloc[0]
        assert row.log_odds_contrast == pytest.approx(row.coefficient - baseline)
        assert row.odds_multiplier_vs_reference == pytest.approx(np.exp(row.log_odds_contrast))
    np.testing.assert_allclose(reconstructed, pipeline.decision_function(train), atol=1e-12)
    np.testing.assert_array_equal(before, positive_probability(pipeline, train))
    assert "one development-training standard deviation" in metadata["numeric_scale"]
    scaler = pipeline.named_steps["preprocessor"].named_transformers_["numeric"].named_steps[
        "scaler"]
    np.testing.assert_allclose(numeric.training_sd, np.sqrt(scaler.var_))


def test_utilization_definitions_use_only_development_and_keep_overflow_signed_missing():
    development = pd.DataFrame({"latest_utilization_proxy": [-2, -1, 0, 1, 2]})
    definition = utilization_band_definition(development)
    assert definition["quartiles"] == [-1, 0, 1]
    assert utilization_bands([-3, -1, 0, 1, 3, np.nan], definition).tolist() == [
        "below_development_min", "quartile_2", "quartile_3", "quartile_4",
        "above_development_max", "missing"]
    np.testing.assert_array_equal(development.latest_utilization_proxy, [-2, -1, 0, 1, 2])


def test_demographic_support_suppresses_all_summaries_and_preserves_counts():
    train = frame()
    validation = frame(300, 1000)
    validation.loc[299, "education"] = 0  # undocumented audit code -> unknown
    validation.loc[0, "age"] = np.nan
    p = np.full(300, 0.3)
    behavioral, demographic, metadata = descriptive_slices(train, validation, p)
    female = demographic.loc[(demographic.attribute == "sex") &
                             (demographic.group == "female")].iloc[0]
    assert female.n == 150 and not female.suppressed
    assert female.target_prevalence == pytest.approx(1 / 3)
    assert female.mean_risk_minus_prevalence == pytest.approx(0.3 - 1 / 3)
    unknown = demographic.loc[(demographic.attribute == "education") &
                              (demographic.group == "unknown")].iloc[0]
    assert unknown.n == 1 and unknown.suppressed
    for field in ("target_prevalence", "mean_predicted_risk", "recall", "false_positive_rate",
                  "mean_risk_minus_prevalence", "brier", "log_loss"):
        assert pd.isna(unknown[field])
    for attribute in demographic.attribute.unique():
        assert demographic.loc[demographic.attribute == attribute, "n"].sum() == len(validation)
    for attribute in behavioral.attribute.unique():
        assert behavioral.loc[behavioral.attribute == attribute, "n"].sum() == len(validation)
    assert metadata["utilization_bands"]["fit_partition"] == "development"


def test_support_requires_both_classes_even_when_total_count_is_large():
    validation = frame(300, 1000)
    validation["default_next_month"] = 0
    _, demographic, _ = descriptive_slices(frame(), validation, np.full(300, 0.1))
    assert demographic.suppressed.all()
    assert demographic.mean_predicted_risk.isna().all()


def test_background_sampling_is_capped_order_invariant_and_label_independent():
    development = frame(1500)
    expected = _sample_rows(development, 100).client_id.tolist()
    changed = development.sample(frac=1, random_state=7)
    changed["default_next_month"] = 1 - changed.default_next_month
    assert _sample_rows(changed, 100).client_id.tolist() == expected
    assert len(_sample_rows(development, 996)) == 996
    assert len(_sample_rows(frame(5), 100)) == 5


def test_shap_additivity_guard_rejects_wrong_scale_shapes_and_nonfinite_values():
    values = [[0.1, -0.2], [-0.5, 1.0]]
    assert verify_shap_additivity(values, -1.0, [-1.1, -0.5], (2, 2)) == pytest.approx(0)
    # Probabilities cannot substitute for the raw margins used in the attribution.
    with pytest.raises(ValueError, match="raw margin"):
        verify_shap_additivity(values, -1.0, [0.25, 0.38], (2, 2))
    with pytest.raises(ValueError, match="shape"):
        verify_shap_additivity(values, -1.0, [-1.1], (2, 2))
    with pytest.raises(ValueError, match="finite"):
        verify_shap_additivity([[np.nan, 0.0]], -1.0, [-1.1], (1, 2))


def test_descriptive_artifacts_are_json_safe_and_enforce_partition_disjointness(tmp_path):
    development = frame()
    validation = frame(300, 1000)
    logistic = build_pipeline("logistic", "raw", "none").fit(
        development, development.default_next_month)
    expected = positive_probability(logistic, validation)
    metadata = run_descriptive_analysis(logistic, development, validation, expected, tmp_path,
                                        reference_identity="fixture-logistic")
    assert json.loads((tmp_path / "descriptive_metadata.json").read_text()) == metadata
    assert metadata["logistic"]["reference_identity"] == "fixture-logistic"
    assert (tmp_path / "logistic_categorical_contrasts.csv").is_file()
    np.testing.assert_array_equal(expected, positive_probability(logistic, validation))
    with pytest.raises(ValueError, match="overlap"):
        run_descriptive_analysis(logistic, development, development, np.zeros(len(development)),
                                 tmp_path)
