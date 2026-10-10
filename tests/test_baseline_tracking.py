"""End-to-end synthetic tracking fixture isolated from the real data and runs."""

# ruff: noqa: E402
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

pytest.importorskip("sklearn", reason="Phase 2 model runtime not installed")
pytest.importorskip("mlflow", reason="Local MLflow runtime not installed")

from mlflow import MlflowClient

from credit_risk.artifacts import file_sha256, json_bytes, sha256_bytes, write_csv, write_json
from credit_risk.features import PREDICTORS, build_features, feature_contract
from credit_risk.phase2 import run
from credit_risk.splits import allocate_records
from fixtures.records import make_records


def fixture_project(root):
    """Mock Phase 1 evidence is software-fixture data, never portfolio evidence."""
    records = make_records(200)
    workbook = root / "data/raw/fixture.xls"
    workbook.parent.mkdir(parents=True)
    workbook.write_bytes(b"synthetic fixture, not an XLS workbook")
    source_hash = file_sha256(workbook)
    assignments, _ = allocate_records(records, source_hash)
    write_csv(root / "artifacts/split_manifest.csv", assignments, tuple(assignments[0]))
    write_json(root / "artifacts/feature_contract_v1_1.json", feature_contract())
    write_json(root / "artifacts/source_manifest.json", {"workbook": {"sha256": source_hash}})
    write_csv(root / "data/processed/financial_features_v1.csv",
              [{"client_id": row["client_id"], **build_features(row)} for row in records],
              ("client_id", *PREDICTORS))
    write_csv(root / "data/processed/labels.csv", [{"client_id": row["client_id"],
              "default_next_month": row["default_next_month"]} for row in records],
              ("client_id", "default_next_month"))
    contract_hash = file_sha256(root / "artifacts/feature_contract_v1_1.json")
    receipt = {"source_sha256": source_hash, "dataset_version": "uci350-v1.1",
               "feature_contract_sha256": contract_hash,
               "manifest_file_sha256": file_sha256(root / "artifacts/split_manifest.csv"),
               "source_reader_evidence": "canonical-xlrd", "integrity": {"fixture_only": True}}
    receipt_name = sha256_bytes(json_bytes(receipt))
    receipt_path = f"artifacts/split_checks/{receipt_name}.json"
    write_json(root / receipt_path, receipt)
    write_json(root / "artifacts/phase1_export_manifest.json", {
        "source_sha256": source_hash, "feature_contract_sha256": contract_hash,
        "dataset_version": "uci350-v1.1", "exported_rows": len(records),
        "financial_export_sha256": file_sha256(root / "data/processed/financial_features_v1.csv"),
        "label_export_sha256": file_sha256(root / "data/processed/labels.csv"),
        "counts_reconcile": True, "sql_python_all_rows_agree": True})
    project_root = Path(__file__).resolve().parents[1]
    (root / "configs").mkdir()
    base = (project_root / "configs/base.toml").read_text().replace(
        "data/raw/default of credit card clients.xls", "data/raw/fixture.xls")
    (root / "configs/base.toml").write_text(base)
    text = (project_root / "configs/phase2.toml").read_text().replace(
        "artifacts/split_checks/840b8d85f42f4dc69e0a693c47af7effcac1afc90004094f189fef467dd79537.json",
        receipt_path).replace("n_estimators = 200", "n_estimators = 2")
    (root / "configs/phase2.toml").write_text(text)
    for name in ("requirements.lock", "requirements-phase2.in", "pyproject.toml"):
        (root / name).write_bytes((project_root / name).read_bytes())


def test_real_local_mlflow_tracks_fixture_runs_and_ignores_remote_environment(tmp_path, monkeypatch):
    fixture_project(tmp_path)
    # A user environment variable cannot send synthetic or customer data remotely.
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "https://invalid.example/never-contact")
    results = [run(root=tmp_path), run(root=tmp_path)]
    client = MlflowClient(tracking_uri=(tmp_path / "mlruns").as_uri())
    all_run_ids, experiment_ids = set(), set()
    for result in results:
        assert result["runtime_validation_passed"]
        assert not result["champion_frozen"]
        run_ids = {result["parent_run_id"], *result["variant_run_ids"].values()}
        assert len(run_ids) == 10 and not all_run_ids & run_ids
        all_run_ids.update(run_ids)
        for run_id in run_ids:
            recorded = client.get_run(run_id)
            assert recorded.info.status == "FINISHED"
            experiment_ids.add(recorded.info.experiment_id)
            expected = tmp_path / "mlruns" / recorded.info.experiment_id / run_id
            assert Path(unquote(urlparse(recorded.info.artifact_uri).path)) == expected / "artifacts"
            assert (expected / "meta.yaml").exists()
            assert client.list_artifacts(run_id)
            artifact = "manifest.json" if run_id == result["parent_run_id"] else "summary.json"
            downloaded = json.loads(Path(client.download_artifacts(run_id, artifact)).read_text())
            if artifact == "manifest.json":
                assert downloaded["parent_run_id"] == run_id
            else:
                assert recorded.data.params["positive_class"] == "1"
                assert recorded.data.tags["partition"] == "development"
                assert recorded.data.tags["mlflow.parentRunId"] == result["parent_run_id"]
                assert "development_cv_average_precision_mean" in recorded.data.metrics
                assert downloaded["model"] == recorded.data.params["model"]
        compact = tmp_path / "reports/phase2_runs" / result["parent_run_id"]
        manifest = json.loads((compact / "manifest.json").read_text())
        assert manifest["oof_coverage_metric_reconciliation_serialization"] == "passed"
        assert manifest["variant_run_ids"] == result["variant_run_ids"]
        assert manifest["total_fits"] == 45
        assert manifest["input_hashes"]
        assert "Average precision mean" in (compact / "report.md").read_text()
    assert len(experiment_ids) == 1
    assert not (tmp_path / "mlruns/artifacts").exists()


