"""Bounded development-only search and the declared base-selection rule.

Each sampled hyperparameter setting is evaluated in four matched variants. The
variant choices count toward the family budget, and never create extra searches.
"""

from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import ParameterSampler, RandomizedSearchCV
from sklearn.utils.validation import check_is_fitted
from threadpoolctl import threadpool_limits

from credit_risk.artifacts import read_csv, write_csv, write_json
from credit_risk.features import PREDICTORS
from credit_risk.models.evaluation import METRICS, _jsonable, probability_metrics, summarize_oof
from credit_risk.models.inputs import validate_oof
from credit_risk.models.pipelines import build_pipeline, positive_probability

BUDGET_CEILINGS = {"logistic": 12, "random_forest": 15, "xgboost": 25}
VARIANTS = (("raw", "none"), ("raw", "balanced"),
            ("engineered", "none"), ("engineered", "balanced"))
DEFAULT_SPACES = {
    "logistic": {"C": [0.01, 0.1, 1.0, 10.0, 100.0]},
    "random_forest": {
        "n_estimators": [100, 200, 300], "max_depth": [6, 10, None],
        "min_samples_leaf": [5, 10, 20], "max_features": ["sqrt", 0.5, 0.8],
    },
    "xgboost": {
        "n_estimators": [100, 200, 300], "max_depth": [2, 3, 4],
        "learning_rate": [0.03, 0.07, 0.1], "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0], "min_child_weight": [1, 5, 10],
        "reg_alpha": [0.0, 0.1, 1.0], "reg_lambda": [1.0, 5.0, 10.0],
    },
}


def make_search_plan(seed=42, parameter_spaces=None, settings_per_family=None):
    """Return a serializable declaration to persist *before* fitting anything.

    Defaults reserve 12/12/24 configurations (60/60/120 CV fits). Sampling is
    reproducible; all four variants share the same sampled settings in a family.
    Caller-supplied spaces replace a family's defaults rather than augment them.
    """
    spaces = {**DEFAULT_SPACES, **(parameter_spaces or {})}
    counts = {"logistic": 3, "random_forest": 3, "xgboost": 6,
              **(settings_per_family or {})}
    if set(spaces) != set(BUDGET_CEILINGS) or set(counts) != set(BUDGET_CEILINGS):
        raise ValueError("Search plan must contain exactly the three model families")
    families = {}
    for family, ceiling in BUDGET_CEILINGS.items():
        count = counts[family]
        if not isinstance(count, int) or count <= 0 or count * len(VARIANTS) > ceiling:
            raise ValueError(f"{family} matched variants exceed configuration budget {ceiling}")
        sampled = list(ParameterSampler(spaces[family], n_iter=count, random_state=seed))
        if len(sampled) != count:
            raise ValueError(f"{family} parameter space cannot supply the declared settings")
        candidates = []
        for setting, parameters in enumerate(sampled):
            for feature_set, weighting in VARIANTS:
                candidates.append({
                    "candidate_id": f"{family}_{setting:02d}_{feature_set}_{weighting}",
                    "model": family, "setting": setting, "setting_id": f"{family}_{setting:02d}",
                    "feature_set": feature_set,
                    "weighting": weighting, "model_params": _jsonable(parameters),
                })
        families[family] = {
            "ceiling": ceiling, "configurations": len(candidates), "folds": 5,
            "cv_fits": len(candidates) * 5, "automatic_refits": 0,
            "parameter_space": _jsonable(spaces[family]), "candidates": candidates,
        }
    return {"seed": seed, "primary_metric": "average_precision", "refit": False,
            "early_stopping": False, "families": families}


