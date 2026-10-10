"""Synthetic examples protect payoff, held-out selection, and frozen-policy semantics."""

import json

import numpy as np
import pytest

from credit_risk.decisioning.policy import (
    FrozenPolicy, Scenario, analytic_cutoff, evaluate_policy, expected_utility,
    fraction_policy, freeze_policies, select_empirical_policy, sensitivity_analysis,
    sensitivity_scenarios,
)


def test_analytic_cutoff_agrees_with_positive_utility_and_abstains_at_boundary():
    scenario = Scenario()
    threshold = analytic_cutoff(scenario)
    assert threshold == pytest.approx(50 / 550)
    p = np.array([0, threshold - 1e-8, threshold, threshold + 1e-8, 1])
    policy = FrozenPolicy("analytic", cutoff=threshold)
    np.testing.assert_array_equal(policy.accept(p), [True, True, False, False, False])
    np.testing.assert_array_equal(expected_utility(p, scenario) > 1e-10, policy.accept(p))
    assert expected_utility([0, 1], scenario).tolist() == [50, -500]


@pytest.mark.parametrize("gain,cost", [(0, 0), (5, 5), (5, 6)])
def test_gain_at_or_below_processing_cost_means_abstain_all(gain, cost):
    scenario = Scenario("unfavorable", gain, 500, cost)
    assert analytic_cutoff(scenario) == 0
    policy = FrozenPolicy("analytic", cutoff=analytic_cutoff(scenario))
    assert not policy.accept([0, 0.01, 0.5, 1]).any()


@pytest.mark.parametrize("updates", [
    {"gain": -1}, {"loss": -1}, {"cost": -1}, {"gain": float("nan")},
    {"loss": float("inf")}, {"gain": 0, "loss": 0}, {"cost": "5"},
    {"gain": True}, {"scenario_id": ""}, {"gain": 1e308, "loss": 1e308},
])
def test_invalid_payoffs_fail(updates):
    with pytest.raises(ValueError):
        Scenario(**updates)


@pytest.mark.parametrize("p", [[], [[0.5]], [-0.01], [1.01], [np.nan], [np.inf], ["risk"]])
def test_invalid_probabilities_fail(p):
    with pytest.raises(ValueError):
        expected_utility(p, Scenario())
    with pytest.raises(ValueError):
        FrozenPolicy("all", kind="all").accept(p)


@pytest.mark.parametrize("y", [[0], [0, 2], [0, np.nan], [[0, 1]], ["0", "1"]])
def test_invalid_outcomes_or_lengths_fail(y):
    with pytest.raises(ValueError):
        evaluate_policy([0.1, 0.2], y, FrozenPolicy("none", kind="none"), Scenario())


@pytest.mark.parametrize("updates", [
    {"kind": "rank"}, {"cutoff": -0.1}, {"cutoff": 1.1}, {"cutoff": float("nan")},
    {"kind": "all", "cutoff": 0.5}, {"target_fraction": 0}, {"target_fraction": 1},
    {"selected_on": "final_test"}, {"policy_id": ""},
])
def test_invalid_frozen_policy_definitions_fail(updates):
    definition = {"policy_id": "example", "cutoff": 0.5} | updates
    with pytest.raises(ValueError):
        FrozenPolicy(**definition)


def test_payoff_processing_cost_is_charged_once_per_accepted_account():
    scenario = Scenario("with_cost", 50, 500, 5)
    result = evaluate_policy([0.05, 0.1, 0.8], [0, 1, 1],
                             FrozenPolicy("example", cutoff=0.5), scenario)
    assert analytic_cutoff(scenario) == pytest.approx(45 / 550)
    assert result["benchmark_utility_total"] == 50 - 500 - 2 * 5
    assert result["benchmark_utility_per_customer"] == pytest.approx(-460 / 3)
    assert result["predicted_expected_utility_total"] == pytest.approx(17.5 - 10)
    assert result["predicted_expected_utility_per_customer"] == pytest.approx(7.5 / 3)
    assert result["predicted_expected_utility_per_accepted"] == pytest.approx(7.5 / 2)


def test_detection_metrics_have_abstention_as_positive_action():
    result = evaluate_policy([0.1, 0.2, 0.3, 0.4, 0.5], [0, 1, 0, 1, 1],
                             FrozenPolicy("example", cutoff=0.3), Scenario())
    assert result["accepted_count"] == 2
    assert result["accepted_default_rate"] == 0.5
    assert result["detection_true_positive"] == 2
    assert result["detection_false_positive"] == 1
    assert result["detection_false_negative"] == 1
    assert result["detection_true_negative"] == 1
    assert result["detection_precision"] == pytest.approx(2 / 3)
    assert result["detection_recall"] == pytest.approx(2 / 3)
    assert result["detection_f1"] == pytest.approx(2 / 3)
    assert result["detection_false_positive_rate"] == 0.5


def test_accept_none_and_accept_all_metrics_preserve_undefined_values():
    p, y = [0, 0.2, 1], [0, 0, 1]
    none = evaluate_policy(p, y, FrozenPolicy("none", kind="none"), Scenario())
    all_result = evaluate_policy(p, y, FrozenPolicy("all", kind="all"), Scenario())
    assert none["accepted_count"] == 0
    assert none["accepted_default_rate"] is None
    assert none["predicted_expected_utility_per_accepted"] is None
    assert none["benchmark_utility_total"] == none["predicted_expected_utility_total"] == 0
    assert none["detection_recall"] == none["detection_false_positive_rate"] == 1
    assert all_result["accepted_count"] == 3
    assert all_result["detection_precision"] is None
    assert all_result["detection_recall"] == all_result["detection_false_positive_rate"] == 0
    assert all_result["benchmark_utility_total"] == -400


