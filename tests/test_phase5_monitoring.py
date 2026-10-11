"""Monitoring fixtures contain no real-data or final-test outcomes."""
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from credit_risk.data.schema import BILL_COLUMNS, STATUS_COLUMNS
from credit_risk.features import PREDICTORS, build_features, feature_contract
from credit_risk.models.pipelines import build_pipeline, positive_probability
from credit_risk.monitoring import (
    distribution_bins, distribution_counts, monitoring_report, population_stability_index,
)
from fixtures.records import make_record


@pytest.fixture
def inputs():
    def frame(start):
        records = []
        for i in range(40):
            row = make_record(start + i, i % 2)
            row.update(dict.fromkeys(STATUS_COLUMNS, int(i % 4 == 0)))
            row[BILL_COLUMNS[-1]] = i * 50
            records.append(row)
        return pd.DataFrame(records)
    development, pv = frame(1), frame(101)
    x = pd.DataFrame([build_features(row) for row in development.to_dict('records')])
    pipeline = build_pipeline('logistic', 'engineered', 'none')
    pipeline.fit(x, development.default_next_month)
    calls = []

    def predict(features):
        assert list(features.columns) == list(PREDICTORS)
        calls.append(features.copy())
        return positive_probability(pipeline, features)

    bundle = SimpleNamespace(base=pipeline, feature_schema=feature_contract(),
                             predict_probability=predict)
    return bundle, development, pv, calls


def test_explicit_tails_missing_and_constant_bins():
    edges = distribution_bins([1, 1, 1])
    assert distribution_counts([0, 1, 2, np.nan], edges).tolist() == [1, 1, 1, 1]
    assert distribution_counts([2, np.nan], distribution_bins([np.nan])).tolist() == [0, 1, 1]
    edges = distribution_bins(np.arange(11))
    counts = distribution_counts([-1, 0, 10, 11, np.nan], edges)
    assert counts[0] == counts[-2] == counts[-1] == 1
    assert counts.sum() == 5
    assert population_stability_index(counts, counts) == 0
    assert np.isfinite(population_stability_index([0, 10], [10, 0]))
    assert population_stability_index([0, 0], [1, 0]) is None
    with pytest.raises(ValueError):
        population_stability_index([1, -1], [1, 2])


def test_sampling_corruption_receipts_and_no_fit(inputs, tmp_path, monkeypatch):
    bundle, development, pv, calls = inputs
    original_dev, original_pv = development.copy(deep=True), pv.copy(deep=True)
    median = bundle.base.named_steps['preprocessor'].named_transformers_['numeric'].named_steps[
        'imputer'].statistics_.copy()

    def forbidden(*args, **kwargs):
        raise AssertionError('monitoring must never fit')

    monkeypatch.setattr(bundle.base, 'fit', forbidden)
    report = monitoring_report(bundle, development, pv, tmp_path)
    assert json.loads((tmp_path / 'monitoring.json').read_text()) == report
    assert (tmp_path / 'monitoring.csv').exists()
    assert (tmp_path / 'risk_distribution.svg').exists()
    pd.testing.assert_frame_equal(development, original_dev)
    pd.testing.assert_frame_equal(pv, original_pv)
    np.testing.assert_array_equal(median, bundle.base.named_steps['preprocessor'].
                                  named_transformers_['numeric'].named_steps['imputer'].statistics_)
    assert len(calls) == 7
    from pathlib import Path
    runtime = Path(report['customer_receipts'])
    assert 'artifacts/runtime/monitoring' in str(runtime)
    weights = pd.read_csv(runtime / 'sampling_weights_counts.csv')
    for scenario in ['financial_mix_shift', 'delinquency_mix_shift']:
        receipt = weights[weights.scenario == scenario]
        assert receipt.sampled_count.sum() == 3000
        assert set(receipt.weight) == {1, 3}
        assert receipt.probability.sum() == pytest.approx(1)
        draws = pd.read_csv(runtime / f'{scenario}_draws.csv')
        expected = np.random.default_rng(42).choice(40, 3000, replace=True,
                                                   p=receipt.probability.to_numpy())
        np.testing.assert_array_equal(draws.source_position, expected)
        assert report['scenarios'][scenario]['labeled_metrics']['rows'] == 3000
    scenarios = report['scenarios']
    assert scenarios['corruption_nonnumeric']['quality']['quarantined_rows'] == 4
    assert scenarios['corruption_nonnumeric']['scored_rows'] == 36
    assert scenarios['corruption_missing']['scored_rows'] == 40
    assert scenarios['corruption_unseen_status']['quality']['unknown_category_counts'][
        STATUS_COLUMNS[-1]] == 4
    for name in report['corruption']:
        assert scenarios[name]['labeled_metrics'] is None
        assert scenarios[name]['warnings']
    for scenario in scenarios.values():
        for distribution in scenario['distributions'].values():
            assert sum(distribution['counts']) == scenario['quality']['rows']
            assert sum(distribution['development_counts']) == 40


