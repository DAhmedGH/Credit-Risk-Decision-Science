"""Synthetic evaluation and scoring integrity; never loads real final-test outcomes."""

import json
import socket
from types import SimpleNamespace
import joblib
import numpy as np
import pandas as pd
import pytest
from credit_risk.data.schema import RAW_PREDICTORS, STATUS_COLUMNS
from credit_risk.features import build_features
from credit_risk.models.pipelines import build_pipeline
from credit_risk.decisioning.policy import Scenario, freeze_policies, sensitivity_analysis
from credit_risk.inference import validate_batch, score_frame, read_batch
from credit_risk.phase5 import metrics, group_resamples, summarize, evaluate, interval
from fixtures.records import make_records


@pytest.fixture
def fixture_bundle():
    records = make_records(40)
    X = pd.DataFrame([build_features(r) for r in records])
    y = np.array([r["default_next_month"] for r in records])
    model = build_pipeline("logistic", "engineered", "none").fit(X, y)
    p = model.predict_proba(X)[:, 1]
    policy = {
        "base_policies": [x.to_dict() for x in freeze_policies(p, y, Scenario())],
        "sensitivity": sensitivity_analysis(p, y),
    }
    bundle = SimpleNamespace(
        policy=policy, predict_probability=lambda frame: model.predict_proba(frame)[:, 1]
    )
    batch = pd.DataFrame(
        [
            {"record_id": f"000-{i}", **{k: r[k] for k in RAW_PREDICTORS}}
            for i, r in enumerate(records)
        ]
    )
    return bundle, batch, model


def test_group_clusters_and_paired_identity():
    groups = ["a", "a", "b", "c", "c", "c"]
    first = list(group_resamples(groups, 20, 42))
    second = list(group_resamples(groups, 20, 42))
    assert all(np.array_equal(a, b) for a, b in zip(first, second))
    for indices in first:
        counts = np.bincount(indices, minlength=6)
        assert counts[0] == counts[1]
        assert counts[3] == counts[4] == counts[5]
    assert any(len(i) != 6 for i in first)


def test_probability_metrics_and_undefined():
    result = metrics([0, 1], [0.1, 0.8])
    assert result["average_precision"] == 1
    assert result["roc_auc"] == 1
    assert result["brier_score"] == pytest.approx(0.025)
    assert metrics([0, 0], [0.1, 0.2])["average_precision"] is None
    assert metrics([1, 1], [0.1, 0.2])["roc_auc"] is None
    assert interval([None, None], None)["undefined_repetitions"] == 2
    with pytest.raises(ValueError):
        metrics([0, 1], [0.1, np.inf])


def test_evidence_metrics_policy_reconciliation(fixture_bundle):
    bundle, batch, _ = fixture_bundle
    scored, _, _ = score_frame(bundle, batch)
    y = np.array([r["default_next_month"] for r in make_records(40)])
    frame = pd.DataFrame(
        {
            "client_id": range(40),
            "fingerprint": np.repeat(np.arange(20), 2),
            "default_next_month": y,
            "selected_bundle": scored.p_default,
            "same_reference": scored.p_default,
        }
    )
    result = summarize(frame, bundle.policy, repetitions=10)
    assert len(result["policy_metrics"]) == 88
    for row in result["policy_metrics"]:
        assert row["detection_true_positive"] + row["detection_false_negative"] == y.sum()
        assert row["accepted_count"] + row["abstained_count"] == 40
        if row["policy_id"] == "abstain_all":
            assert row["accepted_default_rate"] is None
            assert row["benchmark_utility_total"] == 0
    delta = result["intervals"][
        "model_difference/selected_bundle-minus-same_reference/average_precision"
    ]
    assert delta["estimate"] == delta["lower"] == delta["upper"] == 0


def test_database_unavailable_no_fit_and_save_load(fixture_bundle, tmp_path, monkeypatch):
    bundle, batch, model = fixture_bundle

    def forbidden(*args, **kwargs):
        raise AssertionError("Scoring attempted network/fit")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(type(model), "fit", forbidden)
    scored, rejected, receipt = score_frame(bundle, batch)
    assert receipt["counts_reconcile"] and not len(rejected)
    path = tmp_path / "pipeline.joblib"
    joblib.dump(model, path)
    restored = joblib.load(path)
    X, _, _ = validate_batch(batch)
    assert np.array_equal(scored.p_default, restored.predict_proba(X)[:, 1])
    for index in (0, 5):
        one, _, _ = score_frame(bundle, batch.iloc[[index]])
        assert one.p_default.iloc[0] == pytest.approx(scored.p_default.iloc[index], abs=1e-12)
    assert scored.record_id.iloc[0] == "000-0"


@pytest.mark.parametrize("field", ["default_next_month", "target", "client_id", "sex", "p_default"])
def test_schema_leakage_rejection(fixture_bundle, field):
    _, batch, _ = fixture_bundle
    batch[field] = 1
    with pytest.raises(ValueError, match="Schema"):
        validate_batch(batch)


