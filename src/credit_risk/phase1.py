"""Phase 1 orchestration. No predictive fitting, held-out EDA, or evaluation."""

from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess

from credit_risk.artifacts import (
    atomic_write, file_sha256, json_bytes, read_csv, sha256_bytes, write_csv, write_json,
    write_run_evidence,
)
from credit_risk.config import PROJECT_ROOT, project_path
from credit_risk.data.database import (
    connect_database, export_features, ingest_records, reconcile, rules_sha256, verify_feature_export,
    verify_persisted_records,
)
from credit_risk.data.schema import AUDIT_COLUMNS, RAW_PREDICTORS, validate_records
from credit_risk.data.workbook import load_workbook
from credit_risk.features import FEATURE_VERSION, PREDICTORS, build_features, feature_contract
from credit_risk.splits import allocate_records, validate_manifest


def provenance_context(config):
    source = project_path(config["workbook"])
    manifest = json.loads(project_path(config["provenance"]).read_text())
    actual = file_sha256(source)
    if actual != manifest["workbook"]["sha256"]:
        raise ValueError("Workbook differs from the pinned provenance; do not replace a frozen source")
    if source.stat().st_size != manifest["workbook"]["byte_count"]:
        raise ValueError("Workbook size differs from provenance")
    return source, actual


def log_source_access(stage, source_sha256, split_path=None, root=PROJECT_ROOT):
    """Record permitted structural label access before parsing, including failed attempts."""
    target = Path(root) / "docs/test-exposure-log.md"
    split_hash = file_sha256(split_path) if split_path and Path(split_path).exists() else "not frozen yet"
    timestamp = datetime.now(timezone.utc).isoformat()
    entry = (f"\n| {timestamp} — {stage} | Source read requested; targets may be parsed for "
             f"integrity/stratification only | source `{source_sha256}`, split `{split_hash}` | "
             "No held-out outcome summaries or predictive evaluation authorized |\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a") as stream:
        stream.write(entry)


def source_records(config, stage):
    source, checksum = provenance_context(config)
    log_source_access(stage, checksum, project_path(config["split_manifest"]))
    workbook = load_workbook(source)
    if workbook.sha256 != checksum:
        raise ValueError("Source changed while parsing")
    result = validate_records(workbook.records)
    if not result.accepted:
        raise ValueError("No valid rows remain")
    return workbook, result


def stage_metadata(config, source_sha256):
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True,
                                capture_output=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    code_paths = (sorted((PROJECT_ROOT / "src").rglob("*.py"))
                  + sorted((PROJECT_ROOT / "sql").glob("*.sql"))
                  + sorted((PROJECT_ROOT / "scripts").glob("*.py"))
                  + [PROJECT_ROOT / "scripts/bootstrap.sh"])
    code_hash = sha256_bytes(b"".join(str(path.relative_to(PROJECT_ROOT)).encode() + b"\0" + path.read_bytes()
                                     for path in code_paths))
    return {"source_sha256": source_sha256, "dataset_version": config["dataset_version"],
            "rules_sha256": rules_sha256(),
            "feature_contract_sha256": sha256_bytes(json_bytes(feature_contract())),
            "lock_sha256": file_sha256(PROJECT_ROOT / "requirements.lock"),
            "git_commit": commit, "code_tree_sha256": code_hash}


def validate(config):
    workbook, validated = source_records(config, "validate")
    report = {**validated.summary, **stage_metadata(config, workbook.sha256),
              "workbook_parsing": workbook.metadata}
    write_run_evidence(PROJECT_ROOT / "reports/source_validation.json", report)
    write_json(project_path(config["feature_contract"]), feature_contract(), frozen=True)
    return {key: report[key] for key in ("source_rows", "accepted_rows", "rejected_rows", "counts_reconcile")}


def ingest(config):
    workbook, validated = source_records(config, "ingest")
    with connect_database() as connection:
        report = ingest_records(connection, workbook.records, validated,
                                workbook.sha256, config["dataset_version"])
    # Two actual ingestions are verified by reproduce; don't freeze a first-run/no-op flag.
    write_json(PROJECT_ROOT / "reports/database_reconciliation.json",
               {key: value for key, value in report.items() if key != "idempotent_noop"}, frozen=True)
    return report


