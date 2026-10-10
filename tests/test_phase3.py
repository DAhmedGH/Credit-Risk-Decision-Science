"""Phase 3 runner and provenance checks using isolated synthetic projects.

The fake XGBoost class tests wrapper plumbing only. Real XGBoost execution has a
separate dependency-gated integration test and is never implied by the mock.
"""

# ruff: noqa: E402
import json
from pathlib import Path
import shutil
import sys
import tomllib
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

import pytest

pytest.importorskip("sklearn", reason="Install pinned modeling dependencies first")
pytest.importorskip("mlflow", reason="Install pinned local tracking dependencies first")

import joblib
from mlflow import MlflowClient
import numpy as np
import pandas as pd
from sklearn.base import clone, is_classifier
from sklearn.exceptions import ConvergenceWarning

from credit_risk.artifacts import file_sha256, write_json
from credit_risk.features import PREDICTORS
from credit_risk.models.pipelines import (
    FoldLocalXGBClassifier, build_pipeline, positive_probability,
)
from credit_risk.phase3 import (
    XGB_PIN, _fit_development, _verify_profile, load_phase3_config, load_searches,
    profile, run_search, select, verify,
)
from test_baseline_tracking import fixture_project


def phase3_fixture_project(root):
    """Keep source/config hashes meaningful while all data and runs stay synthetic."""
    fixture_project(root)
    project = Path(__file__).resolve().parents[1]
    receipt = tomllib.loads((root / "configs/phase2.toml").read_text())["split_receipt"]
    config = (project / "configs/phase3.toml").read_text().replace(
        "artifacts/split_checks/840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537.json",
        receipt)
    config = config.replace("logistic = 3", "logistic = 1").replace(
        "random_forest = 3", "random_forest = 1").replace("xgboost = 6", "xgboost = 1")
    config = config.replace("n_estimators = [100, 200, 300]", "n_estimators = [3]")
    (root / "configs/phase3.toml").write_text(config)
    shutil.copytree(project / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    for relative in ("requirements-phase3.in", "scripts/bootstrap_phase3.sh"):
        source = project / relative
        if source.exists():
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())


def test_logistic_runner_tracks_bounded_fixture_and_verifies_saved_evidence(tmp_path, monkeypatch):
    phase3_fixture_project(tmp_path)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "https://invalid.example/never-contact")
    result = run_search("logistic", root=tmp_path)
    assert result["fit_count"] == 20
    assert result["base_selected"] is False
    manifest_path = tmp_path / result["manifest"]
    receipt = json.loads(manifest_path.read_text())
    assert receipt["development_rows"] == 120
    assert sum(receipt["fold_rows"].values()) == 120
    assert receipt["automatic_refits"] == 0
    assert receipt["base_selected"] is False
    assert receipt["complete_bundle_frozen"] is False
    assert len(receipt["candidate_run_ids"]) == 4
    assert receipt["input_hashes"] and receipt["code_file_hashes"]
    assert "src/credit_risk/phase3.py" in receipt["code_file_hashes"]
    assert "scripts/bootstrap_phase3.sh" in receipt["code_file_hashes"]
    assert receipt["dependency_lock_sha256"] == file_sha256(tmp_path / "requirements.lock")
    assert receipt["artifacts"] and receipt["compact_artifacts"]
    for relative, digest in receipt["artifacts"].items():
        assert file_sha256(tmp_path / relative) == digest
    client = MlflowClient(tracking_uri=(tmp_path / "mlruns").as_uri())
    for identifier in (result["parent_run_id"], *receipt["candidate_run_ids"].values()):
        recorded = client.get_run(identifier)
        assert recorded.info.status == "FINISHED"
        expected = tmp_path / "mlruns" / recorded.info.experiment_id / identifier / "artifacts"
        assert Path(unquote(urlparse(recorded.info.artifact_uri).path)) == expected
        assert recorded.data.params["positive_class"] == "1"
        assert recorded.data.params["plan_sha256"] == receipt["plan_sha256"]
        assert recorded.data.tags["partition"] == "development"
        assert client.list_artifacts(identifier)
        if identifier != result["parent_run_id"]:
            assert recorded.data.tags["mlflow.parentRunId"] == result["parent_run_id"]
            assert "development_cv_average_precision_mean" in recorded.data.metrics
            assert len(client.get_metric_history(identifier, "development_cv_fold_log_loss")) == 5
    assert verify(result["parent_run_id"], root=tmp_path) == {
        "run_id": result["parent_run_id"], "artifact_hashes_and_tracking": "passed",
        "fit_count": 20, "base_selected": False}
    artifact = tmp_path / next(iter(receipt["artifacts"]))
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="checksum"):
        verify(result["parent_run_id"], root=tmp_path)
    assert not list((tmp_path / "artifacts/models/phase3").rglob("development_pipeline.joblib"))


