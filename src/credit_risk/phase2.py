"""Development-only baseline CLI and explicit local MLflow provenance."""

from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import time
import tomllib
from urllib.parse import unquote, urlparse

from credit_risk.artifacts import file_sha256, json_bytes, sha256_bytes, write_csv, write_json
from credit_risk.config import PROJECT_ROOT, load_config
from credit_risk.models.inputs import load_development

MODEL_PINS = {
    "numpy": "2.2.6", "pandas": "2.3.3", "scipy": "1.15.3", "scikit-learn": "1.7.2",
    "joblib": "1.5.2", "threadpoolctl": "3.6.0", "mlflow-skinny": "3.3.2",
}


def load_phase2_config(path="configs/phase2.toml", root=PROJECT_ROOT):
    path = Path(root) / path
    config = tomllib.loads(path.read_text())
    expected = {"base_config", "export_manifest", "split_receipt", "tracking_dir", "output_dir",
                "reports_dir", "experiment", "seed", "threads", "logistic", "random_forest"}
    if set(config) != expected or config["seed"] != 42 or config["threads"] != 1:
        raise ValueError("Phase 2 requires the documented config, seed 42 and one thread")
    root = Path(root).resolve()
    for key, prefix in (("tracking_dir", "mlruns"), ("output_dir", "artifacts/models/phase2"),
                        ("reports_dir", "reports/phase2_runs")):
        path = (root / config[key]).resolve()
        if not path.is_relative_to(root / prefix):
            raise ValueError(f"{key} must remain within project {prefix}")
    return config


def variants():
    """Nine prespecified comparisons; no data-dependent configuration search."""
    return [("dummy", "raw", "none")] + [
        (model, feature_set, weighting)
        for model in ("logistic", "random_forest")
        for feature_set in ("raw", "engineered")
        for weighting in ("none", "balanced")
    ]


def check_dependencies():
    mismatches = []
    for package, expected in MODEL_PINS.items():
        try:
            installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            installed = "missing"
        if installed != expected:
            mismatches.append(f"{package}: expected {expected}, found {installed}")
    if mismatches:
        raise ModuleNotFoundError("Phase 2 dependencies unavailable/incompatible: " +
                                  "; ".join(mismatches) + ". See docs/reproduction-phase2.md")


def check_inputs(path="configs/phase2.toml", root=PROJECT_ROOT):
    config = load_phase2_config(path, root)
    base = load_config(Path(root) / config["base_config"])
    log_input_access("baseline-inputs", base, root)
    records, hashes = load_development(base, config["export_manifest"], config["split_receipt"], root)
    return {"scope": "development only", "development_rows": len(records),
            "fold_rows": {str(fold): sum(row["fold"] == fold for row in records)
                          for fold in range(5)},
            "input_hashes": hashes, "frozen_inputs_verified": True,
            "heldout_outcomes_interpreted": False, "predictive_fit": False}


def log_input_access(stage, base, root):
    """Record CSV traversal before reading; do not misdescribe it as test evaluation."""
    root = Path(root)
    log = root / "docs/test-exposure-log.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    split_hash = file_sha256(root / base["split_manifest"])
    label_hash = file_sha256(root / base["processed_dir"] / "labels.csv")
    with log.open("a") as stream:
        stream.write(f"\n| {timestamp} — Phase 2 {stage} requested | Full label CSV row strings "
                     "will be traversed to route IDs; only development outcomes are interpreted | "
                     f"split `{split_hash}`, labels `{label_hash}` | Held-out outcomes are not "
                     "converted, summarized, fitted or evaluated; no final-test evidence |\n")


def execution_context(config_path, config, input_hashes, root):
    root = Path(root)
    paths = sorted({*root.glob("src/**/*.py"), *root.glob("scripts/*.py"),
                    *root.glob("scripts/*.sh"), *root.glob("configs/*.toml"),
                    root / "pyproject.toml", root / "requirements.lock",
                    root / "requirements-phase2.in"})
    files = {str(path.relative_to(root)): file_sha256(path) for path in paths}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True,
                                   text=True, check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {
        "started_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "development only",
        "git_commit": commit, "git_dirty": dirty,
        "code_tree_sha256": sha256_bytes(json_bytes(files)), "code_file_hashes": files,
        "input_hashes": input_hashes, "config": config,
        "config_sha256": file_sha256(root / config_path),
        "dependency_lock_sha256": file_sha256(root / "requirements.lock"),
        "dependencies": dict(sorted((dist.metadata["Name"], dist.version)
                                    for dist in importlib.metadata.distributions())),
        "python": platform.python_version(), "platform": platform.platform(),
        "seed": config["seed"], "threads": 1, "positive_class": 1,
        "fold_std_definition": "sample standard deviation (ddof=1), five folds",
        "search_configurations": 0, "variant_count": 9, "total_fits": 45,
        "champion_frozen": False,
    }


