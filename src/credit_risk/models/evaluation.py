"""Fixed development-fold evaluation; no model selection or held-out access."""

import math
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import (
    average_precision_score, brier_score_loss, confusion_matrix, log_loss, roc_auc_score,
)
from threadpoolctl import threadpool_limits

from credit_risk.artifacts import file_sha256, json_bytes, sha256_bytes, write_csv, write_json
from credit_risk.features import PREDICTORS
from credit_risk.models.inputs import validate_oof
from credit_risk.models.pipelines import build_pipeline, fold_class_weights, positive_probability

METRICS = ("average_precision", "roc_auc", "log_loss", "brier_score")


def probability_metrics(y, p):
    y, p = np.asarray(y), np.asarray(p, dtype=np.float64)
    if (y.ndim != 1 or p.shape != y.shape or set(y.tolist()) != {0, 1}
            or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any()):
        raise ValueError("Metrics require both binary classes and finite positive-class probabilities")
    return {
        "average_precision": float(average_precision_score(y, p, pos_label=1)),
        "roc_auc": float(roc_auc_score(y, p)),
        "log_loss": float(log_loss(y, np.column_stack((1 - p, p)), labels=[0, 1])),
        "brier_score": float(brier_score_loss(y, p, pos_label=1)),
    }


def hard_reference(y, prediction):
    """Classification reference only; never treated as probability estimates."""
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    return {"true_negative": int(tn), "false_positive": int(fp),
            "false_negative": int(fn), "true_positive": int(tp),
            "accuracy": float((tn + tp) / len(y)),
            "recall_positive": float(tp / (tp + fn)),
            "precision_positive": float(tp / (tp + fp)) if tp + fp else None}


def summarize_oof(rows, fold_metrics):
    """Recompute fold and pooled metrics directly from reloaded predictions."""
    frame = pd.DataFrame(rows)
    summary = {}
    for fold in range(5):
        part = frame.loc[frame["fold"].astype(int) == fold]
        actual = probability_metrics(part["default_next_month"].astype(int), part["p_default"])
        recorded = next(row for row in fold_metrics if int(row["fold"]) == fold)
        for metric in METRICS:
            if not np.isclose(actual[metric], recorded[metric], atol=1e-12, rtol=0):
                raise ValueError(f"Saved OOF metric mismatch: fold={fold}, metric={metric}")
    for metric in (*METRICS, "fit_seconds", "predict_seconds"):
        values = [row[metric] for row in fold_metrics]
        summary[f"{metric}_mean"] = float(np.mean(values))
        summary[f"{metric}_std"] = float(np.std(values, ddof=1))
    pooled = probability_metrics(frame["default_next_month"].astype(int), frame["p_default"])
    summary.update({f"{metric}_pooled_oof": value for metric, value in pooled.items()})
    return summary


