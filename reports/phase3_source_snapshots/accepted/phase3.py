"""Phase 3 development search, profiling and guarded base-model selection.

Family searches can finish independently. Selection requires all three families
from the same declared plan, inputs, code and environment; partial evidence can
never produce a selected base model. The accepted Phase 2 tracker is reused.
"""

from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import time
import tomllib

from credit_risk.artifacts import (
    file_sha256, json_bytes, read_csv, sha256_bytes, write_json,
)
from credit_risk.config import PROJECT_ROOT, load_config
from credit_risk.features import PREDICTORS
from credit_risk.models.inputs import load_development
from credit_risk.phase2 import (
    _local_experiment, _mark_failed, check_dependencies, execution_context,
)

XGB_PIN = "3.0.5"


def check_xgboost():
    check_dependencies()
    try:
        version = importlib.metadata.version("xgboost-cpu")
    except importlib.metadata.PackageNotFoundError as error:
        raise ModuleNotFoundError(
            "Phase 3 needs xgboost-cpu==3.0.5. Run bash scripts/bootstrap_phase3.sh; "
            "see docs/reproduction-phase3.md") from error
    if version != XGB_PIN:
        raise ValueError(f"Expected xgboost-cpu {XGB_PIN}, found {version}")
    import xgboost
    if xgboost.__version__ != XGB_PIN:
        raise ValueError("XGBoost import and distribution versions disagree")


def load_phase3_config(path="configs/phase3.toml", root=PROJECT_ROOT):
    root = Path(root).resolve()
    config = tomllib.loads((root / path).read_text())
    expected = {"base_config", "export_manifest", "split_receipt", "tracking_dir",
                "output_dir", "reports_dir", "experiment", "profile_receipt", "seed",
                "threads", "search_workers", "ap_tolerance", "log_loss_tolerance",
                "settings_per_family", "parameter_spaces"}
    if set(config) != expected or (config["seed"], config["threads"],
                                   config["search_workers"]) != (42, 1, 1):
        raise ValueError("Phase 3 requires seed 42, one search worker and one library thread")
    if config["ap_tolerance"] != 0.01 or config["log_loss_tolerance"] != 0.001:
        raise ValueError("Phase 3 selection tolerances differ from the declared rule")
    for key, prefix in (("tracking_dir", "mlruns"), ("output_dir", "artifacts/models/phase3"),
                        ("reports_dir", "reports/phase3_runs"), ("profile_receipt", "reports")):
        if not (root / config[key]).resolve().is_relative_to(root / prefix):
            raise ValueError(f"{key} must stay inside {prefix}")
    forest = config["parameter_spaces"]["random_forest"]
    forest["max_depth"] = [None if value == "None" else value for value in forest["max_depth"]]
    return config


def declare_plan(path="configs/phase3.toml", root=PROJECT_ROOT):
    from credit_risk.models.search import make_search_plan
    config = load_phase3_config(path, root)
    plan = make_search_plan(config["seed"], config["parameter_spaces"],
                            config["settings_per_family"])
    plan.update({"search_workers": 1, "library_threads": 1,
                 "ap_tolerance": config["ap_tolerance"],
                 "log_loss_tolerance": config["log_loss_tolerance"],
                 "simplicity_order": ["family: logistic, forest, XGBoost", "fewer trees",
                    "shallower trees (unbounded last)", "raw predictors", "unweighted",
                    "lower exact log loss", "faster measured inference", "higher AP", "ID"],
                 "profile_fits": 5,
                 "oof_and_all_development_refits": "separate, only after complete selection"})
    digest = sha256_bytes(json_bytes(plan))
    relative = f"artifacts/phase3_plans/{digest}.json"
    write_json(Path(root) / relative, plan, frozen=True)
    return {"plan_path": relative, "plan_sha256": digest, "plan": plan}


def _inputs(config, root, stage):
    base = load_config(root / config["base_config"])
    # Preserve the same honest string-routing disclosure without parsing held-out labels.
    log = root / "docs/test-exposure-log.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as stream:
        stream.write(f"\n| {datetime.now(timezone.utc).isoformat()} — Phase 3 {stage} | "
                     "Full label CSV strings traversed for ID routing; only development "
                     f"outcomes interpreted | split `{file_sha256(root / base['split_manifest'])}`; "
                     f"labels `{file_sha256(root / base['processed_dir'] / 'labels.csv')}` | "
                     "No held-out outcome conversion, summaries, fitting or evaluation |\n")
    return load_development(base, config["export_manifest"], config["split_receipt"], root)


