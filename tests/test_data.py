"""Synthetic tests for source integrity and the conservative cleaning contract."""

import hashlib
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from credit_risk.data.schema import (
    AUDIT_COLUMNS,
    BILL_COLUMNS,
    NORMALIZED_COLUMNS,
    RAW_PREDICTORS,
    SOURCE_COLUMNS,
    SOURCE_TO_NORMALIZED,
    STATUS_COLUMNS,
    DataContractError,
    audit_group,
    validate_records,
)
from credit_risk.data.workbook import load_workbook
from fixtures.records import make_record


class SchemaTests(unittest.TestCase):
    def test_storage_and_engineered_arithmetic_ranges_are_validated(self):
        row = make_record()
        row["client_id"] = 2**63
        with self.assertRaises(DataContractError):
            validate_records([row])
        for column, value, reason in (
            ("age", 2**31, "age:integer_storage_range"),
            ("education", 2**31, "education:integer_storage_range"),
            ("bill_amt_2005_09", 1e200, "engineered_features:arithmetic_range"),
            ("limit_bal", 1e-308, "engineered_features:arithmetic_range"),
            ("limit_bal", 10**1000, "limit_bal:non_finite"),
        ):
            row = make_record()
            row[column] = value
            result = validate_records([row])
            with self.subTest(column=column, value=str(value)[:20]):
                self.assertEqual(len(result.rejected), 1)
                self.assertIn(reason, result.rejected[0]["reasons"])

    def test_explicit_schema_and_allowlist(self):
        self.assertEqual(len(SOURCE_COLUMNS), 25)
        self.assertEqual(len(NORMALIZED_COLUMNS), 25)
        self.assertEqual(len(RAW_PREDICTORS), 19)
        self.assertFalse(set(RAW_PREDICTORS) & {"client_id", "default_next_month", *AUDIT_COLUMNS})

    def test_irregular_source_month_mapping(self):
        expected = {
            "PAY_0": "pay_status_2005_09", "PAY_2": "pay_status_2005_08",
            "PAY_3": "pay_status_2005_07", "PAY_4": "pay_status_2005_06",
            "PAY_5": "pay_status_2005_05", "PAY_6": "pay_status_2005_04",
            "BILL_AMT1": "bill_amt_2005_09", "BILL_AMT6": "bill_amt_2005_04",
            "PAY_AMT1": "pay_amt_2005_09", "PAY_AMT6": "pay_amt_2005_04",
        }
        for source, normalized in expected.items():
            self.assertEqual(SOURCE_TO_NORMALIZED[source], normalized)

    def test_signed_balances_special_codes_and_original_values_preserved(self):
        record = make_record()
        result = validate_records([record])
        self.assertEqual(result.accepted, [record])
        self.assertEqual(result.accepted[0][BILL_COLUMNS[0]], -100)
        self.assertEqual([result.accepted[0][column] for column in STATUS_COLUMNS[:3]], [-2, -1, 0])
        self.assertEqual(record, make_record())

    def test_xls_integral_floats_normalize_to_ints(self):
        record = {column: float(value) for column, value in make_record().items()}
        result = validate_records([record])
        self.assertEqual(len(result.accepted), 1)
        self.assertIsInstance(result.accepted[0]["client_id"], int)
        self.assertIsInstance(result.accepted[0]["default_next_month"], int)

    def test_duplicate_or_invalid_id_aborts(self):
        with self.assertRaisesRegex(DataContractError, "duplicate"):
            validate_records([make_record(), make_record()])
        for identifier in (None, 0, -1, 1.2, "1", True, math.inf, math.nan):
            with self.subTest(identifier=identifier):
                record = make_record()
                record["client_id"] = identifier
                with self.assertRaises(DataContractError):
                    validate_records([record])

    def test_schema_drift_aborts(self):
        for column, add in (("unexpected", True), ("sex", False)):
            record = make_record()
            if add:
                record[column] = 42
            else:
                del record[column]
            with self.assertRaisesRegex(DataContractError, "schema mismatch"):
                validate_records([record])

    def test_invalid_target_quarantines_and_counts_reconcile(self):
        for target in (None, 2, "1", True, 0.5, math.inf):
            with self.subTest(target=target):
                result = validate_records([make_record(1), make_record(2, target)])
                self.assertEqual(result.summary["source_rows"], 2)
                self.assertEqual(result.summary["accepted_rows"], 1)
                self.assertEqual(result.summary["rejected_rows"], 1)
                self.assertTrue(result.summary["counts_reconcile"])
                self.assertEqual(result.rejected[0]["client_id"], 2)
                self.assertTrue(result.rejected[0]["reasons"])
                self.assertNotIn("default_next_month", result.summary["category_code_inventory"])

    def test_numeric_types_finiteness_and_limit_validation(self):
        for value in ("1000", True, math.inf, -math.inf, math.nan, 0, -1000, None):
            with self.subTest(value=value):
                record = make_record()
                record["limit_bal"] = value
                result = validate_records([record])
                self.assertEqual(len(result.rejected), 1)
        record = make_record()
        record[BILL_COLUMNS[0]] = math.nan
        self.assertIn("bill_amt_2005_04:non_finite", validate_records([record]).rejected[0]["reasons"])

    def test_missing_histories_are_preserved_for_fold_imputation(self):
        record = make_record()
        record[BILL_COLUMNS[0]] = None
        record[STATUS_COLUMNS[1]] = None
        result = validate_records([record])
        self.assertEqual(result.accepted, [record])
        self.assertEqual(result.summary["missing_by_column"][BILL_COLUMNS[0]], 1)

    def test_out_of_contract_or_fractional_repayment_status_quarantines(self):
        for value in (-3, 10, 0.5):
            record = make_record()
            record[STATUS_COLUMNS[0]] = value
            self.assertEqual(len(validate_records([record]).rejected), 1)

    def test_demographic_special_codes_keep_audit_unknown_group(self):
        for code in (0, 5, 6, 99):
            record = make_record()
            record["education"] = code
            result = validate_records([record])
            self.assertEqual(result.accepted[0]["education"], code)
            self.assertEqual(audit_group("education", code), "unknown")
        self.assertEqual(audit_group("education", 4), "other")
        self.assertEqual(audit_group("marriage", 0), "unknown")


