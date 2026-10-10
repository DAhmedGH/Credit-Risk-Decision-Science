"""Row-only feature formulas and separation from labels and audit fields."""

import copy
import json
import math
import unittest

from credit_risk.data.schema import BILL_COLUMNS, PAYMENT_COLUMNS, RAW_PREDICTORS, STATUS_COLUMNS
from credit_risk.features import PREDICTORS, build_features, feature_contract
from fixtures.records import make_record


class FeatureTests(unittest.TestCase):
    def test_nonfinite_arithmetic_cannot_enter_predictor_output(self):
        record = make_record()
        record["limit_bal"] = 1e-308
        with self.assertRaisesRegex(ValueError, "finite"):
            build_features(record)

    def test_formula_values_and_month_order(self):
        result = build_features(make_record())
        self.assertEqual(result["recent_delinquency_count"], 3)
        self.assertEqual(result["maximum_positive_delay"], 3)
        self.assertEqual(result["recent_history_delay_contrast"], 2)
        self.assertEqual(result["latest_utilization_proxy"], 0.6)
        self.assertEqual(result["mean_utilization_proxy"], 0.2)
        self.assertEqual(result["bill_balance_change"], 0.7)
        self.assertAlmostEqual(result["bill_volatility_proxy"], math.sqrt(340000 / 6) / 1000)
        self.assertEqual(result["mean_payment"], 25)
        self.assertEqual(result["zero_payment_count"], 1)
        self.assertEqual(result["payment_to_prior_bill_proxy"], 0.125)
        self.assertEqual(result["payment_to_prior_bill_missing"], 0)
        self.assertAlmostEqual(result["aggregate_payment_balance_proxy"], 150 / 1300)
        self.assertEqual(result["aggregate_payment_balance_missing"], 0)

    def test_explicit_predictors_exclude_audit_id_and_target(self):
        record = make_record()
        result = build_features(record)
        self.assertEqual(tuple(result), PREDICTORS)
        self.assertEqual(len(PREDICTORS), 32)
        for column in ("client_id", "default_next_month", "sex", "age", "education", "marriage"):
            self.assertNotIn(column, result)
        unlabeled = {column: record[column] for column in RAW_PREDICTORS}
        self.assertEqual(build_features(unlabeled), result)

    def test_target_audit_and_other_rows_cannot_change_features(self):
        row = make_record()
        before = copy.deepcopy(row)
        result = build_features(row)
        row.update(client_id=999, default_next_month=1, sex=1, age=100, education=6, marriage=3)
        self.assertEqual(build_features(row), result)
        # No process-global state, population vocabulary, or aggregate fitted
        # statistic can be changed by an unrelated held-out sentinel row.
        sentinel = make_record(2)
        sentinel["limit_bal"] = 1e30
        sentinel[BILL_COLUMNS[-1]] = 1e20
        build_features(sentinel)
        self.assertEqual(build_features(before), result)

    def test_signed_utilization_and_no_canonical_clipping(self):
        row = make_record()
        row[BILL_COLUMNS[-1]] = -100
        result = build_features(row)
        self.assertEqual(result["latest_utilization_proxy"], -0.1)
        row[BILL_COLUMNS[-1]] = 3000
        self.assertEqual(build_features(row)["latest_utilization_proxy"], 3)

    def test_nonpositive_or_missing_prior_bill_is_missing_with_flag(self):
        for value in (0, -10, None):
            row = make_record()
            row[BILL_COLUMNS[-2]] = value
            result = build_features(row)
            self.assertIsNone(result["payment_to_prior_bill_proxy"])
            self.assertEqual(result["payment_to_prior_bill_missing"], 1)

    def test_zero_or_missing_aggregate_denominator_is_missing_with_flag(self):
        for values in ([0] * 6, [-10] * 6, [100, 100, 100, None, 100, 100]):
            row = make_record()
            row.update(zip(BILL_COLUMNS, values, strict=True))
            result = build_features(row)
            self.assertIsNone(result["aggregate_payment_balance_proxy"])
            self.assertEqual(result["aggregate_payment_balance_missing"], 1)

    def test_missing_inputs_propagate_without_implicit_imputation(self):
        row = make_record()
        row[STATUS_COLUMNS[0]] = None
        row[PAYMENT_COLUMNS[0]] = None
        row[BILL_COLUMNS[1]] = None
        result = build_features(row)
        for column in (
            "recent_delinquency_count", "maximum_positive_delay", "recent_history_delay_contrast",
            "mean_payment", "zero_payment_count", "mean_utilization_proxy", "bill_volatility_proxy",
        ):
            self.assertIsNone(result[column])
        self.assertEqual(result["bill_balance_change"], 0.7)

    def test_special_statuses_remain_distinct_and_constant_bills_have_zero_sd(self):
        row = make_record()
        row.update(zip(STATUS_COLUMNS, (-2, -1, 0, -2, -1, 0), strict=True))
        row.update({column: 25 for column in BILL_COLUMNS})
        result = build_features(row)
        self.assertEqual(result[STATUS_COLUMNS[0]], -2)
        self.assertEqual(result[STATUS_COLUMNS[1]], -1)
        self.assertEqual(result[STATUS_COLUMNS[2]], 0)
        self.assertEqual(result["recent_delinquency_count"], 0)
        self.assertEqual(result["maximum_positive_delay"], 0)
        self.assertEqual(result["bill_volatility_proxy"], 0)

    def test_bad_or_missing_limit_cannot_silently_divide_by_zero(self):
        for limit in (0, -100, math.nan, math.inf):
            row = make_record()
            row["limit_bal"] = limit
            with self.assertRaises(ValueError):
                build_features(row)
        row = make_record()
        row["limit_bal"] = None
        result = build_features(row)
        self.assertIsNone(result["latest_utilization_proxy"])
        self.assertIsNone(result["mean_utilization_proxy"])

    def test_missing_schema_rejected_and_contract_serializes(self):
        row = make_record()
        del row[PAYMENT_COLUMNS[0]]
        with self.assertRaisesRegex(ValueError, "Missing raw"):
            build_features(row)
        contract = json.loads(json.dumps(feature_contract()))
        self.assertEqual(contract["predictors"], list(PREDICTORS))
        self.assertEqual(len(contract["derived"]), 13)


if __name__ == "__main__":
    unittest.main()
