"""Fold-fitted, named preprocessing for the fixed Phase 2 comparisons.

Only ``fit`` rows determine medians, scaling, status vocabularies and balanced
class weights. The selector supports training exports containing extra metadata,
but always drops those columns before any fitted transformation or estimator.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted

from credit_risk.data.schema import RAW_PREDICTORS, STATUS_COLUMNS
from credit_risk.features import PREDICTORS


def feature_columns(feature_set: str) -> list[str]:
    """Return a fresh allowlist in the frozen feature-contract order."""
    if feature_set == "raw":
        return list(RAW_PREDICTORS)
    if feature_set == "engineered":
        return list(PREDICTORS)
    raise ValueError("feature_set must be 'raw' or 'engineered'")


class FinancialPredictorSelector(TransformerMixin, BaseEstimator):
    """Select numeric financial inputs by name and reject structural failures.

    Missing values remain NaN for fold-fitted imputers. No population statistic
    is computed here. Extra input columns never enter the predictor matrix.
    """

    def __init__(self, columns: tuple[str, ...]):
        self.columns = columns

    def _select(self, X: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(X, pd.DataFrame):
            raise ValueError("Predictors require a pandas DataFrame with named columns")
        if not X.columns.is_unique:
            raise ValueError("Predictor input has duplicate column names")
        missing = set(self.columns) - set(X.columns)
        if missing:
            raise ValueError(f"Missing financial predictors: {sorted(missing)}")
        try:
            selected = X.loc[:, list(self.columns)].astype(float)
        except (TypeError, ValueError) as error:
            raise ValueError("Financial predictors must be numeric or missing") from error
        values = selected.to_numpy()
        if np.isinf(values).any():
            raise ValueError("Financial predictors must be finite or missing")
        return selected

    def fit(self, X: pd.DataFrame, y: Any = None) -> FinancialPredictorSelector:
        self._select(X)
        self.feature_names_in_ = np.asarray(self.columns, dtype=object)
        self.n_features_in_ = len(self.columns)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self, "feature_names_in_")
        return self._select(X)

    def get_feature_names_out(self, input_features: Any = None) -> np.ndarray:
        check_is_fitted(self, "feature_names_in_")
        return self.feature_names_in_.copy()


def fold_class_weights(y: Any) -> dict[int, float]:
    """Compute sklearn balanced weights from exactly the supplied fit labels.

    Each class receives n_fit / (2 * n_class). Calling this with validation
    labels would be a caller error; pipelines use sklearn's per-fit computation.
    """
    labels = np.asarray(y)
    if labels.ndim != 1 or set(np.unique(labels)) != {0, 1}:
        raise ValueError("Fit labels must be one-dimensional and contain classes 0 and 1")
    return {
        label: float(len(labels) / (2 * np.count_nonzero(labels == label)))
        for label in (0, 1)
    }


class FoldLocalXGBClassifier(ClassifierMixin, BaseEstimator):
    """CPU XGBoost whose positive weight is recomputed on every fit.

    Composition keeps learned weights out of cloneable constructor parameters.
    The base pipeline's imputation and category vocabulary are also fit-local.
    Import is lazy so the accepted Phase 2 runtime remains usable without XGBoost.
    """

    def __init__(self, weighting="none", seed=42, model_params=None):
        self.weighting = weighting
        self.seed = seed
        self.model_params = model_params

    def fit(self, X, y):
        from xgboost import XGBClassifier

        fold_class_weights(y)  # validate both binary classes before computing a ratio
        if self.weighting not in {"none", "balanced"}:
            raise ValueError("weighting must be 'none' or 'balanced'")
        parameters = dict(self.model_params or {})
        protected = {"scale_pos_weight", "random_state", "n_jobs", "early_stopping_rounds",
                     "callbacks", "device", "tree_method", "objective", "eval_set"}
        if protected & parameters.keys():
            raise ValueError("XGBoost fit/concurrency/weight settings are protected")
        self.fit_class_counts_ = np.bincount(np.asarray(y, dtype=int), minlength=2)
        self.scale_pos_weight_ = (float(self.fit_class_counts_[0] / self.fit_class_counts_[1])
                                  if self.weighting == "balanced" else 1.0)
        defaults = {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.05,
                    "subsample": 1.0, "colsample_bytree": 1.0, "min_child_weight": 1,
                    "reg_alpha": 0.0, "reg_lambda": 1.0}
        defaults.update(parameters)
        self.estimator_ = XGBClassifier(
            objective="binary:logistic", tree_method="hist", device="cpu", n_jobs=1,
            random_state=self.seed, scale_pos_weight=self.scale_pos_weight_, **defaults)
        self.estimator_.fit(X, y)
        self.classes_ = self.estimator_.classes_
        self.n_features_in_ = self.estimator_.n_features_in_
        if hasattr(self.estimator_, "feature_names_in_"):
            self.feature_names_in_ = self.estimator_.feature_names_in_
        return self

    def predict_proba(self, X):
        check_is_fitted(self, "estimator_")
        return self.estimator_.predict_proba(X)

    def predict(self, X):
        check_is_fitted(self, "estimator_")
        return self.estimator_.predict(X)


def build_pipeline(
    model: str,
    feature_set: str,
    weighting: str,
    seed: int = 42,
    model_params: dict[str, Any] | None = None,
) -> Pipeline:
    """Build an unfitted baseline with fixed single-worker model defaults.

    Repayment statuses preserve distinct special codes through one-hot encoding.
    Numeric output follows allowlist order, then status outputs follow oldest to
    newest with categories learned on fit rows. Empty training columns remain
    present (imputed to zero); unknown held-out categories encode to all zeros.
    """
    columns = feature_columns(feature_set)
    if weighting not in {"none", "balanced"}:
        raise ValueError("weighting must be 'none' or 'balanced'")
    if model not in {"dummy", "logistic", "random_forest", "xgboost"}:
        raise ValueError("Unknown model family")
    if model == "dummy" and weighting != "none":
        raise ValueError("The constant-prior dummy is an unweighted probability reference")
    overrides = dict(model_params or {})
    protected = {"class_weight", "random_state", "n_jobs", "strategy", "scale_pos_weight",
                 "early_stopping_rounds", "callbacks", "eval_set"} & overrides.keys()
    if protected:
        raise ValueError(f"Use the pipeline arguments for protected settings: {sorted(protected)}")

    numeric = [column for column in columns if column not in STATUS_COLUMNS]
    numeric_steps = [("imputer", SimpleImputer(strategy="median", keep_empty_features=True))]
    if model == "logistic":
        numeric_steps.append(("scaler", StandardScaler()))
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    preprocessor = ColumnTransformer(
        [
            ("numeric", Pipeline(numeric_steps), numeric),
            ("categorical", categorical_pipeline, list(STATUS_COLUMNS)),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    ).set_output(transform="pandas")
    class_weight = "balanced" if weighting == "balanced" else None
    if model == "dummy":
        estimator = DummyClassifier(strategy="prior", random_state=seed, **overrides)
    elif model == "logistic":
        parameters = {"C": 1.0, "solver": "lbfgs", "max_iter": 2000, "tol": 1e-4}
        parameters.update(overrides)
        estimator = LogisticRegression(
            class_weight=class_weight, random_state=seed, **parameters
        )
    elif model == "random_forest":
        parameters = {
            "n_estimators": 200,
            "max_depth": None,
            "min_samples_leaf": 5,
            "max_features": "sqrt",
            "bootstrap": True,
        }
        parameters.update(overrides)
        estimator = RandomForestClassifier(
            class_weight=class_weight, random_state=seed, n_jobs=1, **parameters
        )
    else:
        estimator = FoldLocalXGBClassifier(weighting=weighting, seed=seed, model_params=overrides)
    return Pipeline([
        ("features", FinancialPredictorSelector(tuple(columns))),
        ("preprocessor", preprocessor),
        ("model", estimator),
    ])


def positive_probability(estimator: Any, X: Any) -> np.ndarray:
    """Map predict_proba columns using classes_, never a fixed column offset."""
    classes = np.asarray(estimator.classes_)
    if classes.ndim != 1 or len(classes) != 2 or set(classes) != {0, 1}:
        raise ValueError("Estimator must expose binary classes 0 and 1")
    probabilities = np.asarray(estimator.predict_proba(X), dtype=float)
    if probabilities.ndim != 2 or probabilities.shape != (len(X), len(classes)):
        raise ValueError("predict_proba shape does not agree with rows and classes")
    if (
        not np.isfinite(probabilities).all()
        or (probabilities < 0).any()
        or (probabilities > 1).any()
        or not np.allclose(probabilities.sum(axis=1), 1.0)
    ):
        raise ValueError("predict_proba must contain finite probability distributions")
    return probabilities[:, int(np.flatnonzero(classes == 1)[0])]