def test_single_class_detection_denominators_are_explicitly_undefined():
    none = FrozenPolicy("none", kind="none")
    result = evaluate_policy([0.1, 0.2], [0, 0], none, Scenario())
    assert result["detection_recall"] is None
    result = evaluate_policy([0.1, 0.2], [1, 1], none, Scenario())
    assert result["detection_false_positive_rate"] is None


def test_fraction_boundary_ties_abstain_and_cutoff_is_reused_on_future_samples():
    policy = fraction_policy([0.1, 0.2, 0.2, 0.7], 0.5)
    assert policy.cutoff == 0.2
    np.testing.assert_array_equal(policy.accept([0.1, 0.2, 0.2, 0.7]),
                                  [True, False, False, False])
    # A new sample has 75% accepted: the original numerical cutoff stays fixed.
    assert policy.accept([0.01, 0.02, 0.03, 0.8]).mean() == 0.75
    assert fraction_policy([0.2] * 4, 0.75).accept([0.2] * 4).sum() == 0
    assert fraction_policy([0.2], 0.25).accept([0.2]).sum() == 0


def test_fraction_policy_uses_first_excluded_order_statistic():
    p = np.linspace(0, 1, 20)
    for fraction in (0.25, 0.5, 0.75):
        policy = fraction_policy(p, fraction)
        assert policy.accept(p).sum() == int(fraction * len(p))
        assert policy.cutoff == p[int(fraction * len(p))]
        assert fraction_policy(p[::-1], fraction) == policy


@pytest.mark.parametrize("partition", ["development", "calibration", "final_test", "test"])
def test_selection_functions_reject_other_partitions(partition):
    with pytest.raises(ValueError, match="only on policy_validation"):
        fraction_policy([0.1, 0.2], 0.5, partition=partition)
    with pytest.raises(ValueError, match="only on policy_validation"):
        select_empirical_policy([0.1, 0.2], [0, 1], Scenario(), partition=partition)
    with pytest.raises(ValueError, match="only on policy_validation"):
        freeze_policies([0.1, 0.2], [0, 1], Scenario(), partition=partition)
    with pytest.raises(ValueError, match="only on policy_validation"):
        sensitivity_analysis([0.1, 0.2], [0, 1], partition=partition)


def test_empirical_grid_strict_boundary_and_lower_acceptance_utility_tie():
    # One accepted nondefault yields utility 50. Accepting the next 11 adds
    # ten nondefaults and one default: exactly zero incremental utility.
    p = [0.001] + [0.2] * 11
    y = [0] + [0] * 10 + [1]
    scenario = Scenario()
    policy = select_empirical_policy(p, y, scenario)
    assert policy.kind == "cutoff"
    assert policy.cutoff == 0.005
    assert policy.accept(p).sum() == 1
    assert evaluate_policy(p, y, policy, scenario)["benchmark_utility_total"] == 50
    assert select_empirical_policy(p[::-1], y[::-1], scenario) == policy


def test_empirical_grid_includes_explicit_all_and_none_and_abstain_all_winner():
    profitable = select_empirical_policy([0.1, 1], [0, 0], Scenario())
    assert profitable.kind == "all"  # The grid cutoff 1 cannot accept p=1.
    unfavorable = select_empirical_policy([0, 0.1, 0.2], [1, 1, 1], Scenario())
    assert unfavorable.kind == "none"
    assert unfavorable.cutoff is None


def test_policy_and_scenario_roundtrip_is_strict_json_and_preserves_predictions():
    p, y, scenario = [0.05, 0.2, 0.4, 0.8], [0, 0, 1, 1], Scenario()
    definition = {"scenario": scenario.to_dict(),
                  "policies": [policy.to_dict() for policy in freeze_policies(p, y, scenario)]}
    loaded = json.loads(json.dumps(definition, allow_nan=False))
    restored_scenario = Scenario.from_dict(loaded["scenario"])
    assert restored_scenario == scenario
    restored = [FrozenPolicy.from_dict(row) for row in loaded["policies"]]
    for old, new in zip(freeze_policies(p, y, scenario), restored, strict=True):
        assert old == new
        np.testing.assert_array_equal(old.accept(p), new.accept(p))
        assert evaluate_policy(p, y, old, scenario) == evaluate_policy(p, y, new, restored_scenario)


def test_complete_sensitivity_grid_has_all_policies_and_unfavorable_results():
    scenarios = sensitivity_scenarios()
    assert len(scenarios) == 10
    assert {(row.gain, row.loss) for row in scenarios if row.cost == 0} == {
        (gain, loss) for gain in (25, 50, 100) for loss in (250, 500, 750)}
    assert [(row.gain, row.loss, row.cost) for row in scenarios if row.cost] == [(50, 500, 5)]
    result = sensitivity_analysis([0.1, 0.3], [1, 1])
    assert len(result["scenarios"]) == 10
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    for evidence in result["scenarios"]:
        assert len(evidence["policies"]) == len(evidence["results"]) == 8
        empirical = next(row for row in evidence["policies"] if row["policy_id"] == "empirical")
        assert empirical["kind"] == "none"
        accept_all = next(row for row in evidence["results"] if row["policy_id"] == "accept_all")
        assert accept_all["benchmark_utility_total"] < 0
        scenario = Scenario.from_dict(evidence["scenario"])
        assert evidence["analytic_cutoff"] == analytic_cutoff(scenario)