def test_quarantine_signed_unknown_missing(fixture_bundle):
    bundle, batch, _ = fixture_bundle
    batch = batch.astype(object)
    batch.loc[0, "limit_bal"] = 0
    batch.loc[1, "bill_amt_2005_09"] = "broken"
    batch.loc[2, "pay_amt_2005_09"] = -1
    batch.loc[3, STATUS_COLUMNS[0]] = 999
    batch.loc[4, "bill_amt_2005_09"] = -999
    batch.loc[5, "bill_amt_2005_09"] = pd.NA
    scored, rejected, receipt = score_frame(bundle, batch)
    assert len(rejected) == 3
    assert receipt["input_count"] == receipt["scored_count"] + receipt["quarantined_count"]
    assert set(rejected.record_id) == {"000-0", "000-1", "000-2"}
    assert {"000-3", "000-4", "000-5"} <= set(scored.record_id)


def test_fatal_missing_duplicate_ids_and_headers(fixture_bundle, tmp_path):
    _, batch, _ = fixture_bundle
    with pytest.raises(ValueError):
        validate_batch(batch.drop(columns=["limit_bal"]))
    batch.loc[1, "record_id"] = batch.loc[0, "record_id"]
    with pytest.raises(ValueError, match="unique"):
        validate_batch(batch)
    path = tmp_path / "duplicate.csv"
    path.write_text("record_id,record_id\n1,2\n")
    with pytest.raises(ValueError, match="Duplicate"):
        read_batch(path)


def test_stale_readiness_prevents_outcome_access(tmp_path, monkeypatch):
    import credit_risk.phase5 as module

    monkeypatch.setattr(
        module, "preflight", lambda root: (None, None, {"code_hashes": {"x": "new"}})
    )

    def forbidden(*args):
        raise AssertionError("Outcomes accessed before readiness")

    monkeypatch.setattr(module, "partition", forbidden)
    receipt = tmp_path / "readiness.json"
    receipt.write_text(json.dumps({"disposition": "PASS", "code_hashes": {"x": "old"}}))
    with pytest.raises(ValueError, match="stale"):
        evaluate(tmp_path, receipt)
    assert not (tmp_path / "artifacts/runtime").exists()


def test_parquet_round_trip(fixture_bundle, tmp_path):
    bundle, batch, _ = fixture_bundle
    path = tmp_path / "batch.parquet"
    batch.to_parquet(path, index=False)
    csv, _, _ = score_frame(bundle, batch)
    parquet, _, _ = score_frame(bundle, read_batch(path))
    pd.testing.assert_frame_equal(csv, parquet)


def test_saved_evidence_rejects_stale_ids_fingerprints_decisions():
    from credit_risk.phase5 import validate_saved, scenarios
    from credit_risk.decisioning.policy import FrozenPolicy

    y = np.array([0, 1, 0, 1])
    p = np.array([0.01, 0.8, 0.03, 0.7])
    policy = {
        "base_policies": [x.to_dict() for x in freeze_policies(p, y, Scenario())],
        "sensitivity": sensitivity_analysis(p, y),
    }
    frame = pd.DataFrame(
        {"client_id": [1, 2, 3, 4], "fingerprint": ["a", "b", "c", "d"], "default_next_month": y}
    )
    for name in [
        "dummy_prior",
        "logistic_00_engineered_none",
        "random_forest_02_engineered_none",
        "xgboost_04_engineered_none",
        "xgboost_05_engineered_none",
        "selected_bundle",
    ]:
        frame[name] = p
    assignments = [
        {"partition": "final_test", "client_id": str(i + 1), "fingerprint": f}
        for i, f in enumerate("abcd")
    ]
    rows = []
    for cell in scenarios(policy):
        for definition in cell["policies"]:
            accepted = FrozenPolicy.from_dict(definition).accept(p)
            rows.extend(
                {
                    "client_id": i + 1,
                    "scenario_id": cell["scenario"]["scenario_id"],
                    "policy_id": definition["policy_id"],
                    "accepted": bool(a),
                }
                for i, a in enumerate(accepted)
            )
    decisions = pd.DataFrame(rows)
    validate_saved(frame, decisions, assignments, policy)
    for mutation in ("id", "fingerprint", "model", "raw"):
        bad = frame.copy()
        if mutation == "id":
            bad.loc[0, "client_id"] = 99
        if mutation == "fingerprint":
            bad.loc[0, "fingerprint"] = "x"
        if mutation == "model":
            bad = bad.drop(columns=["dummy_prior"])
        if mutation == "raw":
            bad.loc[0, "selected_bundle"] = 0.11
        with pytest.raises(ValueError):
            validate_saved(bad, decisions, assignments, policy)
    for mutation in ("mask", "missing", "duplicate"):
        bad = decisions.copy()
        if mutation == "mask":
            bad.loc[0, "accepted"] = False
        if mutation == "missing":
            bad = bad.iloc[1:]
        if mutation == "duplicate":
            bad = pd.concat([bad, bad.iloc[[0]]])
        with pytest.raises(ValueError):
            validate_saved(frame, bad, assignments, policy)
