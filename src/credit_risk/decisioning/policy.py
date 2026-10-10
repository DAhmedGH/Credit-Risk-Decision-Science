"""Synthetic utility decisions selected on policy validation and serialized before test.

The label is an existing-account benchmark outcome, assumed unchanged by hypothetical
allocation. Utility is dimensionless and cannot establish profit or a causal effect.
Abstention is the positive *detection* action; default (label 1) is the positive outcome.
"""

from dataclasses import asdict, dataclass
import math

import numpy as np


def _finite_nonnegative(value, name):
    if isinstance(value, (bool, str)):
        raise ValueError(f"{name} must be a finite nonnegative number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite nonnegative number") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return number


@dataclass(frozen=True)
class Scenario:
    """Net gain/loss exclude the separately charged accepted-account processing cost."""

    scenario_id: str = "base"
    gain: float = 50.0
    loss: float = 500.0
    cost: float = 0.0

    def __post_init__(self):
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("Scenario requires a nonempty scenario_id")
        for name in ("gain", "loss", "cost"):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name))
        if self.gain + self.loss <= 0 or not math.isfinite(self.gain + self.loss):
            raise ValueError("gain + loss must be finite and positive")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, definition):
        return cls(**definition)


def _probabilities(probabilities):
    try:
        p = np.asarray(probabilities, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("Probabilities must be a nonempty finite vector within [0, 1]") from exc
    if (p.ndim != 1 or not len(p) or not np.isfinite(p).all()
            or np.any((p < 0) | (p > 1))):
        raise ValueError("Probabilities must be a nonempty finite vector within [0, 1]")
    return p


def _labels(labels, p):
    y = np.asarray(labels)
    if y.shape != p.shape or not np.isin(y, [0, 1]).all():
        raise ValueError("Labels must match probabilities and contain only binary 0/1 outcomes")
    return y.astype(np.int64)


def _selection_partition(partition):
    if partition != "policy_validation":
        raise ValueError("Policy cutoffs may be selected only on policy_validation")


@dataclass(frozen=True)
class FrozenPolicy:
    """A scalar cutoff is reused verbatim: p < cutoff accepts; boundary ties abstain."""

    policy_id: str
    kind: str = "cutoff"
    cutoff: float | None = None
    target_fraction: float | None = None
    selected_on: str = "policy_validation"

    def __post_init__(self):
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise ValueError("Policy requires a nonempty policy_id")
        if self.kind not in {"all", "none", "cutoff"}:
            raise ValueError("Policy kind must be all, none, or cutoff")
        if self.kind == "cutoff":
            value = _finite_nonnegative(self.cutoff, "cutoff")
            if value > 1:
                raise ValueError("cutoff must be within [0, 1]")
            object.__setattr__(self, "cutoff", value)
        elif self.cutoff is not None:
            raise ValueError("Explicit all/none policies cannot specify a cutoff")
        if self.target_fraction is not None:
            value = _finite_nonnegative(self.target_fraction, "target_fraction")
            if not 0 < value < 1:
                raise ValueError("target_fraction must be strictly within (0, 1)")
            object.__setattr__(self, "target_fraction", value)
        _selection_partition(self.selected_on)

    def accept(self, probabilities):
        p = _probabilities(probabilities)
        if self.kind == "all":
            return np.ones(len(p), dtype=bool)
        if self.kind == "none":
            return np.zeros(len(p), dtype=bool)
        return p < self.cutoff

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, definition):
        return cls(**definition)


def analytic_cutoff(scenario):
    """Zero cutoff implements abstain-all for G <= C; EU equality abstains."""
    if scenario.gain <= scenario.cost:
        return 0.0
    return (scenario.gain - scenario.cost) / (scenario.gain + scenario.loss)


def expected_utility(probabilities, scenario):
    """Accept-action expected utility, before an allocation decision is applied."""
    p = _probabilities(probabilities)
    return (1 - p) * scenario.gain - p * scenario.loss - scenario.cost


def fraction_policy(probabilities, fraction, *, partition="policy_validation"):
    """At most floor(fraction*n) validation accounts; all boundary ties abstain.

    The cutoff is the first excluded order statistic. This can accept fewer than
    the requested fraction when scores tie, and later sample acceptance can differ.
    No ranking or percentile is recomputed when this frozen policy is applied.
    """
    _selection_partition(partition)
    p = _probabilities(probabilities)
    fraction = _finite_nonnegative(fraction, "fraction")
    if not 0 < fraction < 1:
        raise ValueError("fraction must be strictly within (0, 1)")
    boundary = int(math.floor(fraction * len(p)))
    cutoff = float(np.sort(p)[boundary])
    return FrozenPolicy(f"low_risk_fraction_{fraction:g}", cutoff=cutoff,
                        target_fraction=fraction)


def _benchmark_utility(accepted, y, scenario):
    # Count-based arithmetic keeps utility ties deterministic across row permutations.
    defaults = int(np.count_nonzero(accepted & (y == 1)))
    nondefaults = int(np.count_nonzero(accepted & (y == 0)))
    return nondefaults * scenario.gain - defaults * scenario.loss - int(accepted.sum()) * scenario.cost


