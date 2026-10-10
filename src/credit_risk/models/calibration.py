"""Held-out probability calibration with an immutable fitted base (sklearn 1.7)."""

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

from credit_risk.models.pipelines import positive_probability

ORDER = ("raw", "sigmoid", "isotonic")


def verify_fit_scope(development_ids, calibration_ids, policy_ids, test_ids):
    groups = [set(ids) for ids in (development_ids, calibration_ids, policy_ids, test_ids)]
    if any(not group for group in groups):
        raise ValueError("Every partition must be present")
    for i, group in enumerate(groups):
        if any(group & other for other in groups[i + 1:]):
            raise ValueError("Partition IDs overlap")


def fit_mappings(base, X, y, *, partition, calibration_ids, development_ids):
    if partition != "calibration":
        raise ValueError("Mappings may fit only on calibration")
    if (len(X) != len(calibration_ids) or len(set(calibration_ids)) != len(X)
            or set(calibration_ids) & set(development_ids)):
        raise ValueError("Calibration/base fit scope is not disjoint")
    y = np.asarray(y)
    if y.shape != (len(X),) or set(y.tolist()) != {0, 1}:
        raise ValueError("Calibration requires both binary classes")
    before_hash = joblib.hash(base)
    before_predictions = positive_probability(base, X).copy()
    variants = {"raw": base}
    for method in ORDER[1:]:
        mapped = CalibratedClassifierCV(FrozenEstimator(base), method=method, ensemble=False)
        mapped.fit(X, y)
        variants[method] = mapped
    if joblib.hash(base) != before_hash:
        raise ValueError("Calibration mutated the fitted base")
    if not np.array_equal(before_predictions, positive_probability(base, X)):
        raise ValueError("Calibration changed base predictions")
    return variants


def select_mapping(metrics, *, partition="policy_validation", tolerance=0.005):
    if partition != "policy_validation" or tolerance != 0.005 or set(metrics) != set(ORDER):
        raise ValueError("Fixed selection requires policy validation and tolerance 0.005")
    losses = {name: float(metrics[name]["log_loss"]) for name in ORDER}
    if any(not np.isfinite(loss) or loss < 0 for loss in losses.values()):
        raise ValueError("Selection log losses must be finite and nonnegative")
    minimum = min(losses.values())
    # Numeric roundoff at the declared inclusive tolerance is not a new tolerance.
    return next(name for name in ORDER if losses[name] <= minimum + tolerance + 1e-15)


def reliability_bins(y, p):
    y, p = np.asarray(y), np.asarray(p, dtype=float)
    if (y.shape != p.shape or y.ndim != 1 or not len(y)
            or not set(y.tolist()) <= {0, 1} or not np.isfinite(p).all()
            or ((p < 0) | (p > 1)).any()):
        raise ValueError("Invalid reliability inputs")
    indices = np.minimum((p * 10).astype(int), 9)
    rows = []
    for index in range(10):
        mask = indices == index
        count = int(mask.sum())
        rows.append({"bin": index, "lower": index / 10, "upper": (index + 1) / 10,
                     "count": count, "mean_probability": float(p[mask].mean()) if count else None,
                     "observed_rate": float(y[mask].mean()) if count else None,
                     "sparse": count < 100})
    return rows
