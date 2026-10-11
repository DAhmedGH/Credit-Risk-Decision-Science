"""Batch parser regressions for independently observed audit defects."""

import csv
from types import SimpleNamespace

import pandas as pd
import pytest

from credit_risk.data.schema import RAW_PREDICTORS
from credit_risk.decisioning.policy import FrozenPolicy
from credit_risk.inference import read_batch, read_batch_snapshot, score_frame, validate_batch


@pytest.mark.parametrize('extra_fields', [-1, 1])
def test_csv_rejects_short_or_wide_records_before_identity_shift(tmp_path, extra_fields):
    path = tmp_path / 'malformed.csv'
    header = ['record_id', *RAW_PREDICTORS]
    row = ['original-id', '1000', *['1'] * (len(RAW_PREDICTORS) - 1)]
    row = row[:-1] if extra_fields < 0 else [*row, '0']
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerow(row)
    with pytest.raises(ValueError, match='fields; expected'):
        read_batch(path)


@pytest.mark.parametrize('content', ['', '\n', 'record_id,limit_bal\n"unclosed,1000\n'])
def test_csv_rejects_empty_or_malformed_input(tmp_path, content):
    path = tmp_path / 'invalid.csv'
    path.write_text(content)
    with pytest.raises(ValueError, match='header|Malformed CSV'):
        read_batch(path)


def test_csv_preserves_quoted_multiline_identity_and_missing_cells(tmp_path):
    path = tmp_path / 'quoted.csv'
    identifier = '0001, account\nsecond line'
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['record_id', *RAW_PREDICTORS])
        writer.writerow([identifier, '1000', *['1'] * (len(RAW_PREDICTORS) - 2), ''])
    frame = read_batch(path)
    features, positions, rejected = validate_batch(frame)
    assert frame.record_id.tolist() == [identifier]
    assert positions == [0] and rejected == [] and len(features) == 1
    assert features[RAW_PREDICTORS[-1]].isna().all()


def test_csv_accepts_header_only_empty_batch(tmp_path):
    path = tmp_path / 'empty_batch.csv'
    path.write_text(','.join(['record_id', *RAW_PREDICTORS]) + '\n')
    frame = read_batch(path)
    features, positions, rejected = validate_batch(frame)
    assert frame.empty and features.empty and positions == [] and rejected == []


def test_csv_validation_and_parsing_use_one_snapshot(tmp_path, monkeypatch):
    import hashlib
    import credit_risk.inference as inference

    path = tmp_path / 'batch.csv'
    content = (','.join(['record_id', *RAW_PREDICTORS]) + '\n'
               + ','.join(['original-id', *['1'] * len(RAW_PREDICTORS)]) + '\n').encode()
    path.write_bytes(content)
    original_parse = inference._parse_batch

    def replace_then_parse(input_path, snapshot):
        input_path.write_bytes(b'replacement is not a valid batch')
        return original_parse(input_path, snapshot)

    monkeypatch.setattr(inference, '_parse_batch', replace_then_parse)
    frame, input_hash = read_batch_snapshot(path)
    assert frame.record_id.tolist() == ['original-id']
    assert input_hash == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize('field', ['record_id', 'limit_bal'])
def test_csv_rejects_nul_before_parser_truncates_identity_or_financial_value(tmp_path, field):
    path = tmp_path / 'nul.csv'
    row = {'record_id': 'original-id', **dict.fromkeys(RAW_PREDICTORS, '1')}
    row['limit_bal'] = '1000'
    row[field] += '\x00invalid-suffix'
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['record_id', *RAW_PREDICTORS])
        writer.writeheader()
        writer.writerow(row)
    with pytest.raises(ValueError, match='NUL byte'):
        read_batch(path)


@pytest.mark.parametrize('input_format', ['parquet', 'frame'])
def test_nul_record_identity_is_fatal_before_scoring_across_formats(tmp_path, input_format):
    frame = pd.DataFrame([{'record_id': 'original\x00suffix',
                           **dict.fromkeys(RAW_PREDICTORS, 1)}])
    frame['limit_bal'] = 1000
    if input_format == 'parquet':
        path = tmp_path / 'identity.parquet'
        frame.to_parquet(path, index=False)
        frame = read_batch(path)
    assert frame.record_id.tolist() == ['original\x00suffix']

    def forbidden(*args):
        raise AssertionError('Invalid identity must fail before prediction/output')

    bundle = SimpleNamespace(
        policy={'base_policies': [FrozenPolicy('empirical', cutoff=.5).to_dict()],
                'sensitivity': {'scenarios': []}},
        predict_probability=forbidden,
    )
    with pytest.raises(ValueError, match='Record IDs must not contain NUL'):
        score_frame(bundle, frame)