def features(config):
    workbook, validated = source_records(config, "feature-export consistency")
    with connect_database() as connection:
        reconciliation = reconcile(connection, workbook.sha256)
        verify_persisted_records(connection, workbook.records, validated, workbook.sha256)
        exported = export_features(connection, workbook.sha256)
        verify_feature_export(validated.accepted, exported)
        audit_cursor = connection.execute("""
            SELECT client_id, sex, age, education, marriage,
                   sex_group, education_group, marriage_group
            FROM curated.audit_attributes WHERE source_sha256 = %s ORDER BY client_id
        """, (workbook.sha256,))
        audit = [dict(zip([column.name for column in audit_cursor.description], row, strict=True))
                 for row in audit_cursor.fetchall()]
    output = project_path(config["processed_dir"])
    write_csv(output / "financial_features_v1.csv", exported, ("client_id", *PREDICTORS), frozen=True)
    labels = [{"client_id": row["client_id"], "default_next_month": row["default_next_month"]}
              for row in sorted(validated.accepted, key=lambda row: row["client_id"])]
    write_csv(output / "labels.csv", labels, ("client_id", "default_next_month"), frozen=True)
    write_csv(output / "audit_attributes.csv", audit,
              ("client_id", *AUDIT_COLUMNS, "sex_group", "education_group", "marriage_group"), frozen=True)
    rejected = json.dumps(validated.rejected, sort_keys=True, default=str, allow_nan=True, indent=2) + "\n"
    # Quarantine stays ignored and retains original invalid values/reasons.
    atomic_write(PROJECT_ROOT / "data/quarantine/rejected.json", rejected.encode(), frozen=True)
    write_json(project_path(config["feature_contract"]), feature_contract(), frozen=True)
    state = {**stage_metadata(config, workbook.sha256), **reconciliation,
             "financial_export_sha256": file_sha256(output / "financial_features_v1.csv"),
             "label_export_sha256": file_sha256(output / "labels.csv"),
             "audit_export_sha256": file_sha256(output / "audit_attributes.csv"),
             "sql_python_all_rows_agree": True}
    write_run_evidence(PROJECT_ROOT / "artifacts/phase1_export_manifest.json", state)
    return reconciliation


def freeze_splits(config, records, source_sha256, evidence_scope="canonical-xlrd"):
    """Freeze from validated source. Inspection-only evidence stays explicitly qualified."""
    manifest_path = project_path(config["split_manifest"])
    if manifest_path.exists():
        rows = read_csv(manifest_path)
        summary = validate_manifest(records, rows, source_sha256, seed=config["seed"])
    else:
        rows, summary = allocate_records(records, source_sha256, seed=config["seed"])
        write_csv(manifest_path, rows,
                  ("client_id", "partition", "fold", "fingerprint", "seed", "source_sha256"),
                  frozen=True)
    summary = {**summary, "source_reader_evidence": evidence_scope,
               "manifest_file_sha256": file_sha256(manifest_path),
               "feature_contract_sha256": sha256_bytes(json_bytes(feature_contract()))}
    summary_path = project_path(config["split_summary"])
    if summary_path.exists():
        prior = json.loads(summary_path.read_text())
        # A later canonical reader may confirm the same assignments; never relabel
        # the original reader evidence silently or regenerate a more favorable split.
        if prior.get("manifest_file_sha256") != summary["manifest_file_sha256"]:
            raise ValueError("Split summary disagrees with the frozen manifest")
        current = {key: value for key, value in summary.items()
                   if key not in {"source_reader_evidence", "feature_contract_sha256"}}
        prior_stable = {key: value for key, value in prior.items()
                        if key not in {"source_reader_evidence", "feature_contract_sha256"}}
        if current != prior_stable:
            raise ValueError("Frozen split summary no longer matches validated assignments")
        summary = prior
    else:
        write_json(summary_path, summary, frozen=True)
    receipt = {"manifest_file_sha256": summary["manifest_file_sha256"],
               "source_sha256": source_sha256, "dataset_version": config.get("dataset_version"),
               "feature_contract_sha256": sha256_bytes(json_bytes(feature_contract())),
               "source_reader_evidence": evidence_scope, "integrity": summary["integrity"]}
    receipt_hash = sha256_bytes(json_bytes(receipt))
    write_json(manifest_path.parent / "split_checks" / f"{receipt_hash}.json", receipt, frozen=True)
    return summary