def test_development_bins_do_not_use_policy_values_or_labels(inputs, tmp_path):
    bundle, dev, pv, _ = inputs
    first = monitoring_report(bundle, dev, pv, tmp_path / 'first')
    changed = pv.copy()
    changed[BILL_COLUMNS[-1]] = 999999
    dev['default_next_month'] = 'never interpret development outcomes'
    second = monitoring_report(bundle, dev, changed, tmp_path / 'second')
    a = first['scenarios']['reference']['distributions']
    b = second['scenarios']['reference']['distributions']
    for column in a:
        assert a[column]['edges'] == b[column]['edges']
    assert b[BILL_COLUMNS[-1]]['counts'][-2] == 40
    assert first['development_utilization_q75'] == second['development_utilization_q75']


def test_input_rejection_and_unlabeled_reference(inputs, tmp_path):
    bundle, dev, pv, _ = inputs
    with pytest.raises(ValueError, match='overlap'):
        monitoring_report(bundle, dev, dev, tmp_path)
    with pytest.raises(ValueError, match='Schema must contain'):
        monitoring_report(bundle, dev, pv.drop(columns=BILL_COLUMNS[-1]), tmp_path)
    with pytest.raises(ValueError, match='binary'):
        monitoring_report(bundle, dev, pv.assign(default_next_month=9), tmp_path)
    report = monitoring_report(bundle, dev, pv.drop(columns='default_next_month'), tmp_path)
    assert all(s['labeled_metrics'] is None for s in report['scenarios'].values())


def test_protected_artifacts_and_invalid_labels_write_nothing(inputs, tmp_path):
    from pathlib import Path
    import credit_risk.monitoring as monitoring

    bundle, dev, pv, _ = inputs
    protected = Path(monitoring.__file__).resolve().parents[2] / 'artifacts/models/forbidden'
    with pytest.raises(ValueError, match='accepted model'):
        monitoring_report(bundle, dev, pv, protected)
    destination = tmp_path / 'bad_labels'
    with pytest.raises(ValueError, match='binary'):
        monitoring_report(bundle, dev, pv.assign(default_next_month=2), destination)
    assert not destination.exists()


def test_psi_epsilon_is_renormalized():
    p = np.array([1.0, 0.0, 0.0]) + 1e-6
    q = np.array([0.0, 0.5, 0.5]) + 1e-6
    p /= p.sum()
    q /= q.sum()
    expected = np.sum((q - p) * np.log(q / p))
    assert population_stability_index([10, 0, 0], [0, 5, 5]) == pytest.approx(expected)


def test_single_class_and_missing_probability_metrics():
    from credit_risk.monitoring import _metrics

    metrics = _metrics(pd.DataFrame({'default_next_month': [0, 0]}), np.array([0.2, np.nan]))
    assert metrics['rows'] == 1
    assert metrics['AP'] is None and metrics['ROC_AUC'] is None
    assert metrics['Brier'] == pytest.approx(0.04)
    metrics = _metrics(pd.DataFrame({'default_next_month': [0]}), np.array([np.nan]))
    assert metrics['rows'] == 0
    assert metrics['log_loss'] is None