class WorkbookTests(unittest.TestCase):
    def _reader(self, header=SOURCE_COLUMNS, aliases=None, cell_type=2, sheets=("Data",)):
        if aliases is None:
            aliases = ("", *(f"X{i}" for i in range(1, 24)), "Y")

        class Sheet:
            name = "Data"
            ncols = 25
            nrows = 3

            def row_values(self, index):
                return list(aliases if index == 0 else header)

            def cell(self, row_index, column_index):
                return types.SimpleNamespace(
                    ctype=cell_type, value=make_record()[NORMALIZED_COLUMNS[column_index]]
                )

        class Book:
            released = False

            def sheet_names(self):
                return list(sheets)

            def sheet_by_name(self, name):
                return Sheet()

            def release_resources(self):
                self.released = True

        book = Book()
        module = types.SimpleNamespace(
            __version__="fixture",
            open_workbook=lambda **kwargs: book,
            XL_CELL_EMPTY=0,
            XL_CELL_BLANK=6,
            XL_CELL_NUMBER=2,
        )
        return module, book

    def test_reader_keeps_bytes_hash_and_header_interpretation(self):
        reader, book = self._reader()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-reader.xls"
            original = b"software fixture; not a real source workbook"
            path.write_bytes(original)
            with patch.dict(sys.modules, {"xlrd": reader}):
                loaded = load_workbook(path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(loaded.sha256, hashlib.sha256(original).hexdigest())
            self.assertEqual(loaded.records, [make_record()])
            self.assertEqual(loaded.metadata["header_row_excel"], 2)
            self.assertEqual(loaded.metadata["data_start_row_excel"], 3)
            self.assertTrue(book.released)

    def test_unexpected_header_or_variable_row_aborts_and_closes_reader(self):
        for kwargs in ({"header": ("WRONG", *SOURCE_COLUMNS[1:])}, {"aliases": ("wrong",) * 25}):
            reader, book = self._reader(**kwargs)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "fixture.xls"
                path.write_bytes(b"fixture")
                with patch.dict(sys.modules, {"xlrd": reader}):
                    with self.assertRaises(DataContractError):
                        load_workbook(path)
                self.assertTrue(book.released)

    def test_excel_boolean_does_not_become_a_numeric_training_label(self):
        reader, _ = self._reader(cell_type=4)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.xls"
            path.write_bytes(b"fixture")
            with patch.dict(sys.modules, {"xlrd": reader}):
                loaded = load_workbook(path)
            # Even the boolean-typed ID is rejected before ingestion; Excel
            # cell-type values cannot masquerade as numeric training records.
            with self.assertRaises(DataContractError):
                validate_records(loaded.records)

    def test_missing_data_sheet_aborts(self):
        reader, book = self._reader(sheets=("Changed",))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.xls"
            path.write_bytes(b"fixture")
            with patch.dict(sys.modules, {"xlrd": reader}):
                with self.assertRaisesRegex(DataContractError, "'Data' sheet"):
                    load_workbook(path)
            self.assertTrue(book.released)

    def test_excel_text_date_and_error_types_remain_invalid_values(self):
        for cell_type in (1, 3, 5):
            reader, _ = self._reader(cell_type=cell_type)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "fixture.xls"
                path.write_bytes(b"fixture")
                with patch.dict(sys.modules, {"xlrd": reader}):
                    loaded = load_workbook(path)
                self.assertEqual(
                    loaded.records[0]["default_next_month"],
                    {"excel_cell_type": cell_type, "value": 0},
                )


if __name__ == "__main__":
    unittest.main()