def fake_completed_searches(root, models=("logistic", "random_forest", "xgboost")):
    """Guard fixtures contain no invented metrics or fitted-model evidence."""
    identifiers = [str(index) * 32 for index in (1, 2, 3)]
    for identifier, model in zip(identifiers, models, strict=True):
        folder = root / "reports/phase3_runs" / identifier
        write_json(folder / "manifest.json", {
            "fixture_only": True, "status": "FINISHED", "model": model,
            "artifacts": {}, "compact_artifacts": {}, "plan_sha256": "a" * 64,
            "input_hashes": {"fixture": "b" * 64}, "dependency_lock_sha256": "c" * 64,
            "code_tree_sha256": "d" * 64,
        })
        write_json(folder / "search.json", {"fixture_only": True})
    return identifiers


def test_selection_loader_rejects_missing_family_incomplete_and_mixed_provenance(tmp_path):
    config = {"reports_dir": "reports/phase3_runs"}
    with pytest.raises(ValueError, match="three distinct"):
        load_searches(["1" * 32], config, tmp_path)
    identifiers = fake_completed_searches(tmp_path, models=("logistic", "logistic", "xgboost"))
    with pytest.raises(ValueError, match="logistic, forest and XGBoost"):
        load_searches(identifiers, config, tmp_path)
    identifiers = fake_completed_searches(tmp_path)
    path = tmp_path / config["reports_dir"] / identifiers[1] / "manifest.json"
    original = json.loads(path.read_text())
    incomplete = {**original, "status": "RUNNING"}
    write_json(path, incomplete)
    with pytest.raises(ValueError, match="incomplete"):
        load_searches(identifiers, config, tmp_path)
    for field in ("plan_sha256", "input_hashes", "dependency_lock_sha256", "code_tree_sha256"):
        modified = {**original, field: {"changed": True} if field == "input_hashes" else "e" * 64}
        write_json(path, modified)
        with pytest.raises(ValueError, match=f"provenance differs: {field}"):
            load_searches(identifiers, config, tmp_path)


def test_profile_receipt_rejects_stale_code_plan_inputs_and_lock(tmp_path):
    phase3_fixture_project(tmp_path)
    config = load_phase3_config(root=tmp_path)
    hashes = {"synthetic_fixture": "a" * 64}
    context = {"code_tree_sha256": "b" * 64, "plan_sha256": "c" * 64}
    receipt = {
        "fixture_only": True, "input_hashes": hashes, "xgboost_version": XGB_PIN,
        "dependency_lock_sha256": file_sha256(tmp_path / "requirements.lock"),
        **context, "fit_count": 5, "serialization_passed": True,
    }
    with pytest.raises(ValueError, match="phase3-profile"):
        _verify_profile(config, hashes, tmp_path, context)
    write_json(tmp_path / config["profile_receipt"], receipt)
    assert _verify_profile(config, hashes, tmp_path, context)["fixture_only"]
    for field in ("code_tree_sha256", "plan_sha256", "input_hashes", "dependency_lock_sha256"):
        stale = {**receipt, field: {"changed": True} if field == "input_hashes" else "d" * 64}
        write_json(tmp_path / config["profile_receipt"], stale)
        with pytest.raises(ValueError, match="does not match"):
            _verify_profile(config, hashes, tmp_path, context)


def test_development_refit_refuses_nonconverged_logistic_model(tmp_path):
    phase3_fixture_project(tmp_path)
    frame = pd.read_csv(tmp_path / "data/processed/financial_features_v1.csv")
    labels = pd.read_csv(tmp_path / "data/processed/labels.csv")["default_next_month"]
    # Synthetic software fixture only; this check does not load project outcomes.
    pipeline = build_pipeline("logistic", "engineered", "none", model_params={"max_iter": 1})
    with pytest.raises((ConvergenceWarning, ValueError), match="converg|max_iter|iteration"):
        _fit_development(pipeline, frame.loc[:, list(PREDICTORS)], labels)


