"""Monitoring replay must preserve previous report and customer receipt evidence."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from credit_risk.features import feature_contract
from credit_risk.monitoring import monitoring_report
from fixtures.records import make_records


@pytest.fixture
def monitoring_inputs():
    records = make_records(20)
    development = pd.DataFrame(records[:10])
    validation = pd.DataFrame(records[10:])
    encoder = SimpleNamespace(categories_=[np.array([-2, -1, 0, 1, 2])] * 6)
    categorical = SimpleNamespace(named_steps={'encoder': encoder})
    preprocessor = SimpleNamespace(named_transformers_={'categorical': categorical})
    bundle = SimpleNamespace(
        feature_schema=feature_contract(),
        base=SimpleNamespace(named_steps={'preprocessor': preprocessor}),
        predict_probability=lambda frame: np.full(len(frame), 0.2),
    )
    return bundle, development, validation


def _bytes(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


def _forbid_prediction(*args):
    raise AssertionError('Existing evidence must be rejected before scoring')


def test_nonempty_monitoring_output_is_rejected_before_scoring(monitoring_inputs, tmp_path):
    bundle, development, validation = monitoring_inputs
    sentinel = tmp_path / 'existing.txt'
    sentinel.write_bytes(b'previous evidence')
    before = _bytes(tmp_path)
    bundle.predict_probability = _forbid_prediction
    with pytest.raises(ValueError, match='new or an empty directory'):
        monitoring_report(bundle, development, validation, tmp_path)
    assert _bytes(tmp_path) == before


def test_repeat_monitoring_preserves_aggregate_and_customer_receipts(monitoring_inputs, tmp_path):
    bundle, development, validation = monitoring_inputs
    output = tmp_path / 'report'
    output.mkdir()  # An existing empty destination remains supported.
    report = monitoring_report(bundle, development, validation, output)
    runtime = Path(report['customer_receipts'])
    aggregates, receipts = _bytes(output), _bytes(runtime)
    bundle.predict_probability = _forbid_prediction
    with pytest.raises(ValueError, match='new or an empty directory'):
        monitoring_report(bundle, development, validation, output)
    assert _bytes(output) == aggregates
    assert _bytes(runtime) == receipts


def test_stale_runtime_receipts_prevent_replay_into_empty_output(monitoring_inputs, tmp_path):
    bundle, development, validation = monitoring_inputs
    output = tmp_path / 'report'
    report = monitoring_report(bundle, development, validation, output)
    runtime = Path(report['customer_receipts'])
    receipts = _bytes(runtime)
    output.rename(tmp_path / 'preserved_report')
    output.mkdir()
    bundle.predict_probability = _forbid_prediction
    with pytest.raises(ValueError, match='customer receipts already exist'):
        monitoring_report(bundle, development, validation, output)
    assert not list(output.iterdir())
    assert _bytes(runtime) == receipts