def _context(path, config, hashes, root, plan):
    context = execution_context(path, config, hashes, root)
    # Include Phase 3 inputs without altering the accepted Phase 2 implementation.
    for name in ("requirements-phase3.in", "scripts/bootstrap_phase3.sh"):
        file = root / name
        if file.exists():
            context["code_file_hashes"][name] = file_sha256(file)
    context["code_tree_sha256"] = sha256_bytes(json_bytes(context["code_file_hashes"]))
    for obsolete in ("variant_count", "total_fits", "search_configurations"):
        context.pop(obsolete, None)
    context.update({"phase": 3, "plan_sha256": plan["plan_sha256"],
                    "plan_path": plan["plan_path"], "complete_bundle_frozen": False})
    context["runtime_root"] = str(root)
    return context


def _tracker(config, root, name):
    from mlflow import MlflowClient
    tracking = (root / config["tracking_dir"]).resolve()
    client = MlflowClient(tracking_uri=tracking.as_uri())
    experiment = _local_experiment(client, config["experiment"], tracking)
    run = client.create_run(experiment, tags={"mlflow.runName": name,
                                            "partition": "development", "phase": "3"})
    return client, experiment, run.info.run_id


def _params(client, run_id, context, extra):
    for key, value in {"seed": 42, "search_workers": 1, "library_threads": 1,
                       "positive_class": 1, "git_commit": context["git_commit"] or "unavailable",
                       "code_tree_sha256": context["code_tree_sha256"],
                       "plan_sha256": context["plan_sha256"],
                       "dependency_lock_sha256": context["dependency_lock_sha256"],
                       "input_hashes_sha256": sha256_bytes(json_bytes(context["input_hashes"])),
                       **extra}.items():
        client.log_param(run_id, key, value)


def _verify_profile(config, hashes, root, context):
    receipt = root / config["profile_receipt"]
    if not receipt.exists():
        raise ValueError("Run phase3-profile before the XGBoost final search")
    profile = json.loads(receipt.read_text())
    if (profile.get("input_hashes") != hashes or profile.get("xgboost_version") != XGB_PIN
            or profile.get("dependency_lock_sha256") != file_sha256(root / "requirements.lock")
            or profile.get("code_tree_sha256") != context["code_tree_sha256"]
            or profile.get("plan_sha256") != context["plan_sha256"]
            or profile.get("fit_count") != 5 or not profile.get("serialization_passed")):
        raise ValueError("XGBoost profile does not match current inputs/environment")
    return profile


def _fit_development(pipeline, X, y):
    """Treat a nonconverged development refit as a failure before serialization."""
    import warnings
    import numpy as np
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        pipeline.fit(X, y)
    fitted = pipeline.named_steps["model"]
    if isinstance(fitted, LogisticRegression) and np.max(fitted.n_iter_) >= fitted.max_iter:
        raise ValueError("All-development logistic refit reached max_iter")
    return pipeline


def profile(path="configs/phase3.toml", root=PROJECT_ROOT):
    """Five small 30-tree development fits; measured separately from final budget."""
    check_xgboost()
    from credit_risk.models.evaluation import evaluate_variant
    root = Path(root).resolve()
    config = load_phase3_config(path, root)
    plan = declare_plan(path, root)
    records, hashes = _inputs(config, root, "XGBoost smoke/profile")
    context = _context(path, config, hashes, root, plan)
    client, _, run_id = _tracker(config, root, "phase3-xgboost-profile-30-trees")
    output = root / config["output_dir"] / run_id
    try:
        summary, _ = evaluate_variant(records, "xgboost", "engineered", "none", 42,
                                      {"n_estimators": 30, "max_depth": 3}, output)
        receipt = {**context, "run_id": run_id, "xgboost_version": XGB_PIN,
                   "fit_count": 5, "serialization_passed": True, "summary": summary,
                   "output": str(output.relative_to(root)), "cpu_threads": 1,
                   "linear_tree_count_search_fit_seconds_estimate":
                       summary["fit_seconds_mean"] * 300 / 30 * 120,
                   "runtime_estimate_note": "approximate planning estimate; depth and feature choices also affect runtime",
                   "concurrency_decision": "one worker and one library thread; no oversubscription",
                   "range_review": "100–300 trees, depths 2–4; check measured runtime before search"}
        write_json(output / "profile.json", receipt)
        write_json(root / config["profile_receipt"], receipt)
        _params(client, run_id, context, {"fit_count": 5, "purpose": "profile"})
        client.log_artifacts(run_id, str(output))
        client.set_terminated(run_id, status="FINISHED")
        return receipt
    except Exception as error:
        _mark_failed(client, run_id, error)
        raise


