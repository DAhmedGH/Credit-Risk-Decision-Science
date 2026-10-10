"""Runnable without modeling packages: frozen IDs bound all outcome access."""

import copy

import pytest

from credit_risk.artifacts import write_csv
from credit_risk.features import PREDICTORS, build_features
from credit_risk.models.inputs import select_development, validate_oof, verify_assignments
from credit_risk import phase2
from credit_risk.phase2 import load_phase2_config, variants
from credit_risk.splits import allocate_records
from fixtures.records import make_records


@pytest.fixture
def inputs(tmp_path):
    records = make_records(200)
    source = "a" * 64
    assignments, _ = allocate_records(records, source)
    features = [{"client_id": row["client_id"], **build_features(row)} for row in records]
    labels = [{"client_id": row["client_id"], "default_next_month": row["default_next_month"]}
              for row in records]
    features_path, labels_path = tmp_path / "features.csv", tmp_path / "labels.csv"
    write_csv(features_path, features, ("client_id", *PREDICTORS))
    write_csv(labels_path, labels, ("client_id", "default_next_month"))
    return features_path, labels_path, assignments, source, features, labels


def test_filter_precedes_numeric_or_outcome_interpretation(inputs):
    features_path, labels_path, assignments, source, features, labels = inputs
    expected = select_development(features_path, labels_path, assignments, source)
    heldout = {int(row["client_id"]) for row in assignments if row["partition"] != "development"}
    for row in features:
        if row["client_id"] in heldout:
            row.update({column: "must-never-be-interpreted" for column in PREDICTORS})
    for row in labels:
        if row["client_id"] in heldout:
            row["default_next_month"] = "must-never-be-interpreted"
    write_csv(features_path, features, ("client_id", *PREDICTORS))
    write_csv(labels_path, labels, ("client_id", "default_next_month"))
    assert select_development(features_path, labels_path, assignments, source) == expected
    assert {row["fold"] for row in expected} == set(range(5))


def test_groups_and_source_cannot_cross_frozen_boundaries(inputs):
    _, _, assignments, source, _, _ = inputs
    verify_assignments(assignments, source)
    tampered = copy.deepcopy(assignments)
    development = [row for row in tampered if row["partition"] == "development"]
    first = development[0]
    other = next(row for row in development if row["fold"] != first["fold"])
    other["fingerprint"] = first["fingerprint"]
    with pytest.raises(ValueError, match="crosses"):
        verify_assignments(tampered, source)
    with pytest.raises(ValueError, match="source"):
        verify_assignments(assignments, "b" * 64)
    tampered = copy.deepcopy(assignments)
    tampered[0]["client_id"] = tampered[1]["client_id"]
    with pytest.raises(ValueError, match="unique"):
        verify_assignments(tampered, source)


def test_development_fingerprint_and_export_coverage_are_verified(inputs):
    features_path, labels_path, assignments, source, features, labels = inputs
    development_id = next(row["client_id"] for row in assignments if row["partition"] == "development")
    row = next(row for row in features if row["client_id"] == development_id)
    row["limit_bal"] += 1
    write_csv(features_path, features, ("client_id", *PREDICTORS))
    with pytest.raises(ValueError, match="fingerprint"):
        select_development(features_path, labels_path, assignments, source)
    labels = [row for row in labels if row["client_id"] != development_id]
    write_csv(labels_path, labels, ("client_id", "default_next_month"))
    with pytest.raises(ValueError, match="coverage"):
        select_development(features_path, labels_path, assignments, source)


def test_out_of_fold_coverage_and_assignments_cannot_be_faked(inputs):
    features_path, labels_path, assignments, source, _, _ = inputs
    expected = select_development(features_path, labels_path, assignments, source)
    rows = [{key: row[key] for key in ("client_id", "fold", "fingerprint", "default_next_month")} |
            {"p_default": 0.2} for row in expected]
    assert validate_oof(rows, expected)
    for invalid in (rows[:-1], rows + [rows[0]], [rows[0]] + rows[:-1]):
        with pytest.raises(ValueError, match="coverage|duplicated"):
            validate_oof(invalid, expected)
    for column, value in (("client_id", 999999), ("fold", 99), ("fingerprint", "0" * 64),
                          ("default_next_month", 2), ("p_default", float("nan")),
                          ("p_default", -0.1), ("p_default", 1.1)):
        invalid = copy.deepcopy(rows)
        invalid[0][column] = value
        with pytest.raises(ValueError):
            validate_oof(invalid, expected)


def test_fixed_factorial_design_and_worker_contract():
    design = variants()
    assert len(design) == len(set(design)) == 9
    assert design[0] == ("dummy", "raw", "none")
    assert {row[0] for row in design} == {"dummy", "logistic", "random_forest"}
    config = load_phase2_config()
    assert config["threads"] == 1 and config["seed"] == 42


def test_dependency_failure_precedes_outcome_access(monkeypatch):
    monkeypatch.setattr(phase2, "MODEL_PINS", {"credit-risk-nonexistent-test-package": "0"})
    monkeypatch.setattr(phase2, "load_development", lambda *args: pytest.fail("outcomes accessed"))
    with pytest.raises(ModuleNotFoundError, match="dependencies unavailable"):
        phase2.run()