class FakeXGBClassifier:
    """Inspectable probability stub; this is not an XGBoost implementation."""

    def __init__(self, **parameters):
        self.parameters = parameters

    def fit(self, X, y):
        self.classes_ = np.array([0, 1])
        self.n_features_in_ = np.asarray(X).shape[1]
        self.probability_ = float(np.mean(y))
        return self

    def predict_proba(self, X):
        p = np.full(len(X), self.probability_)
        return np.column_stack((1 - p, p))

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= .5).astype(int)


def test_xgboost_wrapper_recomputes_fit_weight_and_preserves_clone_and_serialization(
        tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "xgboost", SimpleNamespace(XGBClassifier=FakeXGBClassifier))
    wrapper = FoldLocalXGBClassifier("balanced", 42, {"n_estimators": 3})
    assert is_classifier(wrapper)
    assert clone(wrapper).get_params() == wrapper.get_params()
    for labels in ([0, 0, 0, 1], [0, 0, 1, 1, 1]):
        X = np.arange(len(labels) * 2).reshape(-1, 2)
        wrapper.fit(X, np.asarray(labels))
        ratio = labels.count(0) / labels.count(1)
        assert wrapper.scale_pos_weight_ == ratio
        assert wrapper.estimator_.parameters["scale_pos_weight"] == ratio
        assert wrapper.estimator_.parameters["n_jobs"] == 1
        assert wrapper.estimator_.parameters["tree_method"] == "hist"
        assert wrapper.estimator_.parameters["device"] == "cpu"
        assert wrapper.estimator_.parameters["objective"] == "binary:logistic"
        assert "early_stopping_rounds" not in wrapper.estimator_.parameters
        np.testing.assert_array_equal(wrapper.fit_class_counts_, np.bincount(labels))
        path = tmp_path / "mock-contract-only.joblib"
        joblib.dump(wrapper, path)
        np.testing.assert_array_equal(positive_probability(wrapper, X),
                                      positive_probability(joblib.load(path), X))
    unweighted = FoldLocalXGBClassifier("none").fit(np.zeros((4, 2)), np.array([0, 0, 0, 1]))
    assert unweighted.scale_pos_weight_ == 1.0
    assert "scale_pos_weight_" not in clone(wrapper).__dict__
    for parameters in ({"scale_pos_weight": 100}, {"n_jobs": -1},
                       {"early_stopping_rounds": 2}, {"eval_set": []}):
        protected = FoldLocalXGBClassifier(model_params=parameters)
        with pytest.raises(ValueError, match="protected"):
            protected.fit(np.zeros((4, 2)), np.array([0, 0, 0, 1]))


def test_real_xgboost_complete_fixture_selection_preserves_development_only_bundles(tmp_path):
    pytest.importorskip("xgboost", reason="Install pinned Phase 3 XGBoost before this integration")
    phase3_fixture_project(tmp_path)
    smoke = profile(root=tmp_path)
    assert smoke["fit_count"] == 5 and smoke["serialization_passed"]
    results = [run_search(family, root=tmp_path)
               for family in ("logistic", "random_forest", "xgboost")]
    selection = select([result["parent_run_id"] for result in results], root=tmp_path)
    assert selection["base_selected"] is True
    assert selection["complete_bundle_frozen"] is False
    assert selection["search_cv_fits"] == 60
    assert selection["oof_refits"] == 5 * len(selection["bundles"])
    assert selection["all_development_refits"] == len(selection["bundles"])
    assert 4 <= len(selection["bundles"]) <= 5
    roles = []
    for identifier, bundle in selection["bundles"].items():
        metadata = json.loads((tmp_path / bundle["metadata"]).read_text())
        assert metadata["training_partition"] == "development"
        assert metadata["training_rows"] == 120
        assert metadata["save_load_predictions_match"] is True
        assert metadata["pipeline_sha256"] == file_sha256(tmp_path / bundle["pipeline"])
        assert metadata["positive_class"] == 1
        assert not {"client_id", "default_next_month", "age", "sex", "marriage", "education"} & set(
            metadata["feature_columns"])
        assert (tmp_path / bundle["pipeline"]).with_name("oof_predictions.csv").exists()
        roles.append(metadata["role"])
        if metadata["role"] == "selected_base":
            assert identifier == selection["selected_candidate_id"]
    assert roles.count("selected_base") == 1
    assert verify(selection["parent_run_id"], root=tmp_path)["base_selected"] is True