def run_search(family, path="configs/phase3.toml", root=PROJECT_ROOT):
    check_dependencies()
    if family == "xgboost":
        check_xgboost()
    from credit_risk.models.search import run_family_search
    root = Path(root).resolve()
    config, plan = load_phase3_config(path, root), declare_plan(path, root)
    if family not in plan["plan"]["families"]:
        raise ValueError("Search family must be logistic, random_forest or xgboost")
    records, hashes = _inputs(config, root, f"{family} bounded search")
    context = _context(path, config, hashes, root, plan)
    profile_receipt = _verify_profile(config, hashes, root, context) if family == "xgboost" else None
    client, experiment, run_id = _tracker(config, root, f"phase3-search-{family}")
    output = root / config["output_dir"] / run_id
    compact = root / config["reports_dir"] / run_id
    compact.mkdir(parents=True, exist_ok=False)
    child_ids = {}
    try:
        write_json(compact / "plan.json", plan["plan"])
        write_json(compact / "execution_context.json", context)
        _params(client, run_id, context, {"model": family, "purpose": "bounded search"})
        result = run_family_search(records, family, plan["plan"]["families"][family]["candidates"],
                                   seed=42, n_jobs=1, output=output)
        for candidate in result["candidates"]:
            child = client.create_run(experiment, tags={"mlflow.parentRunId": run_id,
                "mlflow.runName": candidate["candidate_id"], "partition": "development"})
            child_id = child.info.run_id
            child_ids[candidate["candidate_id"]] = child_id
            try:
                _params(client, child_id, context, {"model": family,
                        "feature_set": candidate["feature_set"], "weighting": candidate["weighting"],
                        "resolved_model_parameters": json.dumps(candidate["model_params"], sort_keys=True)})
                for name, value in candidate.items():
                    if isinstance(value, (float, int)) and not isinstance(value, bool):
                        client.log_metric(child_id, f"development_cv_{name}", value)
                for fold in result["fold_metrics"]:
                    if fold["candidate_id"] == candidate["candidate_id"]:
                        for name in ("average_precision", "roc_auc", "log_loss", "brier_score",
                                     "fit_seconds", "predict_seconds"):
                            client.log_metric(child_id, f"development_cv_fold_{name}",
                                              fold[name], step=fold["fold"])
                child_path = compact / f"{candidate['candidate_id']}.json"
                write_json(child_path, candidate)
                client.log_artifact(child_id, str(child_path))
                client.set_terminated(child_id, status="FINISHED")
            except Exception as error:
                _mark_failed(client, child_id, error)
                raise
        for name in ("candidate_metrics.csv", "fold_metrics.csv", "cv_results.json", "search.json"):
            (compact / name).write_bytes((output / name).read_bytes())
        receipt = {**context, "parent_run_id": run_id, "candidate_run_ids": child_ids,
                   "model": family, "fit_count": result["fit_count"], "automatic_refits": 0,
                   "runtime_seconds": result["runtime_seconds"], "development_rows": len(records),
                   "fold_rows": {str(f): sum(r["fold"] == f for r in records) for f in range(5)},
                   "profile_run_id": profile_receipt["run_id"] if profile_receipt else None,
                   "status": "FINISHED", "base_selected": False,
                   "artifacts": {str(f.relative_to(root)): file_sha256(f)
                                 for f in sorted(output.rglob("*")) if f.is_file()},
                   "compact_artifacts": {f.name: file_sha256(f)
                                         for f in sorted(compact.iterdir()) if f.is_file()}}
        write_json(compact / "manifest.json", receipt)
        client.log_artifacts(run_id, str(compact))
        client.set_terminated(run_id, status="FINISHED")
        return {"parent_run_id": run_id, "model": family, "fit_count": result["fit_count"],
                "runtime_seconds": result["runtime_seconds"], "base_selected": False,
                "manifest": str((compact / "manifest.json").relative_to(root))}
    except Exception as error:
        try:
            write_json(compact / "failure.json", {"error_type": type(error).__name__,
                                                   "run_id": run_id, "candidate_run_ids": child_ids})
        except Exception as cleanup:
            error.add_note(f"Failure receipt write failed: {type(cleanup).__name__}")
        _mark_failed(client, run_id, error)
        raise


