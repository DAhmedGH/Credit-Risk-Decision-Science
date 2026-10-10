"""Reproduce qualified Phase 1 data evidence without optional third-party imports.

This uses the independent bounded BIFF diagnostic, not the canonical xlrd/SQL
pipeline. It cannot pass the complete Phase 1 exit gate. It never fits models.
Run from the project root with PYTHONPATH=src.
"""

import json
import sys

from credit_risk.artifacts import file_sha256, read_csv, write_csv, write_json
from credit_risk.config import PROJECT_ROOT, load_config, project_path
from credit_risk.data.schema import validate_records
from credit_risk.features import FEATURE_VERSION, PREDICTORS, build_features, feature_contract
from credit_risk.phase1 import (
    development_report, freeze_splits, log_source_access, provenance_context, stage_metadata,
)


def main():
    config = load_config()
    _, source_sha = provenance_context(config)
    metadata = json.loads((PROJECT_ROOT / "data/processed/inspection_metadata.json").read_text())
    records_path = PROJECT_ROOT / "data/processed/inspection_records.jsonl"
    if metadata["source_sha256"] != source_sha or metadata["records_sha256"] != file_sha256(records_path):
        raise ValueError("Inspection data/source checksum mismatch")
    if metadata["script_sha256"] != file_sha256(PROJECT_ROOT / "scripts/inspect_supplied_workbook.py"):
        raise ValueError("Diagnostic parser code differs from its recorded execution")
    log_source_access("independent diagnostic validation/split freeze", source_sha,
                      project_path(config["split_manifest"]))
    records = [json.loads(line) for line in records_path.read_text().splitlines()]
    validated = validate_records(records)
    scope = "independent-biff-diagnostic; canonical-xlrd-parity-pending"
    version = config["dataset_version"]
    validation = {**validated.summary, **stage_metadata(config, source_sha), "evidence_scope": scope,
                  "inspection_records_sha256": metadata["records_sha256"]}
    from credit_risk.artifacts import write_run_evidence

    write_run_evidence(PROJECT_ROOT / f"reports/inspection_validation_{version}.json", validation)
    write_json(project_path(config["feature_contract"]), feature_contract(), frozen=True)
    rows = [{"client_id": row["client_id"], **build_features(row)} for row in validated.accepted]
    write_csv(PROJECT_ROOT / "data/processed/inspection_financial_features_v1.csv", rows,
              ("client_id", *PREDICTORS), frozen=True)
    reconciliation = {**stage_metadata(config, source_sha), "evidence_scope": scope,
                      "source_rows": len(records), "accepted_rows": len(validated.accepted),
                      "rejected_rows": len(validated.rejected), "python_feature_rows": len(rows),
                      "python_counts_reconcile": len(records) == len(validated.accepted) + len(validated.rejected)
                      and len(rows) == len(validated.accepted),
                      "postgresql_curated_rows": None, "sql_export_rows": None,
                      "postgresql_idempotency_verified": False}
    write_run_evidence(PROJECT_ROOT / f"reports/inspection_reconciliation_{version}.json", reconciliation)
    partitions = freeze_splits(config, validated.accepted, source_sha, evidence_scope=scope)
    manifest = read_csv(project_path(config["split_manifest"]))
    report = development_report(validated.accepted, manifest, source_sha)
    report.update(stage_metadata(config, source_sha))
    report.update({"evidence_scope": scope, "split_manifest_sha256": partitions["manifest_file_sha256"],
                   "feature_version": FEATURE_VERSION})
    write_run_evidence(PROJECT_ROOT / f"reports/inspection_development_eda_{version}.json", report)
    result = {"validation": {key: validation[key] for key in
                             ("source_rows", "accepted_rows", "rejected_rows")},
              "python_counts_reconcile": reconciliation["python_counts_reconcile"],
              "partitions": {name: value["rows"] for name, value in partitions["partitions"].items()},
              "development_folds": {name: value["rows"] for name, value in partitions["development_folds"].items()},
              "group_count": partitions["group_count"], "integrity": partitions["integrity"],
              "split_manifest_sha256": partitions["manifest_file_sha256"],
              "evidence_scope": scope, "full_phase1_gate": "pending canonical runtime and PostgreSQL checks"}
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(f"Inspection stopped: {error}", file=sys.stderr)
        sys.exit(1)
