"""Synthetic structural tests; no real-data outcomes are inspected."""

import copy
import random
import unittest
from decimal import Decimal

from credit_risk.splits import allocate_records, financial_fingerprint, validate_manifest

PREDICTORS = ("credit_limit", "bill_april", "repayment_september")
SOURCE_SHA256 = "b" * 64


def fixture_records(count=240):
    records = [
        {
            "client_id": index + 1,
            "credit_limit": 10_000 + index * 100,
            "bill_april": -50 + index,
            "repayment_september": (index % 4) - 2,
            "default_next_month": int(index % 4 == 0),
            "sex": 1 + index % 2,
            "age": 21 + index % 50,
        }
        for index in range(count)
    ]
    for index in range(0, min(count, 24), 2):
        duplicate = dict(records[index])
        duplicate["client_id"] = count + index + 1
        duplicate["default_next_month"] = 1 - duplicate["default_next_month"]
        duplicate["sex"] = 3 - duplicate["sex"]
        records.append(duplicate)
    return records


class FingerprintTests(unittest.TestCase):
    def test_only_raw_financial_predictors_affect_fingerprint(self):
        record = fixture_records()[0]
        changed = dict(record, client_id=99999, default_next_month=1, sex=2, age=90)
        self.assertEqual(
            financial_fingerprint(record, PREDICTORS),
            financial_fingerprint(changed, PREDICTORS),
        )
        changed["bill_april"] += 1
        self.assertNotEqual(
            financial_fingerprint(record, PREDICTORS),
            financial_fingerprint(changed, PREDICTORS),
        )

    def test_numeric_equivalence_missingness_and_schema_are_explicit(self):
        record = dict(zip(PREDICTORS, (1, 0, -2), strict=True))
        equivalent = dict(zip(PREDICTORS, (Decimal("1.00"), -0.0, -2.0), strict=True))
        self.assertEqual(
            financial_fingerprint(record, PREDICTORS),
            financial_fingerprint(equivalent, PREDICTORS),
        )
        missing = dict(record, bill_april=None)
        self.assertNotEqual(
            financial_fingerprint(record, PREDICTORS),
            financial_fingerprint(missing, PREDICTORS),
        )
        self.assertNotEqual(
            financial_fingerprint(record, PREDICTORS),
            financial_fingerprint(record, tuple(reversed(PREDICTORS))),
        )
        del missing["bill_april"]
        with self.assertRaisesRegex(ValueError, "Missing financial"):
            financial_fingerprint(missing, PREDICTORS)

    def test_forbidden_schema_and_nonfinite_values_fail(self):
        for field in ("client_id", "default_next_month", "sex", "age", "education", "marriage"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                financial_fingerprint({field: 1}, (field,))
        for value in (float("nan"), float("inf"), "1", True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                financial_fingerprint({"credit_limit": value}, ("credit_limit",))


class SplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = fixture_records()
        cls.manifest, cls.summary = allocate_records(cls.records, SOURCE_SHA256, 42, PREDICTORS)

    def test_complete_and_group_disjoint_with_conflicting_labels(self):
        by_profile = {}
        for row in self.manifest:
            by_profile.setdefault(row["fingerprint"], set()).add((row["partition"], row["fold"]))
        self.assertTrue(all(len(destinations) == 1 for destinations in by_profile.values()))
        self.assertEqual(len(self.manifest), len(self.records))
        self.assertEqual(len({row["client_id"] for row in self.manifest}), len(self.records))
        self.assertEqual(self.summary["duplicate_profile_groups"], 12)
        self.assertTrue(all(self.summary["integrity"].values()))

    def test_partition_and_fold_balancing_has_measured_deviations(self):
        self.assertEqual(
            sum(partition["rows"] for partition in self.summary["partitions"].values()),
            len(self.records),
        )
        max_group = self.summary["largest_profile_group_rows"]
        for partition in self.summary["partitions"].values():
            self.assertLessEqual(abs(partition["row_deviation"]), max_group)
        dev_count = self.summary["partitions"]["development"]["rows"]
        self.assertEqual(
            sum(fold["rows"] for fold in self.summary["development_folds"].values()), dev_count
        )
        self.assertEqual(
            {row["fold"] for row in self.manifest if row["partition"] == "development"},
            set(range(5)),
        )
        for row in self.manifest:
            if row["partition"] != "development":
                self.assertIsNone(row["fold"])

    def test_input_order_reproducibility_and_csv_validation(self):
        reordered = copy.deepcopy(self.records)
        random.Random(999).shuffle(reordered)
        manifest, summary = allocate_records(reordered, SOURCE_SHA256, 42, PREDICTORS)
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(summary, self.summary)
        csv_manifest = [
            {key: "" if value is None else str(value) for key, value in row.items()}
            for row in reversed(manifest)
        ]
        self.assertEqual(
            validate_manifest(reordered, csv_manifest, SOURCE_SHA256, PREDICTORS), summary
        )

    def test_no_heldout_outcome_distribution_is_exposed(self):
        def check_keys(value):
            if isinstance(value, dict):
                for key, nested in value.items():
                    self.assertNotIn(
                        key, {"prevalence", "positive_count", "negative_count", "class_counts"}
                    )
                    check_keys(nested)
            elif isinstance(value, list):
                for nested in value:
                    check_keys(nested)

        check_keys(self.summary)
        self.assertFalse(any("default_next_month" in row for row in self.manifest))

    def test_changed_ids_source_features_and_assignment_are_rejected(self):
        changes = (
            lambda rows: rows.pop(),
            lambda rows: rows.append(copy.deepcopy(rows[0])),
            lambda rows: rows[0].update(client_id=999999),
            lambda rows: rows[0].update(source_sha256="c" * 64),
            lambda rows: rows[0].update(seed=43),
            lambda rows: rows[0].update(partition="other"),
            lambda rows: rows[0].update(fold=99),
            lambda rows: rows[0].update(fingerprint="d" * 64),
        )
        for index, change in enumerate(changes):
            modified = copy.deepcopy(self.manifest)
            change(modified)
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_manifest(self.records, modified, SOURCE_SHA256, PREDICTORS)
        changed_records = copy.deepcopy(self.records)
        changed_records[0]["bill_april"] += 0.5
        with self.assertRaises(ValueError):
            validate_manifest(changed_records, self.manifest, SOURCE_SHA256, PREDICTORS)
        with self.assertRaises(ValueError):
            validate_manifest(self.records, self.manifest, "e" * 64, PREDICTORS)

    def test_invalid_source_ids_targets_and_impossible_groups_fail(self):
        for field, value in (("client_id", 0), ("default_next_month", 2)):
            records = copy.deepcopy(self.records)
            records[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                allocate_records(records, SOURCE_SHA256, 42, PREDICTORS)
        with self.assertRaises(ValueError):
            allocate_records(self.records, "not-a-hash", 42, PREDICTORS)
        with self.assertRaisesRegex(ValueError, "Insufficient distinct"):
            allocate_records(fixture_records(4), SOURCE_SHA256, 42, PREDICTORS)

    def test_scarce_mixed_groups_are_reserved_for_two_class_folds(self):
        records = []
        for profile in range(8):
            for target in (0, 1):
                records.append(
                    {
                        "client_id": len(records) + 1,
                        "credit_limit": 1000 + profile,
                        "bill_april": None,
                        "repayment_september": -2,
                        "default_next_month": target,
                    }
                )
        for profile in range(60):
            records.append(
                {
                    "client_id": len(records) + 1,
                    "credit_limit": 2000 + profile,
                    "bill_april": 0,
                    "repayment_september": -1,
                    "default_next_month": 0,
                }
            )
        manifest, summary = allocate_records(records, SOURCE_SHA256, 42, PREDICTORS)
        self.assertTrue(all(summary["integrity"].values()))
        self.assertEqual(len(manifest), len(records))

    def test_many_minority_rows_in_one_profile_do_not_make_stratification_feasible(self):
        records = fixture_records(80)
        for record in records:
            if record["default_next_month"]:
                record.update(credit_limit=999_999, bill_april=0, repayment_september=-2)
        with self.assertRaisesRegex(ValueError, "Insufficient distinct"):
            allocate_records(records, SOURCE_SHA256, 42, PREDICTORS)


if __name__ == "__main__":
    unittest.main()