def load_searches(run_ids, config, root):
    """Require complete same-provenance family results before any selection."""
    if len(run_ids) != 3 or len(set(run_ids)) != 3:
        raise ValueError("Selection requires three distinct completed family search runs")
    receipts, results = [], []
    for run_id in run_ids:
        if len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
            raise ValueError("Invalid MLflow run ID")
        directory = root / config["reports_dir"] / run_id
        receipt = json.loads((directory / "manifest.json").read_text())
        if receipt["status"] != "FINISHED":
            raise ValueError("Search is incomplete")
        for relative, digest in receipt["artifacts"].items():
            if file_sha256(root / relative) != digest:
                raise ValueError("Saved search artifact changed")
        for relative, digest in receipt["compact_artifacts"].items():
            if file_sha256(directory / relative) != digest:
                raise ValueError("Compact search evidence changed")
        receipts.append(receipt)
        results.append(json.loads((directory / "search.json").read_text()))
    if {r["model"] for r in receipts} != {"logistic", "random_forest", "xgboost"}:
        raise ValueError("Selection requires logistic, forest and XGBoost evidence")
    for key in ("plan_sha256", "input_hashes"):
        if any(r[key] != receipts[0][key] for r in receipts):
            raise ValueError(f"Search provenance differs: {key}; do not combine runs")
    reference = next(r for r in receipts if r["model"] == "xgboost")
    for receipt in receipts:
        for key in ("dependency_lock_sha256", "code_tree_sha256"):
            if receipt[key] != reference[key]:
                try:
                    validate_search_reuse(receipt, reference, root)
                except ValueError as error:
                    raise ValueError(f"Search provenance differs: {key}; {error}") from error
    return receipts, results