class SearchCandidate(ClassifierMixin, BaseEstimator):
    """Cloneable classifier that constructs every learned step inside ``fit``.

    Metadata/variant parameters remain identifiable in ``cv_results_``; pipelines
    themselves need not be serialized as opaque parameter choices. This wrapper
    delegates weighting to the per-fit model implementation and accepts no global
    sample weights or validation set.
    """

    def __init__(self, model="logistic", feature_set="raw", weighting="none",
                 seed=42, model_params=None):
        self.model = model
        self.feature_set = feature_set
        self.weighting = weighting
        self.seed = seed
        self.model_params = model_params

    def fit(self, X, y):
        self.pipeline_ = build_pipeline(
            self.model, self.feature_set, self.weighting, self.seed, self.model_params)
        # A nonconverged trial is an invalid search result, not a quiet competitor.
        with threadpool_limits(limits=1), warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            started = time.perf_counter()
            self.pipeline_.fit(X, y)
            self.fit_seconds_ = time.perf_counter() - started
        model = self.pipeline_.named_steps["model"]
        if self.model == "logistic" and np.max(model.n_iter_) >= model.max_iter:
            raise RuntimeError("Logistic search fit reached max_iter")
        self.classes_ = self.pipeline_.classes_
        self.n_features_in_ = self.pipeline_.n_features_in_
        self.feature_names_in_ = self.pipeline_.feature_names_in_
        self.fit_class_counts_ = np.bincount(np.asarray(y, dtype=int), minlength=2)
        return self

    def predict_proba(self, X):
        check_is_fitted(self, "pipeline_")
        return self.pipeline_.predict_proba(X)

    def predict(self, X):
        check_is_fitted(self, "pipeline_")
        return self.pipeline_.predict(X)


def frozen_cv(records):
    """Validate and return the existing five folds; never allocate new folds."""
    frame = pd.DataFrame(records)
    required = {"client_id", "fold", "fingerprint", "default_next_month", *PREDICTORS}
    if not required <= set(frame) or frame.empty:
        raise ValueError("Search requires complete development records")
    if frame["client_id"].duplicated().any():
        raise ValueError("Development IDs must be unique")
    if set(frame["fold"]) != set(range(5)):
        raise ValueError("Search requires exactly five frozen development folds")
    if frame.groupby("fingerprint")["fold"].nunique().max() != 1:
        raise ValueError("Financial fingerprint crosses a frozen fold")
    y, folds = frame["default_next_month"].to_numpy(), frame["fold"].to_numpy()
    splits = []
    for fold in range(5):
        fit, validation = np.flatnonzero(folds != fold), np.flatnonzero(folds == fold)
        if set(y[fit]) != {0, 1} or set(y[validation]) != {0, 1}:
            raise ValueError("Every frozen fit/validation fold requires both classes")
        splits.append((fit, validation))
    return splits


def _signature(feature_set, weighting, parameters):
    return json.dumps([feature_set, weighting, _jsonable(parameters)], sort_keys=True)


def _score_candidate(estimator, X, y, capture=None):
    """Predict once with the common positive-class contract for all metrics."""
    started = time.perf_counter()
    probabilities = positive_probability(estimator, X)
    prediction_seconds = time.perf_counter() - started
    if capture is not None:
        capture(estimator, X, y, probabilities)
    scores = probability_metrics(y, probabilities)
    scores["log_loss"] *= -1
    scores["brier_score"] *= -1
    return {**scores, "fit_seconds": estimator.fit_seconds_,
            "predict_seconds": prediction_seconds}


