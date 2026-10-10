"""Fixture-only SQL checks; live integration is explicit and never downloads data."""

import copy
import os
import unittest

from credit_risk.config import PROJECT_ROOT
from credit_risk.data.database import (
    connect_database, export_features, ingest_records, reconcile,
    verify_database_identity, verify_feature_export,
)
from credit_risk.data.schema import validate_records
from credit_risk.features import PREDICTORS, build_features
from fixtures.records import make_records


class DatabaseContractTests(unittest.TestCase):
    def test_identity_is_required_before_any_project_ddl(self):
        class Result:
            def fetchone(self):
                return ("production", "admin", None, None)

        class Connection:
            calls = []

            def execute(self, statement):
                self.calls.append(statement)
                return Result()

        connection = Connection()
        with self.assertRaisesRegex(ValueError, "identity"):
            verify_database_identity(connection)
        self.assertEqual(len(connection.calls), 1)
        self.assertNotIn("CREATE", connection.calls[0])

    def test_feature_export_requires_exact_ids_schema_values_and_missingness(self):
        records = make_records(10)
        rows = [{"client_id": row["client_id"], **build_features(row)} for row in records]
        verify_feature_export(records, rows)
        for change in ("missing", "duplicate", "extra", "value", "null"):
            modified = copy.deepcopy(rows)
            if change == "missing":
                modified.pop()
            elif change == "duplicate":
                modified[-1] = modified[0]
            elif change == "extra":
                modified[0]["default_next_month"] = 1
            elif change == "value":
                modified[0]["maximum_positive_delay"] += 1
            else:
                modified[0]["latest_utilization_proxy"] = None
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify_feature_export(records, modified)

    def test_sql_export_uses_explicit_contract_not_target_or_audits(self):
        sql = (PROJECT_ROOT / "sql/003_feature_export.sql").read_text().split("SELECT", 1)[1]
        projection = sql.split("FROM", 1)[0].replace("\n", "")
        self.assertEqual([value.strip() for value in projection.split(",")], ["client_id", *PREDICTORS])
        self.assertNotIn("*", projection)
        self.assertIn("source_sha256 = %s", sql)


@unittest.skipUnless(os.environ.get("CREDIT_RISK_SQL_TEST") == "1", "dedicated PostgreSQL unavailable/not requested")
class PostgreSQLIntegrationTests(unittest.TestCase):
    def test_transaction_idempotency_quarantine_reconciliation_and_sql_python_parity(self):
        records = make_records()
        records[-1]["limit_bal"] = 0
        records[0]["bill_amt_2005_08"] = 0
        records[1]["bill_amt_2005_09"] = None
        records[2]["pay_status_2005_04"] = None
        records[3]["pay_amt_2005_09"] = None
        validated = validate_records(records)
        checksum = "f" * 64
        with connect_database() as connection:
            class RollbackFixture(Exception):
                pass

            try:
                with connection.transaction():
                    first = ingest_records(connection, records, validated, checksum, "synthetic-fixture-only")
                    second = ingest_records(connection, records, validated, checksum, "synthetic-fixture-only")
                    self.assertTrue(second["idempotent_noop"])
                    self.assertEqual(first["source_rows"], 120)
                    self.assertEqual(first["rejected_rows"], 1)
                    self.assertEqual(first["curated_rows"], 119)
                    self.assertEqual(first["exported_rows"], 119)
                    verify_feature_export(validated.accepted, export_features(connection, checksum))
                    self.assertEqual(reconcile(connection, checksum)["source_rows"], 120)
                    connection.execute("""
                        UPDATE curated.credit_clients SET default_next_month = 1 - default_next_month
                        WHERE source_sha256 = %s AND client_id = 1
                    """, (checksum,))
                    with self.assertRaisesRegex(ValueError, "Persisted predictors/label/audits"):
                        ingest_records(connection, records, validated, checksum, "synthetic-fixture-only")
                    raise RollbackFixture()
            except RollbackFixture:
                pass
            # Either fixture DDL was rolled back or pre-existing real tables survived.
            present = connection.execute("SELECT to_regclass('raw.ingestions')").fetchone()[0]
            if present:
                self.assertEqual(connection.execute(
                    "SELECT count(*) FROM raw.ingestions WHERE source_sha256 = %s", (checksum,)
                ).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