def _jsonable(value):
    # Imputer parameters contain NaN as a missing-value sentinel. Represent that
    # configuration explicitly without admitting non-finite reported measurements.
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def evaluate_variant(records, model, feature_set, weighting, seed, model_params, output):
    """Fit exactly five independent pipelines, save and reconcile all OOF rows."""
    output.mkdir(parents=True, exist_ok=False)
    frame = pd.DataFrame(records)
    X = frame.loc[:, list(PREDICTORS)]
    y = frame["default_next_month"].to_numpy(dtype=int)
    folds = frame["fold"].to_numpy(dtype=int)
    metrics, predictions, evidence = [], [], []
    majority = []
    started = time.perf_counter()
    for fold in range(5):
        fit, validation = np.flatnonzero(folds != fold), np.flatnonzero(folds == fold)
        if (set(frame.iloc[fit]["fingerprint"]) & set(frame.iloc[validation]["fingerprint"])):
            raise ValueError("Financial fingerprint crosses a frozen fold")
        pipeline = build_pipeline(model, feature_set, weighting, seed, model_params)
        with threadpool_limits(limits=1), warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            start = time.perf_counter()
            pipeline.fit(X.iloc[fit], y[fit])
            fit_seconds = time.perf_counter() - start
            start = time.perf_counter()
            p = positive_probability(pipeline, X.iloc[validation])
            predict_seconds = time.perf_counter() - start
        warning_rows = [{"category": item.category.__name__, "message": str(item.message)}
                        for item in captured]
        convergence_warnings = sum(issubclass(item.category, ConvergenceWarning)
                                   for item in captured)
        estimator = pipeline.named_steps["model"]
        iterations = getattr(estimator, "n_iter_", np.array([], dtype=int)).tolist()
        converged = (convergence_warnings == 0 and
                     (model != "logistic" or max(iterations) < estimator.max_iter))
        fold_result = {"fold": fold, "fit_rows": len(fit), "validation_rows": len(validation),
                       **probability_metrics(y[validation], p), "fit_seconds": fit_seconds,
                       "predict_seconds": predict_seconds,
                       "convergence_warning_count": convergence_warnings,
                       "converged": converged}
        metrics.append(fold_result)
        model_path = output / f"fold_{fold}.joblib"
        joblib.dump(pipeline, model_path)
        restored = positive_probability(joblib.load(model_path), X.iloc[validation])
        if not np.allclose(p, restored, atol=1e-12, rtol=0):
            raise ValueError("Serialized pipeline predictions differ")
        for index, probability in zip(validation, p, strict=True):
            row = records[index]
            predictions.append({key: row[key] for key in
                                ("client_id", "fold", "fingerprint", "default_next_month")} |
                               {"p_default": float(probability)})
        majority_class = int(np.argmax(np.bincount(y[fit], minlength=2)))
        majority.append({"fold": fold, "fit_majority_class": majority_class,
                         **hard_reference(y[validation], np.full(len(validation), majority_class))})
        names = pipeline.named_steps["preprocessor"].get_feature_names_out().tolist()
        evidence.append({
            "fold": fold, "fit_ids_sha256": sha256_bytes(json_bytes(
                frame.iloc[fit]["client_id"].tolist())),
            "validation_ids_sha256": sha256_bytes(json_bytes(
                frame.iloc[validation]["client_id"].tolist())),
            "fit_class_counts": np.bincount(y[fit], minlength=2).tolist(),
            "effective_class_weights": (
                {0: 1.0, 1: estimator.scale_pos_weight_} if model == "xgboost" else
                fold_class_weights(y[fit]) if weighting == "balanced" else {0: 1.0, 1: 1.0}),
            "fitted_model_parameters": _jsonable(
                estimator.estimator_.get_params() if model == "xgboost" else estimator.get_params()),
            "resolved_pipeline_parameters": _jsonable(pipeline.get_params(deep=True)),
            "encoded_feature_names": names, "n_iter": iterations, "warnings": warning_rows,
            "serialization_predictions_match": True, "pipeline_sha256": file_sha256(model_path),
        })
    predictions.sort(key=lambda row: row["client_id"])
    validate_oof(predictions, records)
    oof_path = output / "oof_predictions.csv"
    write_csv(oof_path, predictions, tuple(predictions[0]))
    # Re-read bytes rather than reconciling only the in-memory predictions.
    from credit_risk.artifacts import read_csv
    reloaded = read_csv(oof_path)
    validate_oof(reloaded, records)
    summary = summarize_oof(reloaded, metrics)
    summary.update({"model": model, "feature_set": feature_set, "weighting": weighting,
                    "development_rows": len(records), "runtime_seconds": time.perf_counter() - started,
                    "all_folds_converged": all(row["converged"] for row in metrics)})
    write_csv(output / "fold_metrics.csv", metrics, tuple(metrics[0]))
    write_json(output / "fold_evidence.json", evidence)
    write_json(output / "summary.json", summary)
    if model == "dummy":
        write_json(output / "majority_hard_reference.json", majority)
    # All diagnostics use held-out-within-development OOF probabilities only.
    diagnostic = pd.DataFrame(predictions)
    diagnostic["squared_error"] = (diagnostic["default_next_month"] - diagnostic["p_default"]) ** 2
    diagnostic["error_at_0_5"] = (diagnostic["p_default"] >= 0.5).astype(int) != diagnostic["default_next_month"]
    cases = diagnostic.sort_values(["squared_error", "client_id"], ascending=[False, True]).head(10)
    write_csv(output / "development_error_cases.csv", cases.to_dict("records"), tuple(cases.columns))
    write_json(output / "development_errors.json", {
        "scope": "development OOF only; diagnostic threshold 0.5, no policy selection",
        "classification_at_0_5": hard_reference(diagnostic["default_next_month"],
                                                (diagnostic["p_default"] >= 0.5).astype(int)),
        "by_fold": [{"fold": fold, "errors_at_0_5": int(part["error_at_0_5"].sum()),
                     "rows": len(part)} for fold, part in diagnostic.groupby("fold")],
    })
    return summary, metrics