def run_family_search(records, family, candidates, seed=42, n_jobs=1, output=None):
    """Run precisely the declared candidates on frozen development folds.

    ``score_seconds`` includes metric computation, and is not inference time.
    The callable scorer separately measures one prediction per fold. Full
    ``cv_results`` retain sklearn's negative-loss scoring convention;
    normalized candidate/fold tables report positive loss and sample fold SD.
    The scorer preserves OOF predictions without additional fits. They remain
    in ignored runtime output; compact summaries contain pooled metrics only.
    """
    if family not in BUDGET_CEILINGS:
        raise ValueError("Unknown model family")
    if not 0 < len(candidates) <= BUDGET_CEILINGS[family]:
        raise ValueError("Search exceeds family configuration budget")
    if n_jobs != 1:
        raise ValueError("OOF capture requires the declared single search worker")
    lookup, distributions = {}, []
    for candidate in candidates:
        if candidate["model"] != family:
            raise ValueError("Candidate family differs from requested family")
        signature = _signature(candidate["feature_set"], candidate["weighting"],
                               candidate["model_params"])
        if signature in lookup:
            raise ValueError("Duplicate candidate configuration")
        lookup[signature] = candidate
        distributions.append({name: [candidate[name]]
                              for name in ("feature_set", "weighting", "model_params")})
    if len({candidate["candidate_id"] for candidate in candidates}) != len(candidates):
        raise ValueError("Candidate IDs must be unique")
    if any(not isinstance(row["candidate_id"], str) or
           not row["candidate_id"].replace("_", "").replace("-", "").isalnum()
           for row in candidates):
        raise ValueError("Candidate IDs must be safe artifact filenames")
    cv = frozen_cv(records)
    frame = pd.DataFrame(records)
    oof = {row["candidate_id"]: [] for row in candidates}

    def capture(estimator, X, y, probabilities):
        candidate = lookup[_signature(estimator.feature_set, estimator.weighting,
                                      estimator.model_params)]
        for index, label, probability in zip(X.index, y, probabilities, strict=True):
            source = records[index]
            if int(label) != source["default_next_month"]:
                raise ValueError("Search scorer label differs from the development row")
            oof[candidate["candidate_id"]].append({
                key: source[key] for key in ("client_id", "fold", "fingerprint", "default_next_month")
            } | {"p_default": float(probability)})

    def score(estimator, X, y):
        return _score_candidate(estimator, X, y, capture)

    search = RandomizedSearchCV(
        SearchCandidate(model=family, seed=seed), distributions,
        n_iter=len(candidates), scoring=score,
        refit=False, cv=cv, random_state=seed, n_jobs=n_jobs,
        pre_dispatch=n_jobs, error_score="raise", return_train_score=False,
    )
    started = time.perf_counter()
    with threadpool_limits(limits=1), warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        search.fit(frame.loc[:, list(PREDICTORS)], frame["default_next_month"].to_numpy())
    runtime = time.perf_counter() - started
    results = search.cv_results_
    summaries, fold_metrics = [], []
    for index, params in enumerate(results["params"]):
        candidate = lookup[_signature(params["feature_set"], params["weighting"],
                                      params["model_params"])]
        row = dict(candidate)
        row.update({"sklearn_fit_seconds_mean": float(results["mean_fit_time"][index]),
                    "sklearn_fit_seconds_std": float(results["std_fit_time"][index]),
                    "score_seconds_mean": float(results["mean_score_time"][index]),
                    "score_seconds_std": float(results["std_score_time"][index]),
                    "rank_average_precision": int(results["rank_test_average_precision"][index])})
        for metric in (*METRICS, "fit_seconds", "predict_seconds"):
            sign = -1 if metric in {"log_loss", "brier_score"} else 1
            values = [float(results[f"split{fold}_test_{metric}"][index]) * sign
                      for fold in range(5)]
            if not np.isfinite(values).all():
                raise ValueError("Search produced a nonfinite fold metric")
            row[f"{metric}_mean"] = float(np.mean(values))
            row[f"{metric}_std"] = float(np.std(values, ddof=1))
        summaries.append(row)
        for fold, (fit, validation) in enumerate(cv):
            fold_metrics.append({
                "candidate_id": candidate["candidate_id"], "fold": fold,
                "fit_rows": len(fit), "validation_rows": len(validation),
                **{metric: float(results[f"split{fold}_test_{metric}"][index]) *
                   (-1 if metric in {"log_loss", "brier_score"} else 1)
                   for metric in (*METRICS, "fit_seconds", "predict_seconds")},
            })
    summaries.sort(key=lambda row: row["candidate_id"])
    if output is not None:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
    oof_artifacts = {}
    for row in summaries:
        identifier = row["candidate_id"]
        predictions = sorted(oof[identifier], key=lambda item: item["client_id"])
        validate_oof(predictions, records)
        if output is not None:
            relative = f"oof/{identifier}.csv"
            write_csv(output / relative, predictions, tuple(predictions[0]))
            predictions = read_csv(output / relative)
            validate_oof(predictions, records)
            oof_artifacts[identifier] = relative
        folds = [fold for fold in fold_metrics if fold["candidate_id"] == identifier]
        reconciled = summarize_oof(predictions, folds)
        row.update({key: value for key, value in reconciled.items() if key.endswith("_pooled_oof")})
    result = {
        "model": family, "candidates": summaries, "fold_metrics": fold_metrics,
        "cv_results": _jsonable(results), "fit_count": len(candidates) * 5,
        "automatic_refits": 0, "runtime_seconds": runtime, "n_jobs": n_jobs,
        "library_threads_per_fit": 1,
        "oof_artifacts": oof_artifacts,
        "oof_coverage_and_metric_reconciliation": "passed",
        "warnings": [{"category": warning.category.__name__, "message": str(warning.message)}
                     for warning in captured],
        "timing_note": "fit/predict seconds measured per fold; sklearn fit/score overhead recorded separately",
    }
    if output is not None:
        write_json(output / "search.json", result)
        write_json(output / "cv_results.json", result["cv_results"])
        compact = [{**row, "model_params": json.dumps(row["model_params"], sort_keys=True)}
                   for row in summaries]
        write_csv(output / "candidate_metrics.csv", compact, tuple(compact[0]))
        write_csv(output / "fold_metrics.csv", fold_metrics, tuple(fold_metrics[0]))
    return result