def comparisons(summaries):
    lookup = {(row["model"], row["feature_set"], row["weighting"]): row for row in summaries}
    result = []
    for model in ("logistic", "random_forest"):
        for weighting in ("none", "balanced"):
            pairs = [("engineered_minus_raw", (model, "engineered", weighting),
                      (model, "raw", weighting))]
            for feature_set in ("raw", "engineered"):
                # Emit weighting contrasts once per feature set.
                if weighting == "none":
                    pairs.append(("balanced_minus_none", (model, feature_set, "balanced"),
                                  (model, feature_set, "none")))
            for name, right, left in pairs:
                result.append({"comparison": name, "model": model,
                               "right": "/".join(right), "left": "/".join(left),
                               **{f"{metric}_mean_delta": lookup[right][f"{metric}_mean"] -
                                  lookup[left][f"{metric}_mean"] for metric in
                                  ("average_precision", "roc_auc", "log_loss", "brier_score")}})
    return result


def _report(summaries, contrasts, parent_id, majority):
    lines = ["# Phase 2 measured development baselines", "",
             f"MLflow parent run: `{parent_id}`. Five frozen development folds; no champion frozen.",
             "Sample fold standard deviations are descriptive, not confidence intervals.", "",
             "| Model | Features | Weighting | Average precision mean ± SD | ROC-AUC | Log loss | Brier | Fit seconds mean |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in summaries:
        lines.append(f"| {row['model']} | {row['feature_set']} | {row['weighting']} | "
                     f"{row['average_precision_mean']:.5f} ± {row['average_precision_std']:.5f} | "
                     f"{row['roc_auc_mean']:.5f} | {row['log_loss_mean']:.5f} | "
                     f"{row['brier_score_mean']:.5f} | {row['fit_seconds_mean']:.3f} |")
    lines += ["", "These are fold averages. Separate pooled OOF metrics are in comparison.csv;",
              "pooled ranking metrics need not equal the mean of the fold metrics.", "",
              "| Controlled comparison | Variant | Δ average precision | Δ log loss |",
              "| --- | --- | ---: | ---: |"]
    for row in contrasts:
        lines.append(f"| {row['comparison']} | {row['right']} | "
                     f"{row['average_precision_mean_delta']:+.5f} | {row['log_loss_mean_delta']:+.5f} |")
    lines += ["", "Majority-class hard-prediction reference (separate from probability metrics):", "",
              "| Fold | Fit majority class | Default recall | Accuracy (reference only) |",
              "| ---: | ---: | ---: | ---: |"]
    for row in majority:
        lines.append(f"| {row['fold']} | {row['fit_majority_class']} | "
                     f"{row['recall_positive']:.5f} | {row['accuracy']:.5f} |")
    lines += ["", "Positive AP changes favor the right variant; negative log-loss changes favor it.",
              "Weighting changes the fit objective and may worsen probability quality. No benefit is assumed.",
              "Convergence, classification diagnostics and development-only worst squared-error cases",
              "are saved per variant. A 0.5 diagnostic cutoff is not a lending policy.",
              "The majority-class hard reference is separate from the constant-prior probability baseline.",
              "No calibration, policy-validation, or final-test outcomes contributed to these comparisons.",
              "These historical existing-account results are not validated new-loan underwriting evidence.", ""]
    return "\n".join(lines)


def _local_experiment(client, name, tracking):
    """Use FileStore's default layout; never silently reuse a legacy artifact root."""
    experiment = client.get_experiment_by_name(name)
    if experiment is None:
        return client.create_experiment(name)
    location = urlparse(experiment.artifact_location)
    artifact_path = (Path(unquote(location.path)).resolve()
                     if location.scheme == "file" and location.netloc in {"", "localhost"}
                     else None)
    if artifact_path != tracking / experiment.experiment_id:
        raise ValueError(
            f"Experiment {name!r} uses a custom artifact location. Preserve its runs and "
            "artifacts and choose a new experiment name in configs/phase2.toml; "
            "see docs/reproduction-phase2.md for legacy-layout recovery."
        )
    return experiment.experiment_id


def _mark_failed(client, run_id, original_error):
    """Failure cleanup is best effort and cannot replace the triggering error."""
    try:
        client.set_terminated(run_id, status="FAILED")
    except Exception as cleanup_error:
        original_error.add_note(
            f"MLflow FAILED cleanup for run {run_id} also raised {type(cleanup_error).__name__}"
        )


def run(path="configs/phase2.toml", root=PROJECT_ROOT):
    # Stop before outcomes or tracking writes if dependencies cannot run.
    check_dependencies()
    from mlflow import MlflowClient
    from credit_risk.models.evaluation import evaluate_variant
    root = Path(root)
    config = load_phase2_config(path, root)
    base = load_config(root / config["base_config"])
    log_input_access("baselines", base, root)
    records, input_hashes = load_development(
        base, config["export_manifest"], config["split_receipt"], root)
    context = execution_context(path, config, input_hashes, root)
    # An explicit local client cannot inherit a remote tracking URI or active run.
    tracking = (root / config["tracking_dir"]).resolve()
    client = MlflowClient(tracking_uri=tracking.as_uri())
    experiment_id = _local_experiment(client, config["experiment"], tracking)
    parent = client.create_run(experiment_id, tags={"mlflow.runName": "phase2-fixed-baselines",
                                                  "partition": "development"})
    parent_id = parent.info.run_id
    output = root / config["output_dir"] / parent_id
    compact = root / config["reports_dir"] / parent_id
    summaries, all_metrics, run_ids = [], [], {}
    started = time.perf_counter()
    try:
        output.mkdir(parents=True, exist_ok=False)
        compact.mkdir(parents=True, exist_ok=False)
        write_json(output / "execution_context.json", context)
        client.log_artifact(parent_id, str(output / "execution_context.json"))
        for model, feature_set, weighting in variants():
            name = f"{model}__{feature_set}__{weighting}"
            child = client.create_run(experiment_id, tags={"mlflow.parentRunId": parent_id,
                                      "mlflow.runName": name, "partition": "development"})
            child_id = child.info.run_id
            run_ids[name] = child_id
            try:
                for key, value in {"model": model, "feature_set": feature_set,
                                   "weighting": weighting, "seed": config["seed"],
                                   "threads": 1, "positive_class": 1,
                                   "source_sha256": input_hashes[base["workbook"]],
                                   "split_sha256": input_hashes[base["split_manifest"]],
                                   "feature_sha256": input_hashes[base["feature_contract"]],
                                   "code_tree_sha256": context["code_tree_sha256"],
                                   "git_commit": context["git_commit"] or "unavailable"}.items():
                    client.log_param(child_id, key, value)
                result, folds = evaluate_variant(records, model, feature_set, weighting,
                                                 config["seed"], config.get(model, {}), output / name)
                # Full resolved estimator + preprocessing parameters and fit weights are artifacts.
                result["mlflow_run_id"] = child_id
                summaries.append(result)
                for fold in folds:
                    all_metrics.append({"variant": name, "mlflow_run_id": child_id, **fold})
                    for metric in ("average_precision", "roc_auc", "log_loss", "brier_score",
                                   "fit_seconds", "predict_seconds"):
                        client.log_metric(child_id, f"development_cv_fold_{metric}",
                                          fold[metric], step=fold["fold"])
                for key, value in result.items():
                    if isinstance(value, (float, int)) and not isinstance(value, bool):
                        client.log_metric(child_id, f"development_cv_{key}", value)
                client.log_artifacts(child_id, str(output / name))
                client.set_terminated(child_id, status="FINISHED")
            except Exception as error:
                _mark_failed(client, child_id, error)
                raise
        contrasts = comparisons(summaries)
        write_csv(compact / "comparison.csv", summaries, tuple(summaries[0]))
        write_csv(compact / "fold_metrics.csv", all_metrics, tuple(all_metrics[0]))
        write_csv(compact / "controlled_comparisons.csv", contrasts, tuple(contrasts[0]))
        majority = json.loads((output / "dummy__raw__none/majority_hard_reference.json").read_text())
        write_csv(compact / "majority_hard_reference.csv", majority, tuple(majority[0]))
        diagnostics = []
        for model, feature_set, weighting in variants():
            name = f"{model}__{feature_set}__{weighting}"
            error = json.loads((output / name / "development_errors.json").read_text())
            diagnostics.append({"variant": name, **error["classification_at_0_5"]})
        write_csv(compact / "development_diagnostics.csv", diagnostics, tuple(diagnostics[0]))
        report_path = compact / "report.md"
        report_path.write_text(_report(summaries, contrasts, parent_id, majority))
        passed = all(row["all_folds_converged"] for row in summaries)
        manifest = {**context, "parent_run_id": parent_id, "variant_run_ids": run_ids,
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    "runtime_seconds": time.perf_counter() - started,
                    "all_folds_converged": passed,
                    "oof_coverage_metric_reconciliation_serialization": "passed",
                    "artifacts": {str(file.relative_to(root)): file_sha256(file)
                                  for file in sorted(output.rglob("*")) if file.is_file()},
                    "compact_artifacts": {file.name: file_sha256(file)
                                          for file in sorted(compact.iterdir()) if file.is_file()}}
        write_json(compact / "manifest.json", manifest)
        client.log_artifacts(parent_id, str(compact))
        client.set_tag(parent_id, "all_folds_converged", str(passed))
        client.set_terminated(parent_id, status="FINISHED")
        return {"parent_run_id": parent_id, "variant_run_ids": run_ids,
                "report": str(report_path.relative_to(root)), "runtime_validation_passed": passed,
                "champion_frozen": False}
    except Exception as error:
        # Neither failure-artifact writes nor status cleanup may mask the original error.
        try:
            write_json(output / "failure.json", {"error_type": type(error).__name__,
                       "error_stage": "development baseline evaluation or local artifact write",
                       "run_ids": run_ids, "parent_run_id": parent_id, "context": context})
            client.log_artifact(parent_id, str(output / "failure.json"))
        except Exception as cleanup_error:
            error.add_note(f"Failure artifact cleanup also raised {type(cleanup_error).__name__}")
        _mark_failed(client, parent_id, error)
        raise
