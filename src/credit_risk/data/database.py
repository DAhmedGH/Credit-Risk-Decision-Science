"""Transactional ingestion/export, restricted to a marked disposable development DB."""

import math
from decimal import Decimal
from pathlib import Path

from credit_risk.artifacts import json_bytes, sha256_bytes
from credit_risk.config import PROJECT_ROOT, database_settings
from credit_risk.data.schema import RAW_PREDICTORS, audit_group
from credit_risk.features import PREDICTORS, build_features, feature_contract


def rules_sha256(root=PROJECT_ROOT):
    paths = ["src/credit_risk/data/schema.py", "src/credit_risk/data/workbook.py",
             "src/credit_risk/features/__init__.py", "sql/001_schema.sql",
             "sql/002_curated.sql", "sql/003_feature_export.sql"]
    return sha256_bytes(b"".join(name.encode() + b"\0" + (Path(root) / name).read_bytes()
                                 for name in paths))


def verify_database_identity(connection):
    identity = connection.execute("""
        SELECT current_database(), current_user,
               current_setting('credit_risk.project', true),
               current_setting('credit_risk.lifecycle', true)
    """).fetchone()
    expected = ("credit_risk_dev", "credit_risk_app", "credit-risk-decision-science",
                "disposable-development")
    if tuple(identity) != expected:
        raise ValueError("Database identity/lifecycle check failed; no project DDL or writes allowed")


def connect_database():
    import psycopg

    connection = psycopg.connect(**database_settings())
    try:
        verify_database_identity(connection)
        connection.commit()
        return connection
    except Exception:
        connection.close()
        raise


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {"invalid_numeric_literal": repr(value)}
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return value


def ingest_records(connection, source_records, validated, source_sha256, dataset_version):
    """Commit source, curated, audit, and reconciliation together; identical reruns are no-ops."""
    from psycopg.types.json import Jsonb

    contract_hash = sha256_bytes(json_bytes(feature_contract()))
    rules_hash = rules_sha256()
    with connection.transaction():
        verify_database_identity(connection)
        connection.execute("SELECT pg_advisory_xact_lock(3502026)")
        for sql_file in ("001_schema.sql", "002_curated.sql"):
            connection.execute((PROJECT_ROOT / "sql" / sql_file).read_text())
        prior = connection.execute("""
            SELECT dataset_version, rules_sha256, feature_contract_sha256,
                   source_rows, accepted_rows, rejected_rows
            FROM raw.ingestions WHERE source_sha256 = %s
        """, (source_sha256,)).fetchone()
        summary = validated.summary
        signature = (dataset_version, rules_hash, contract_hash, len(source_records),
                     len(validated.accepted), len(validated.rejected))
        if prior is not None:
            if tuple(prior) != signature:
                raise ValueError("Existing source uses different rules/version/counts; preserve it and version the change")
            result = reconcile(connection, source_sha256)
            verify_persisted_records(connection, source_records, validated, source_sha256)
            verify_feature_export(validated.accepted, export_features(connection, source_sha256))
            return {**result, "idempotent_noop": True, "rules_sha256": rules_hash}
        connection.execute("""
            INSERT INTO raw.ingestions
            (source_sha256, dataset_version, rules_sha256, feature_contract_sha256,
             source_rows, accepted_rows, rejected_rows, validation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (source_sha256, *signature, Jsonb(summary)))
        rejected = {row["client_id"]: row["reasons"] for row in validated.rejected}
        with connection.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO raw.credit_clients
                (source_sha256, client_id, source_row, source_values, accepted, rejection_reasons)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [(source_sha256, int(row["client_id"]), index + 3, Jsonb(_json_safe(row)),
                    int(row["client_id"]) not in rejected,
                    Jsonb(rejected.get(int(row["client_id"]), [])))
                   for index, row in enumerate(source_records)])
            columns = ("source_sha256", "client_id", *RAW_PREDICTORS, "default_next_month")
            placeholders = ", ".join(["%s"] * len(columns))
            cursor.executemany(
                f"INSERT INTO curated.credit_clients ({', '.join(columns)}) VALUES ({placeholders})",
                [(source_sha256, row["client_id"], *(_pg_numeric(row[column]) for column in RAW_PREDICTORS),
                  row["default_next_month"]) for row in validated.accepted],
            )
            cursor.executemany("""
                INSERT INTO curated.audit_attributes
                (source_sha256, client_id, sex, age, education, marriage,
                 sex_group, education_group, marriage_group)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [(source_sha256, row["client_id"], row["sex"], row["age"], row["education"],
                    row["marriage"], *(audit_group(column, row[column])
                                       for column in ("sex", "education", "marriage")))
                   for row in validated.accepted])
        result = reconcile(connection, source_sha256)
        verify_persisted_records(connection, source_records, validated, source_sha256)
        verify_feature_export(validated.accepted, export_features(connection, source_sha256))
        return {**result, "idempotent_noop": False, "rules_sha256": rules_hash}