def select_base_candidate(rows, ap_tolerance=0.01, log_loss_tolerance=0.001):
    """Apply AP eligibility, a declared small-loss tolerance, then simplicity.

    Within the small-loss set: logistic < random forest < XGBoost; then fewer
    trees, shallower trees, fewer predictors, no weighting, lower exact log loss,
    lower measured inference time, higher AP and stable candidate ID. Runtime
    never substitutes for the AP/loss conditions or exact-loss tie-break.
    """
    if not rows or ap_tolerance < 0 or log_loss_tolerance < 0:
        raise ValueError("Selection requires candidates and nonnegative tolerances")
    for row in rows:
        if (row["model"] not in BUDGET_CEILINGS or
                not np.isfinite([row["average_precision_mean"], row["log_loss_mean"]]).all()):
            raise ValueError("Selection requires finite development candidate metrics")
    best_ap = max(row["average_precision_mean"] for row in rows)
    ap_close = [row for row in rows if row["average_precision_mean"] >=
                best_ap - ap_tolerance - 1e-12]
    best_loss = min(row["log_loss_mean"] for row in ap_close)
    loss_close = [row for row in ap_close if row["log_loss_mean"] <=
                  best_loss + log_loss_tolerance + 1e-12]
    complexity = {"logistic": 0, "random_forest": 1, "xgboost": 2}

    def tie_key(row):
        parameters = row.get("model_params", {})
        depth = parameters.get("max_depth", 0)
        return (complexity[row["model"]], parameters.get("n_estimators", 0),
                float("inf") if depth is None else depth,
                row["feature_set"] != "raw", row["weighting"] != "none",
                row["log_loss_mean"], row.get("predict_seconds_mean", float("inf")),
                -row["average_precision_mean"], row["candidate_id"])

    selected = min(loss_close, key=tie_key)
    return {
        "selected": selected, "best_average_precision": best_ap,
        "ap_tolerance": ap_tolerance, "log_loss_tolerance": log_loss_tolerance,
        "ap_eligible_candidate_ids": sorted(row["candidate_id"] for row in ap_close),
        "minimum_eligible_log_loss": best_loss,
        "small_loss_candidate_ids": sorted(row["candidate_id"] for row in loss_close),
        "selection_rule": "mean development CV AP eligibility, lower log loss, then declared simplicity and runtime tie-breaks",
        "tolerance_is_significance_test": False,
    }