def validate_search_reuse(source, target, root):
    """Permit only proven additive-XGBoost/orchestration changes for old CV runs.

    Original contexts remain immutable. Numerical source, plan, inputs, Python
    and every installed existing distribution must agree exactly. A source
    snapshot binds the reviewed runner changes to the actual original bytes.
    This validates reuse of completed fits; it does not regenerate evidence.
    """
    import ast
    import re

    for key in ("plan_sha256", "input_hashes", "config_sha256", "config", "python",
                "platform", "seed", "threads", "positive_class"):
        if key not in source or source[key] != target.get(key):
            raise ValueError(f"Cannot reuse search: {key} changed or is missing")
    for key in ("dependencies", "code_file_hashes"):
        if not source.get(key) or not target.get(key):
            raise ValueError(f"Cannot reuse search: missing {key}")
    def normalize(deps):
        return {re.sub(r"[-_.]+", "-", k).lower(): v for k, v in deps.items()}
    old_dependencies, new_dependencies = normalize(source["dependencies"]), normalize(target["dependencies"])
    if any(new_dependencies.get(k) != v for k, v in old_dependencies.items()):
        raise ValueError("Cannot reuse search: an existing dependency changed or disappeared")
    added = {k: v for k, v in new_dependencies.items() if k not in old_dependencies}
    if added not in ({}, {"xgboost-cpu": XGB_PIN}):
        raise ValueError("Cannot reuse search: only the pinned XGBoost dependency may be added")
    old_files, new_files = source["code_file_hashes"], target["code_file_hashes"]
    for provenance in (source, target):
        if (sha256_bytes(json_bytes(provenance["code_file_hashes"])) != provenance["code_tree_sha256"]
                or provenance["code_file_hashes"].get("requirements.lock") !=
                provenance["dependency_lock_sha256"]):
            raise ValueError("Cannot reuse search: inconsistent code/lock fingerprints")
    changed = sorted(k for k in old_files.keys() | new_files.keys()
                     if old_files.get(k) != new_files.get(k))
    allowed = {"src/credit_risk/phase3.py", "src/credit_risk/__main__.py", "requirements.lock"}
    if set(changed) - allowed:
        raise ValueError("Cannot reuse search: numerical or unlisted source/config files changed")
    identical = (not changed and not added and
                 source["dependency_lock_sha256"] == target["dependency_lock_sha256"])
    if not identical and source.get("model") not in {"logistic", "random_forest"}:
        raise ValueError("Only completed logistic/forest searches support additive reuse")
    if source["dependency_lock_sha256"] != target["dependency_lock_sha256"] and not added:
        raise ValueError("Cannot reuse search: a lock change requires the pinned XGBoost addition")
    if added:
        if source["dependency_lock_sha256"] == target["dependency_lock_sha256"]:
            raise ValueError("Cannot reuse search: XGBoost addition requires an updated validated lock")
        lock = Path(root) / "requirements.lock"
        if not lock.exists() or file_sha256(lock) != target["dependency_lock_sha256"]:
            raise ValueError("Cannot reuse search: current lock bytes do not match target provenance")
        pins = normalize(dict(re.findall(r"(?m)^([A-Za-z0-9_.-]+)==([^\s;]+)", lock.read_text())))
        if any(pins.get(k) != v for k, v in new_dependencies.items()
               if k != "credit-risk-decision-science"):
            raise ValueError("Cannot reuse search: target installed dependency pins are absent from lock")
    snapshot_digest = None
    if "src/credit_risk/phase3.py" in changed:
        snapshot = Path(root) / "provenance/original_code/src/credit_risk/phase3.py"
        current = Path(root) / "src/credit_risk/phase3.py"
        if (not snapshot.exists() or file_sha256(snapshot) != old_files.get("src/credit_risk/phase3.py")
                or file_sha256(current) != new_files.get("src/credit_risk/phase3.py")):
            raise ValueError("Cannot reuse search: original/current runner snapshot hash mismatch")
        snapshot_digest = file_sha256(snapshot)
        before, after = ast.parse(snapshot.read_text()), ast.parse(current.read_text())
        old_functions = {n.name: n for n in before.body if isinstance(n, ast.FunctionDef)}
        new_functions = {n.name: n for n in after.body if isinstance(n, ast.FunctionDef)}
        def dump(node):
            return ast.dump(node, include_attributes=False)
        for name, node in old_functions.items():
            if name not in {"load_searches", "select"} and (
                    name not in new_functions or dump(node) != dump(new_functions[name])):
                raise ValueError(f"Cannot reuse search: protected runner function {name} changed")
        # Protect module imports/constants and the actual selection/reference/fit
        # statements inside select, while allowing provenance-only guard/metadata edits.
        globals_before = [n for n in before.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.Assign))]
        globals_after = [n for n in after.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.Assign))]
        if [dump(n) for n in globals_before] != [dump(n) for n in globals_after]:
            raise ValueError("Cannot reuse search: runner imports/constants changed")

        def selection_blocks(function):
            blocks, collecting = [], False
            for node in function.body:
                names = ([n.id for n in node.targets if isinstance(n, ast.Name)]
                         if isinstance(node, ast.Assign) else [])
                if "candidates" in names:
                    collecting = True
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and (
                        isinstance(node.value.func, ast.Name) and node.value.func.id == "_tracker"):
                    collecting = False
                if collecting:
                    blocks.append(dump(node))
                if isinstance(node, ast.Try):
                    for child in node.body:
                        if isinstance(child, ast.For) and isinstance(child.target, ast.Tuple):
                            for statement in child.body:
                                if (isinstance(statement, ast.Assign) and any(
                                        isinstance(t, ast.Name) and t.id == "metadata"
                                        for t in statement.targets)):
                                    break
                                blocks.append(dump(statement))
            for node in ast.walk(function):
                if isinstance(node, ast.Assign) and any(
                    isinstance(name, ast.Name) and name.id in {"records", "hashes", "frame", "X", "y"}
                    for target in node.targets for name in ast.walk(target)
                ):
                    blocks.append("fit_input_assignment:" + dump(node))
            return blocks

        if selection_blocks(old_functions["select"]) != selection_blocks(new_functions["select"]):
            raise ValueError("Cannot reuse search: selection or numerical refit statements changed")
    unchanged = {k: v for k, v in old_files.items() if k not in allowed}
    return {"mode": "identical" if identical else "verified_additive_xgboost_orchestration",
            "source_run_id": source.get("parent_run_id"),
            "original_code_tree_sha256": source["code_tree_sha256"],
            "current_code_tree_sha256": target["code_tree_sha256"],
            "original_dependency_lock_sha256": source["dependency_lock_sha256"],
            "current_dependency_lock_sha256": target["dependency_lock_sha256"],
            "unchanged_scientific_code_sha256": sha256_bytes(json_bytes(unchanged)),
            "allowed_changed_files": changed, "added_dependencies": added,
            "original_runner_snapshot_sha256": snapshot_digest,
            "original_dependencies": source["dependencies"], "current_dependencies": target["dependencies"],
            "additional_search_fits": 0}