def _pg_numeric(value):
    return None if value is None else Decimal(str(value))


def verify_persisted_records(connection, source_records, validated, source_sha256):
    """Counts alone cannot detect changed labels, audit attributes, or financial values."""
    rejected = {row["client_id"]: row["reasons"] for row in validated.rejected}
    stored_source = connection.execute("""
        SELECT client_id, source_row, source_values, accepted, rejection_reasons
        FROM raw.credit_clients WHERE source_sha256 = %s ORDER BY source_row
    """, (source_sha256,)).fetchall()
    if len(stored_source) != len(source_records):
        raise ValueError("Persisted source record count changed")
    for offset, (stored, original) in enumerate(zip(stored_source, source_records, strict=True)):
        client_id = int(original["client_id"])
        expected = (client_id, offset + 3, _json_safe(original), client_id not in rejected,
                    rejected.get(client_id, []))
        if tuple(stored) != expected:
            raise ValueError(f"Persisted raw source/rejection ledger disagrees for client {client_id}")
    projection = ", ".join(f"c.{column}" for column in RAW_PREDICTORS)
    stored = connection.execute(f"""
        SELECT c.client_id, {projection}, c.default_next_month,
               a.sex, a.age, a.education, a.marriage,
               a.sex_group, a.education_group, a.marriage_group
        FROM curated.credit_clients c JOIN curated.audit_attributes a
          USING (source_sha256, client_id)
        WHERE c.source_sha256 = %s ORDER BY c.client_id
    """, (source_sha256,)).fetchall()
    accepted = sorted(validated.accepted, key=lambda row: row["client_id"])
    if len(stored) != len(accepted):
        raise ValueError("Persisted curated/audit record count changed")
    for actual, row in zip(stored, accepted, strict=True):
        expected = (row["client_id"], *(_pg_numeric(row[column]) for column in RAW_PREDICTORS),
                    row["default_next_month"], row["sex"], row["age"], row["education"], row["marriage"],
                    *(audit_group(column, row[column]) for column in ("sex", "education", "marriage")))
        if tuple(actual) != expected:
            raise ValueError(f"Persisted predictors/label/audits disagree for client {row['client_id']}")


def export_features(connection, source_sha256):
    cursor = connection.execute((PROJECT_ROOT / "sql/003_feature_export.sql").read_text(),
                                (source_sha256,))
    columns = [column.name for column in cursor.description]
    if columns != ["client_id", *PREDICTORS]:
        raise ValueError("SQL predictor allowlist/order disagrees with the versioned contract")
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def verify_feature_export(records, exported):
    expected = {row["client_id"]: build_features(row) for row in records}
    if len(exported) != len(expected) or {row["client_id"] for row in exported} != set(expected):
        raise ValueError("Feature export lost or duplicated IDs")
    for row in exported:
        if set(row) != {"client_id", *PREDICTORS}:
            raise ValueError("Unexpected feature export schema")
        for name, python_value in expected[row["client_id"]].items():
            sql_value = row[name]
            if python_value is None or sql_value is None:
                equal = python_value is None and sql_value is None
            else:
                equal = math.isclose(float(sql_value), float(python_value), rel_tol=1e-10,
                                     abs_tol=1e-10)
            if not equal:
                raise ValueError(f"SQL/Python feature disagreement: client {row['client_id']}, {name}")


def reconcile(connection, source_sha256):
    expected = connection.execute("""
        SELECT source_rows, accepted_rows, rejected_rows FROM raw.ingestions WHERE source_sha256 = %s
    """, (source_sha256,)).fetchone()
    if expected is None:
        raise ValueError("Source has not been ingested")
    counts = {}
    for name, table in (("source_rows", "raw.credit_clients"),
                        ("curated_rows", "curated.credit_clients"),
                        ("audit_rows", "curated.audit_attributes"),
                        ("exported_rows", "curated.model_features_v1")):
        counts[name] = connection.execute(
            f"SELECT count(*) FROM {table} WHERE source_sha256 = %s", (source_sha256,)
        ).fetchone()[0]
    counts["rejected_rows"] = connection.execute("""
        SELECT count(*) FROM raw.credit_clients WHERE source_sha256 = %s AND NOT accepted
    """, (source_sha256,)).fetchone()[0]
    if (counts["source_rows"], counts["curated_rows"], counts["rejected_rows"]) != tuple(expected):
        raise ValueError("Source/curated/rejected database counts disagree with ingestion metadata")
    if counts["source_rows"] != counts["curated_rows"] + counts["rejected_rows"]:
        raise ValueError("Source-to-curated row reconciliation failed")
    if not counts["curated_rows"] == counts["audit_rows"] == counts["exported_rows"]:
        raise ValueError("Curated/audit/SQL-export row reconciliation failed")
    return {"source_sha256": source_sha256, **counts, "counts_reconcile": True}