def select_empirical_policy(probabilities, labels, scenario, *, partition="policy_validation"):
    """Fixed 201-point grid plus all/none; utility ties prefer fewer acceptances.

    At equal utility and count, the deterministic order is none, increasing grid
    cutoff, all. In particular zero-acceptance winners become explicit abstain-all.
    """
    _selection_partition(partition)
    p = _probabilities(probabilities)
    y = _labels(labels, p)
    candidates = [FrozenPolicy("empirical", kind="none")]
    candidates += [FrozenPolicy("empirical", cutoff=index / 200) for index in range(201)]
    candidates += [FrozenPolicy("empirical", kind="all")]
    best, best_key = None, None
    for candidate in candidates:
        accepted = candidate.accept(p)
        key = (_benchmark_utility(accepted, y, scenario), -int(accepted.sum()))
        if best_key is None or key > best_key:
            best, best_key = candidate, key
    return best


def freeze_policies(probabilities, labels, scenario, *, partition="policy_validation"):
    _selection_partition(partition)
    p = _probabilities(probabilities)
    y = _labels(labels, p)
    return [
        FrozenPolicy("accept_all", kind="all"),
        FrozenPolicy("abstain_all", kind="none"),
        *(fraction_policy(p, fraction, partition=partition) for fraction in (0.25, 0.5, 0.75)),
        FrozenPolicy("probability_0_5", cutoff=0.5),
        FrozenPolicy("analytic", cutoff=analytic_cutoff(scenario)),
        select_empirical_policy(p, y, scenario, partition=partition),
    ]


def _ratio(numerator, denominator):
    return float(numerator / denominator) if denominator else None


def evaluate_policy(probabilities, labels, policy, scenario):
    """Evaluate a frozen definition without deriving or adapting any threshold.

    Detection TP = abstained default; FP = abstained nondefault; FN = accepted
    default; TN = accepted nondefault. Undefined rates are None (display as N/A).
    Predicted expected utility includes zeros for every abstained customer.
    """
    p = _probabilities(probabilities)
    y = _labels(labels, p)
    accepted = policy.accept(p)
    count = int(accepted.sum())
    total = _benchmark_utility(accepted, y, scenario)
    predicted_total = float(expected_utility(p, scenario)[accepted].sum())
    tp = int(np.count_nonzero(~accepted & (y == 1)))
    fp = int(np.count_nonzero(~accepted & (y == 0)))
    fn = int(np.count_nonzero(accepted & (y == 1)))
    tn = int(np.count_nonzero(accepted & (y == 0)))
    return {
        "scenario_id": scenario.scenario_id,
        "policy_id": policy.policy_id,
        "policy_kind": policy.kind,
        "cutoff": policy.cutoff,
        "target_fraction": policy.target_fraction,
        "rows": len(p),
        "accepted_count": count,
        "abstained_count": len(p) - count,
        "accepted_nondefault_count": tn,
        "accepted_default_count": fn,
        "acceptance_rate": float(count / len(p)),
        "accepted_default_rate": _ratio(fn, count),
        "benchmark_utility_total": float(total),
        "benchmark_utility_per_customer": float(total / len(p)),
        "predicted_expected_utility_total": predicted_total,
        "predicted_expected_utility_per_customer": float(predicted_total / len(p)),
        "predicted_expected_utility_per_accepted": _ratio(predicted_total, count),
        "detection_true_positive": tp,
        "detection_false_positive": fp,
        "detection_false_negative": fn,
        "detection_true_negative": tn,
        "detection_precision": _ratio(tp, tp + fp),
        "detection_recall": _ratio(tp, tp + fn),
        "detection_f1": _ratio(2 * tp, 2 * tp + fp + fn),
        "detection_false_positive_rate": _ratio(fp, fp + tn),
    }


def sensitivity_scenarios():
    """All nine predefined G/L cells and the base G/L with secondary C=5."""
    scenarios = [Scenario(f"g{gain}_l{loss}_c0", gain, loss, 0)
                 for gain in (25, 50, 100) for loss in (250, 500, 750)]
    scenarios.append(Scenario("g50_l500_c5", 50, 500, 5))
    return scenarios


def sensitivity_analysis(probabilities, labels, *, partition="policy_validation"):
    """Serializable complete sensitivity evidence; never filters unfavorable scenarios."""
    _selection_partition(partition)
    p = _probabilities(probabilities)
    y = _labels(labels, p)
    scenario_results = []
    for scenario in sensitivity_scenarios():
        policies = freeze_policies(p, y, scenario, partition=partition)
        scenario_results.append({
            "scenario": scenario.to_dict(),
            "analytic_cutoff": analytic_cutoff(scenario),
            "policies": [policy.to_dict() for policy in policies],
            "results": [evaluate_policy(p, y, policy, scenario) for policy in policies],
        })
    return {
        "selection_partition": partition,
        "utility_units": "dimensionless synthetic benchmark units",
        "boundary_ties": "abstain",
        "fraction_rule": "first excluded order statistic; all boundary ties abstain",
        "empirical_grid": {"start": 0.0, "stop": 1.0, "step": 0.005,
                           "explicit_all_none": True, "ties": "lower acceptance"},
        "detection_positive_action": "abstain_simulated",
        "scenarios": scenario_results,
    }