def select(run_ids, path="configs/phase3.toml", root=PROJECT_ROOT):
    check_xgboost()
    import joblib
    import numpy as np
    import pandas as pd
    from threadpoolctl import threadpool_limits
    from credit_risk.models.evaluation import _jsonable, evaluate_variant
    from credit_risk.models.pipelines import build_pipeline, positive_probability
    from credit_risk.models.search import select_base_candidate

    root = Path(root).resolve()
    config = load_phase3_config(path, root)
    receipts, results = load_searches(run_ids, config, root)
    plan = declare_plan(path, root)
    if plan["plan_sha256"] != receipts[0]["plan_sha256"]:
        raise ValueError("Current plan differs from completed searches")
    records, hashes = _inputs(config, root, "base selection and development-only refits")
    context = _context(path, config, hashes, root, plan)
    reuse_proofs = {r["parent_run_id"]: validate_search_reuse(r, context, root) for r in receipts}
    candidates = [row for result in results for row in result["candidates"]]
    decision = select_base_candidate(candidates, config["ap_tolerance"], config["log_loss_tolerance"])
    chosen = decision["selected"]
    references = {chosen["candidate_id"]: chosen}
    for family in ("logistic", "random_forest", "xgboost"):
        winner = min((c for c in candidates if c["model"] == family),
                     key=lambda c: (-c["average_precision_mean"], c["log_loss_mean"], c["candidate_id"]))
        references[winner["candidate_id"]] = winner
    references["dummy_prior"] = {"candidate_id": "dummy_prior", "model": "dummy",
        "feature_set": "raw", "weighting": "none", "model_params": {}}
    client, _, run_id = _tracker(config, root, "phase3-base-selection-development-refits")
    output = root / config["output_dir"] / run_id
    compact = root / config["reports_dir"] / run_id
    output.mkdir(parents=True, exist_ok=False)
    compact.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        write_json(compact / "selection.json", decision)
        frame = pd.DataFrame(records)
        X, y = frame.loc[:, list(PREDICTORS)], frame["default_next_month"].to_numpy(dtype=int)
        bundles = {}
        for candidate_id, candidate in references.items():
            folder = output / candidate_id
            summary, folds = evaluate_variant(records, candidate["model"], candidate["feature_set"],
                candidate["weighting"], 42, candidate["model_params"], folder)
            if not summary["all_folds_converged"]:
                raise ValueError("Reference OOF fit did not converge")
            if candidate["model"] != "dummy":
                expected = {int(row["fold"]): row for result in results
                            for row in result["fold_metrics"] if row["candidate_id"] == candidate_id}
                for fold in folds:
                    for metric in ("average_precision", "roc_auc", "log_loss", "brier_score"):
                        if not np.isclose(fold[metric], expected[fold["fold"]][metric], atol=1e-12, rtol=0):
                            raise ValueError("Search and preserved OOF metrics do not reconcile")
            pipeline = build_pipeline(candidate["model"], candidate["feature_set"],
                                       candidate["weighting"], 42, candidate["model_params"])
            with threadpool_limits(limits=1):
                start = time.perf_counter()
                _fit_development(pipeline, X, y)
                fit_seconds = time.perf_counter() - start
                predictions = positive_probability(pipeline, X)
                artifact = folder / "development_pipeline.joblib"
                joblib.dump(pipeline, artifact)
                restored = positive_probability(joblib.load(artifact), X)
                if not np.allclose(predictions, restored, atol=1e-12, rtol=0):
                    raise ValueError("Development model save/load predictions differ")
            metadata = {**context, "candidate": candidate, "training_partition": "development",
                "training_rows": len(records), "training_ids_sha256": sha256_bytes(json_bytes(
                    frame["client_id"].tolist())), "fit_seconds": fit_seconds,
                "pipeline_sha256": file_sha256(artifact), "positive_class": 1,
                "feature_columns": list(pipeline.named_steps["features"].columns),
                "encoded_feature_names": pipeline[:-1].get_feature_names_out().tolist(),
                "resolved_pipeline_parameters": _jsonable(pipeline.get_params(deep=True)),
                "role": "selected_base" if candidate_id == chosen["candidate_id"] else "reference",
                "save_load_predictions_match": True, "complete_bundle_frozen": False}
            fitted = pipeline.named_steps["model"]
            metadata["search_provenance"] = next((
                {"run_id": r["parent_run_id"], "code_tree_sha256": r["code_tree_sha256"],
                 "dependency_lock_sha256": r["dependency_lock_sha256"], "dependencies": r["dependencies"]}
                for r in receipts if r["model"] == candidate["model"]), None)
            if candidate["model"] == "xgboost":
                metadata["fitted_xgboost_parameters"] = _jsonable(fitted.estimator_.get_params())
                metadata["fit_class_counts"] = fitted.fit_class_counts_.tolist()
                metadata["scale_pos_weight"] = fitted.scale_pos_weight_
            write_json(folder / "metadata.json", metadata)
            bundles[candidate_id] = {"pipeline": str(artifact.relative_to(root)),
                                      "metadata": str((folder / "metadata.json").relative_to(root)),
                                      "role": metadata["role"], "fit_seconds": fit_seconds}
        receipt = {**context, "parent_run_id": run_id, "search_run_ids": run_ids,
                   "search_reuse_proofs": reuse_proofs,
                   "selected_candidate_id": chosen["candidate_id"], "bundles": bundles,
                   "oof_refits": 5 * len(references), "all_development_refits": len(references),
                   "search_cv_fits": sum(r["fit_count"] for r in receipts),
                   "runtime_seconds": time.perf_counter() - started,
                   "base_selected": True, "complete_bundle_frozen": False,
                   "artifacts": {str(f.relative_to(root)): file_sha256(f)
                                 for f in sorted(output.rglob("*")) if f.is_file()}}
        write_json(compact / "manifest.json", receipt)
        _params(client, run_id, context, {"selected_candidate_id": chosen["candidate_id"]})
        client.log_artifacts(run_id, str(compact))
        client.log_artifacts(run_id, str(output), artifact_path="development_bundles")
        client.set_terminated(run_id, status="FINISHED")
        return receipt
    except Exception as error:
        _mark_failed(client, run_id, error)
        raise


