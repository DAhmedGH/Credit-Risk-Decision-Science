"""Missing source values must retain their frozen profile and audit semantics."""

import numpy as np
import pandas as pd
import pytest

from credit_risk.artifacts import write_csv
from credit_risk.data.schema import BILL_COLUMNS, STATUS_COLUMNS, validate_records
from credit_risk.explanations import descriptive_slices
from credit_risk.features import PREDICTORS, build_features
from credit_risk.models.phase4_inputs import routed_partitions
from credit_risk.models.pipelines import FinancialPredictorSelector
from credit_risk.splits import allocate_records
from fixtures.records import make_records


def _exports(root, records):
    accepted = validate_records(records).accepted
    assert len(accepted) == len(records)
    assignments, _ = allocate_records(accepted, "a" * 64)
    output = root / "data/processed"
    output.mkdir(parents=True)
    write_csv(output / "financial_features_v1.csv", [
        {"client_id": row["client_id"], **build_features(row)} for row in accepted
    ], ("client_id", *PREDICTORS))
    columns = ("client_id", "default_next_month")
    write_csv(output / "labels.csv", [{key: row[key] for key in columns} for row in accepted],
              columns)
    columns = ("client_id", "sex", "age", "education", "marriage",
               "sex_group", "education_group", "marriage_group")
    audits = [{**row, "sex_group": "unknown", "education_group": "unknown",
               "marriage_group": "unknown"} for row in accepted]
    write_csv(output / "audit_attributes.csv", [{key: row[key] for key in columns}
                                               for row in audits], columns)
    return assignments


@pytest.mark.parametrize("column", [BILL_COLUMNS[0], STATUS_COLUMNS[-1]])
def test_missing_history_preserves_frozen_profile(tmp_path, column):
    records = make_records()
    for row in records:
        row[column] = None
    assignments = _exports(tmp_path, records)
    parts = routed_partitions(tmp_path, assignments)
    for frame in parts.values():
        converted = FinancialPredictorSelector(tuple(PREDICTORS)).fit_transform(frame)
        assert converted[column].isna().all()
    expected = {row["client_id"]: row for row in assignments if row["partition"] != "final_test"}
    actual = {int(row.client_id): row for frame in parts.values()
              for row in frame.itertuples(index=False)}
    assert set(actual) == set(expected)
    for identifier, row in actual.items():
        assert row.fingerprint == expected[identifier]["fingerprint"]
        assert row.default_next_month == records[identifier - 1]["default_next_month"]
        assert pd.isna(getattr(row, column))


def test_missing_demographics_remain_unknown_in_descriptive_audit(tmp_path):
    records = make_records()
    for row in records:
        for column in ("sex", "age", "education", "marriage"):
            row[column] = None
    parts = routed_partitions(tmp_path, _exports(tmp_path, records))
    validation = parts["policy_validation"]
    assert validation[["sex", "age", "education", "marriage"]].isna().all().all()
    _, demographics, _ = descriptive_slices(parts["development"], validation,
                                            np.full(len(validation), .2))
    assert set(demographics.group) == {"unknown"}
    assert set(demographics.attribute) == {"sex", "education", "marriage", "age_band"}
    assert demographics.n.sum() == 4 * len(validation)


def test_nonfinite_literal_is_not_a_missing_history(tmp_path):
    assignments = _exports(tmp_path, make_records())
    path = tmp_path / "data/processed/financial_features_v1.csv"
    frame = pd.read_csv(path)
    frame[BILL_COLUMNS[0]] = frame[BILL_COLUMNS[0]].astype(float)
    identifier = next(row["client_id"] for row in assignments if row["partition"] == "development")
    frame.loc[frame.client_id == identifier, BILL_COLUMNS[0]] = float("inf")
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="Nonfinite financial value"):
        routed_partitions(tmp_path, assignments)