def test_legacy_experiment_is_preserved_and_new_name_works_in_same_store(tmp_path):
    fixture_project(tmp_path)
    config_path = tmp_path / "configs/phase2.toml"
    from credit_risk.phase2 import load_phase2_config
    config = load_phase2_config(root=tmp_path)
    tracking = tmp_path / "mlruns"
    client = MlflowClient(tracking_uri=tracking.as_uri())
    experiment_id = client.create_experiment(
        config["experiment"], artifact_location=(tracking / "artifacts").as_uri())
    legacy = client.create_run(experiment_id)
    example = tmp_path / "legacy.txt"
    example.write_text("preserve legacy fixture artifacts")
    client.log_artifact(legacy.info.run_id, str(example))
    # Do not read or terminate the legacy run through ambiguous discovery.
    before = {str(path.relative_to(tracking)): path.read_bytes()
              for path in tracking.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="choose a new experiment name"):
        run(root=tmp_path)
    assert before == {str(path.relative_to(tracking)): path.read_bytes()
                      for path in tracking.rglob("*") if path.is_file()}
    config_path.write_text(config_path.read_text().replace(config["experiment"],
                                                         config["experiment"] + "-layout-v2"))
    result = run(root=tmp_path)
    for run_id in (result["parent_run_id"], *result["variant_run_ids"].values()):
        assert client.get_run(run_id).info.status == "FINISHED"
        assert client.list_artifacts(run_id)
    assert all((tracking / name).read_bytes() == content for name, content in before.items())


def test_real_tracking_marks_failed_runs_without_masking_fit_error(tmp_path):
    fixture_project(tmp_path)
    config = tmp_path / "configs/phase2.toml"
    config.write_text(config.read_text().replace("max_iter = 2000", "max_iter = -1"))
    with pytest.raises(ValueError, match="max_iter"):
        run(root=tmp_path)
    failure = json.loads(next((tmp_path / "artifacts/models/phase2").glob("*/failure.json")).read_text())
    client = MlflowClient(tracking_uri=(tmp_path / "mlruns").as_uri())
    assert client.get_run(failure["parent_run_id"]).info.status == "FAILED"
    assert client.get_run(failure["run_ids"]["dummy__raw__none"]).info.status == "FINISHED"
    assert client.get_run(failure["run_ids"]["logistic__raw__none"]).info.status == "FAILED"


def test_missing_metadata_during_cleanup_preserves_original_exception(tmp_path, monkeypatch):
    fixture_project(tmp_path)
    original = RuntimeError("original fit failure")
    backups = []

    def fail_fit(*args):
        # Temporarily move only this synthetic fixture's metadata to reproduce real
        # FileStore cleanup errors. Restore it below; tracking uses no mock client.
        for metadata in (tmp_path / "mlruns").glob("*/*/meta.yaml"):
            backup = metadata.with_name("saved-meta.yaml")
            metadata.rename(backup)
            backups.append((metadata, backup))
        # MLflow caches the parent's artifact repository after the first log.
        # Force a real filesystem error too, rather than relying on that cache.
        (args[-1].parent / "failure.json").mkdir()
        raise original

    monkeypatch.setattr("credit_risk.models.evaluation.evaluate_variant", fail_fit)
    try:
        with pytest.raises(RuntimeError, match="original fit failure") as caught:
            run(root=tmp_path)
        assert caught.value is original
        assert len(backups) == 2
        assert len(original.__notes__) == 3  # Child status, failure artifact, parent status.
    finally:
        for metadata, backup in backups:
            backup.rename(metadata)
    parent_id = next((tmp_path / "artifacts/models/phase2").iterdir()).name
    client = MlflowClient(tracking_uri=(tmp_path / "mlruns").as_uri())
    assert client.get_run(parent_id).info.status == "RUNNING"
