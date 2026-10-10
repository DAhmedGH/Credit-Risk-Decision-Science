"""Read-only source/SQL/export integrity audit; log structural target access first.

Run from the project root with PYTHONPATH=src and the isolated Python environment.
No source outcome distribution, fitting, ingestion or final evaluation is performed.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from credit_risk.artifacts import file_sha256
from credit_risk.data.database import (
    connect_database,
    export_features,
    reconcile,
    verify_feature_export,
    verify_persisted_records,
)
from credit_risk.data.schema import validate_records
from credit_risk.data.workbook import load_workbook

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path,
                    default=root / "reports/project-audit-evidence/database.json",
                    help="New receipt path; existing evidence is never overwritten")
args = parser.parse_args()
output = args.output
if output.exists() or output.is_symlink():
    parser.error("Audit receipt already exists; choose --output NEW_PATH before any source access")
source = root / "data/raw/default of credit card clients.xls"
# The accepted workbook checksum is independently pinned in the audit request evidence.
expected = "30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933"
if file_sha256(source) != expected:
    raise ValueError("Accepted workbook bytes changed")
timestamp = datetime.now(timezone.utc).isoformat()
with (root / "docs/test-exposure-log.md").open("a") as stream:
    stream.write(
        "\n### Read-only audit source/SQL integrity " + timestamp + "\n\n"
        "Original workbook targets will be decoded only for schema/binary validity "
        "and exact persisted-source/curated/export reconciliation. No outcome "
        "distribution, model fitting, policy selection or final evaluation. "
        "Source SHA `" + expected + "`.\n"
    )
loaded = load_workbook(source)
validated = validate_records(loaded.records)
with connect_database() as connection:
    connection.execute("SET TRANSACTION READ ONLY")
    counts = reconcile(connection, expected)
    verify_persisted_records(connection, loaded.records, validated, expected)
    exported = export_features(connection, expected)
    verify_feature_export(validated.accepted, exported)
    # Compare SQL financial rows against the immutable accepted export, not just Python formulas.
    import csv
    from credit_risk.features import PREDICTORS
    import math

    with (root / "data/processed/financial_features_v1.csv").open(newline="") as stream:
        saved = {int(row["client_id"]): row for row in csv.DictReader(stream)}
    if set(saved) != {row["client_id"] for row in exported} or len(saved) != len(exported):
        raise ValueError("SQL/saved export ID coverage differs")
    for row in exported:
        for column in PREDICTORS:
            stored = saved[row["client_id"]][column]
            actual = row[column]
            if stored == "":
                equal = actual is None
            else:
                equal = actual is not None and math.isclose(
                    float(stored), float(actual), rel_tol=1e-10, abs_tol=1e-10
                )
            if not equal:
                raise ValueError("SQL/saved financial export mismatch")
    connection.rollback()
evidence = {
    "utc": timestamp,
    "source_sha256": expected,
    "counts": counts,
    "source_rows_validated": len(loaded.records),
    "accepted_rows": len(validated.accepted),
    "rejected_rows": len(validated.rejected),
    "persisted_source_curated_audit_exact": True,
    "sql_python_feature_agreement": True,
    "sql_saved_export_agreement": True,
    "read_only_transaction": True,
    "fits": 0,
    "outcome_distributions": False,
}
output.parent.mkdir(parents=True, exist_ok=True)
with output.open("x") as stream:
    stream.write(json.dumps(evidence, indent=2) + "\n")
print("Verified read-only workbook/source/curated/audit/SQL/export reconciliation:", counts)