def test_row_validation_matches_scorer_with_repeated_sources(inputs, monkeypatch):
    import credit_risk.monitoring as monitoring
    from credit_risk.data.schema import PAYMENT_COLUMNS, RAW_PREDICTORS
    from credit_risk.inference import validate_batch

    bundle, _, pv, _ = inputs
    frame = pd.concat([pv.iloc[:8], pv.iloc[:1]])  # repeated IDs and dataframe indexes
    frame = frame.copy(deep=True)
    frame['limit_bal'] = frame.limit_bal.astype(object)
    frame.iloc[0, frame.columns.get_loc('limit_bal')] = np.nan
    frame.iloc[1, frame.columns.get_loc('limit_bal')] = ''
    frame.iloc[2, frame.columns.get_loc(PAYMENT_COLUMNS[-1])] = -1
    frame[STATUS_COLUMNS[-1]] = frame[STATUS_COLUMNS[-1]].astype(float)
    frame.iloc[3, frame.columns.get_loc(STATUS_COLUMNS[-1])] = 0.5
    frame.iloc[4, frame.columns.get_loc(STATUS_COLUMNS[-1])] = 99
    frame.iloc[5, frame.columns.get_loc('limit_bal')] = True
    frame[BILL_COLUMNS[-1]] = frame[BILL_COLUMNS[-1]].astype(float)
    frame.iloc[6, frame.columns.get_loc(BILL_COLUMNS[-1])] = np.inf
    frame.iloc[7, frame.columns.get_loc(BILL_COLUMNS[-1])] = -200
    encoder = bundle.base.named_steps['preprocessor'].named_transformers_[
        'categorical'].named_steps['encoder']
    vocab = dict(zip(STATUS_COLUMNS, encoder.categories_, strict=True))
    scorer_frame = frame.loc[:, list(RAW_PREDICTORS)].reset_index(drop=True)
    scorer_frame.insert(0, 'record_id', [str(i) for i in range(len(frame))])
    expected, positions, rejected = validate_batch(scorer_frame)
    seen = []
    original = frame.copy(deep=True)

    def checked_batch(batch):
        assert set(batch.columns) == {'record_id', *RAW_PREDICTORS}
        assert batch.record_id.is_unique
        seen.append(len(batch))
        return validate_batch(batch)

    monkeypatch.setattr(monitoring, 'validate_batch', checked_batch)
    features, valid, quality = monitoring._features(frame, vocab)
    assert seen == [9]
    assert np.flatnonzero(valid).tolist() == positions == [0, 1, 4, 7, 8]
    pd.testing.assert_frame_equal(features.loc[valid].reset_index(drop=True), expected)
    assert quality['quarantined_rows'] == len(rejected) == 4
    assert quality['counts_reconcile']
    assert quality['missing_counts']['limit_bal'] == 2
    assert quality['unknown_category_counts'][STATUS_COLUMNS[-1]] == 1
    assert quality['quarantine_reason_counts'] == {
        row['reason']: 1 for row in rejected}
    risk = monitoring._probabilities(bundle, features, valid)
    np.testing.assert_allclose(risk[valid], bundle.predict_probability(expected))
    assert np.isnan(risk[~valid]).all()
    assert np.isnan(features.loc[valid].iloc[0].latest_utilization_proxy)
    pd.testing.assert_frame_equal(frame, original)


def test_missing_limits_and_unknown_statuses_still_score_in_report(inputs, tmp_path):
    bundle, dev, pv, _ = inputs
    pv.loc[0, 'limit_bal'] = np.nan
    pv.loc[1, STATUS_COLUMNS[-1]] = 99
    original = pv.copy(deep=True)
    report = monitoring_report(bundle, dev, pv, tmp_path)
    pd.testing.assert_frame_equal(pv, original)
    reference = report['scenarios']['reference']
    assert reference['quality']['quarantined_rows'] == 0
    assert reference['scored_rows'] == 40
    assert reference['quality']['missing_counts']['limit_bal'] == 1
    assert reference['quality']['unknown_category_counts'][STATUS_COLUMNS[-1]] == 1
    assert reference['labeled_metrics']['rows'] == 40
    assert report['scenarios']['financial_mix_shift']['scored_rows'] == 3000


def test_plot_encodes_actual_shared_bin_distributions(inputs, tmp_path):
    from xml.etree import ElementTree

    bundle, dev, pv, _ = inputs
    report = monitoring_report(bundle, dev, pv, tmp_path)
    svg = ElementTree.parse(tmp_path / 'risk_distribution.svg')
    rectangles = [element for element in svg.getroot().iter()
                  if element.tag.endswith('rect') and 'data-series' in element.attrib]
    reference = report['scenarios']['reference']['distributions']['p_default']
    expected_series = {'development': reference['development_counts']}
    for name in ('reference', 'financial_mix_shift', 'delinquency_mix_shift'):
        expected_series[name] = report['scenarios'][name]['distributions']['p_default']['counts']
    assert len(rectangles) == sum(map(len, expected_series.values()))
    for name, counts in expected_series.items():
        bars = [element for element in rectangles if element.attrib['data-series'] == name]
        assert [int(element.attrib['data-bin']) for element in bars] == list(range(len(counts)))
        assert [int(element.attrib['data-count']) for element in bars] == counts
        fractions = [float(element.attrib['data-fraction']) for element in bars]
        np.testing.assert_allclose(fractions, np.array(counts) / sum(counts))
        assert sum(fractions) == pytest.approx(1)
        np.testing.assert_allclose([float(e.attrib['height']) for e in bars],
                                   np.array(fractions) * 260, atol=0.00051)
    assert 'underflow' in ''.join(svg.getroot().itertext())
    assert 'missing' in ''.join(svg.getroot().itertext())
