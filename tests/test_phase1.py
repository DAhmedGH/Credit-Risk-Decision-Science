"""Protect source/freeze contracts and development-only reporting."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from credit_risk.artifacts import atomic_write, file_sha256, read_csv, write_csv, write_run_evidence
from credit_risk.phase1 import development_report, freeze_splits, provenance_context
from credit_risk.splits import allocate_records
from fixtures.records import make_records


class Phase1Tests(unittest.TestCase):
    def test_execution_provenance_refresh_preserves_prior_evidence_and_rejects_scientific_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            report = {"source_sha256": "a" * 64, "rows": 120, "git_commit": None, "code_tree_sha256": "old"}
            write_run_evidence(path, report)
            revised = {**report, "git_commit": "commit", "code_tree_sha256": "new"}
            write_run_evidence(path, revised)
            self.assertEqual(json.loads(path.read_text()), revised)
            snapshots = list((path.parent / "history").glob("*.json"))
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(json.loads(snapshots[0].read_text()), report)
            with self.assertRaisesRegex(ValueError, "Scientific evidence changed"):
                write_run_evidence(path, {**revised, "rows": 121})
    def test_freeze_is_repeatable_and_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frozen.csv"
            atomic_write(path, b"original\n", frozen=True)
            atomic_write(path, b"original\n", frozen=True)
            with self.assertRaisesRegex(ValueError, "frozen"):
                atomic_write(path, b"different\n", frozen=True)
            self.assertEqual(path.read_bytes(), b"original\n")

    def test_source_provenance_checks_actual_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.xls"
            source.write_bytes(b"source bytes")
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(json.dumps({"workbook": {"sha256": file_sha256(source), "byte_count": 12}}))
            config = {"workbook": str(source), "provenance": str(manifest)}
            self.assertEqual(provenance_context(config)[1], file_sha256(source))
            source.write_bytes(b"changed bytes")
            with self.assertRaisesRegex(ValueError, "differs"):
                provenance_context(config)

    def test_frozen_manifest_survives_csv_roundtrip_and_detects_tampering(self):
        records = make_records()
        with tempfile.TemporaryDirectory() as directory:
            config = {"split_manifest": str(Path(directory) / "split.csv"),
                      "split_summary": str(Path(directory) / "summary.json"), "seed": 42}
            first = freeze_splits(config, records, "a" * 64)
            second = freeze_splits(config, records[::-1], "a" * 64)
            self.assertEqual(first, second)
            rows = read_csv(config["split_manifest"])
            rows[0]["partition"] = "final_test" if rows[0]["partition"] != "final_test" else "calibration"
            write_csv(config["split_manifest"], rows, tuple(rows[0]))
            with self.assertRaisesRegex(ValueError, "Manifest differs"):
                freeze_splits(config, records, "a" * 64)

    def test_development_eda_never_uses_heldout_values_or_outcomes(self):
        records = make_records()
        manifest, _ = allocate_records(records, "a" * 64)
        original = development_report(records, manifest, "a" * 64)
        heldout = {row["client_id"] for row in manifest if row["partition"] != "development"}
        altered = copy.deepcopy(records)
        for row in altered:
            if row["client_id"] in heldout:
                row["default_next_month"] = object()  # Cannot be aggregated as an outcome.
                row["limit_bal"] = object()  # Cannot enter feature calculations either.
        # Structural split validation is separately tested; isolate the report's
        # access pattern to prove filtering precedes every summary calculation.
        with patch("credit_risk.phase1.validate_manifest"):
            self.assertEqual(development_report(altered, manifest, "a" * 64), original)
        self.assertEqual(original["scope"], "development only")
        self.assertNotIn("final_test", json.dumps(original))


if __name__ == "__main__":
    unittest.main()