def split(config):
    workbook, validated = source_records(config, "stratified split creation/validation")
    summary = freeze_splits(config, validated.accepted, workbook.sha256)
    return summary


def development_report(records, manifest_rows, source_sha256):
    """Filter to frozen development IDs before calculating any distribution or outcome count."""
    validate_manifest(records, manifest_rows, source_sha256)
    development_ids = {int(row["client_id"]) for row in manifest_rows if row["partition"] == "development"}
    development = [row for row in records if row["client_id"] in development_ids]
    feature_rows = [build_features(row) for row in development]
    default_count = sum(row["default_next_month"] for row in development)
    descriptions = {}
    for column in PREDICTORS:
        values = [row[column] for row in feature_rows if row[column] is not None]
        descriptions[column] = {"observed": len(values), "missing": len(development) - len(values),
                                "minimum": min(values) if values else None,
                                "median": statistics.median(values) if values else None,
                                "mean": statistics.fmean(values) if values else None,
                                "maximum": max(values) if values else None}
    categories = {column: {} for column in RAW_PREDICTORS if column.startswith("pay_status_")}
    for row in development:
        for column in categories:
            key = "missing" if row[column] is None else str(row[column])
            categories[column][key] = categories[column].get(key, 0) + 1
    return {"scope": "development only", "source_sha256": source_sha256,
            "development_rows": len(development), "development_defaults": default_count,
            "development_default_prevalence": default_count / len(development),
            "descriptive_financial_features": descriptions,
            "development_repayment_category_counts": categories,
            "learned_preprocessing": "none; descriptive summaries are not exported as fitted transforms"}


def eda(config):
    workbook, validated = source_records(config, "development EDA source-integrity verification")
    manifest_path = project_path(config["split_manifest"])
    if not manifest_path.exists():
        raise ValueError("Freeze and validate splits before development EDA")
    rows = read_csv(manifest_path)
    report = development_report(validated.accepted, rows, workbook.sha256)
    report.update(stage_metadata(config, workbook.sha256))
    report.update({"split_manifest_sha256": file_sha256(manifest_path), "feature_version": FEATURE_VERSION})
    write_run_evidence(PROJECT_ROOT / "reports/development_eda.json", report)
    text = ("# Development data inspection\n\n"
            f"Only the {report['development_rows']:,} frozen development rows are summarized. "
            f"Development default prevalence: {report['development_default_prevalence']:.4%}. "
            "See development_eda.json for measured feature summaries. Missing ratios remain "
            "missing and signed balances remain signed. No distribution cutoff or category "
            "vocabulary was learned for preprocessing. Repayment codes are categories; "
            "negative/zero special-code meanings are not inferred. The data support a "
            "historical existing-account snapshot study, with no chronological or external "
            "validation claim. No predictive model has been fit.\n")
    atomic_write(PROJECT_ROOT / "reports/development_eda.md", text.encode(), frozen=True)
    return {"scope": report["scope"], "development_rows": report["development_rows"]}


def reproduce(config):
    validation = validate(config)
    first = ingest(config)
    second = ingest(config)
    if not second["idempotent_noop"]:
        raise ValueError("Second ingestion did not verify idempotency")
    exported = features(config)
    partitions = split(config)
    development = eda(config)
    result = {"validation": validation, "database": exported,
              "second_ingestion_noop": second["idempotent_noop"],
              "first_ingestion_noop": first["idempotent_noop"],
              "split_manifest_sha256": partitions["manifest_file_sha256"],
              "development_report": development, "predictive_training": "not run"}
    write_json(PROJECT_ROOT / "reports/phase1_run.json", result)
    return result