def verify(run_id, path="configs/phase3.toml", root=PROJECT_ROOT):
    """Verify completed family artifacts without outcomes, fitting or new selection."""
    from mlflow import MlflowClient
    root = Path(root).resolve()
    config = load_phase3_config(path, root)
    if len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
        raise ValueError("Invalid MLflow run ID")
    directory = root / config["reports_dir"] / run_id
    receipt = json.loads((directory / "manifest.json").read_text())
    for relative, digest in receipt["artifacts"].items():
        if file_sha256(root / relative) != digest:
            raise ValueError("Artifact checksum mismatch")
    for relative, digest in receipt.get("compact_artifacts", {}).items():
        if file_sha256(directory / relative) != digest:
            raise ValueError("Compact artifact checksum mismatch")
    client = MlflowClient(tracking_uri=(root / config["tracking_dir"]).as_uri())
    for identifier in [run_id, *receipt.get("candidate_run_ids", {}).values()]:
        if client.get_run(identifier).info.status != "FINISHED":
            raise ValueError("MLflow run is not FINISHED")
    if "candidate_run_ids" in receipt:
        result = json.loads((directory / "search.json").read_text())
        metrics = read_csv(directory / "fold_metrics.csv")
        if len(metrics) != receipt["fit_count"] or result["fit_count"] != receipt["fit_count"]:
            raise ValueError("Search fit counts disagree")
    return {"run_id": run_id, "artifact_hashes_and_tracking": "passed",
            "fit_count": receipt.get("fit_count"), "base_selected": receipt.get("base_selected", False)}
