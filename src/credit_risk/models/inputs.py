"""Verify frozen inputs and select development IDs before interpreting outcomes.

This module has no modeling dependencies, never decodes the workbook, and never
opens the audit export. Full-file hashes are byte-integrity checks only.
"""

import csv
import json
import math
from pathlib import Path

from credit_risk.artifacts import file_sha256
from credit_risk.features import PREDICTORS, feature_contract
from credit_risk.splits.allocation import financial_fingerprint


def verify_assignments(rows, source_hash):
    """Check assignment structure and groups without any outcomes or allocation."""
    expected = {"client_id", "partition", "fold", "fingerprint", "seed", "source_sha256"}
    destinations, seen, development = {}, set(), []
    partitions = {"development", "calibration", "policy_validation", "final_test"}
    present = set()
    for row in rows:
        if set(row) != expected:
            raise ValueError("Frozen assignment columns changed")
        identifier = int(row["client_id"])
        if identifier <= 0 or identifier in seen:
            raise ValueError("Frozen IDs must be unique and positive")
        seen.add(identifier)
        partition = row["partition"]
        if partition not in partitions or str(row["seed"]) != "42":
            raise ValueError("Frozen partition/seed contract changed")
        present.add(partition)
        if row["source_sha256"] != source_hash:
            raise ValueError("Frozen source hash changed")
        fingerprint = row["fingerprint"]
        if len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint):
            raise ValueError("Invalid frozen fingerprint")
        fold = "" if row["fold"] is None else str(row["fold"])
        if partition == "development":
            if fold not in {"0", "1", "2", "3", "4"}:
                raise ValueError("Expected five frozen development folds")
            development.append({**row, "client_id": identifier, "fold": int(fold)})
        elif fold != "":
            raise ValueError("Held-out assignments must not have development folds")
        destination = (partition, fold)
        if fingerprint in destinations and destinations[fingerprint] != destination:
            raise ValueError("Fingerprint group crosses a partition or fold")
        destinations[fingerprint] = destination
    if present != partitions or {row["fold"] for row in development} != set(range(5)):
        raise ValueError("Missing partition or development fold")
    return sorted(development, key=lambda row: row["client_id"])


def _selected_csv(path, expected_columns, selected_ids, convert):
    selected, seen = {}, set()
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(expected_columns):
            raise ValueError(f"Export columns/order changed: {Path(path).name}")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed export record")
            identifier = int(row["client_id"])
            if identifier <= 0 or identifier in seen:
                raise ValueError("Export IDs must be unique and positive")
            seen.add(identifier)
            # Held-out outcome/feature strings are not converted or inspected.
            if identifier in selected_ids:
                selected[identifier] = convert(row)
    if set(selected) != selected_ids:
        raise ValueError("Development export coverage differs from frozen IDs")
    return selected, seen


def select_development(features_path, labels_path, assignments, source_hash):
    """Return ordered row records, labels and folds; ignore held-out values."""
    development = verify_assignments(assignments, source_hash)
    identifiers = {row["client_id"] for row in development}

    def feature_values(row):
        values = {column: float(row[column]) if row[column] != "" else None
                  for column in PREDICTORS}
        if any(value is not None and not math.isfinite(value) for value in values.values()):
            raise ValueError("Non-finite development predictor")
        return values

    def label_value(row):
        if row["default_next_month"] not in {"0", "1"}:
            raise ValueError("Development outcomes must be binary/non-null")
        return int(row["default_next_month"])

    features, feature_ids = _selected_csv(
        features_path, ("client_id", *PREDICTORS), identifiers, feature_values)
    labels, label_ids = _selected_csv(
        labels_path, ("client_id", "default_next_month"), identifiers, label_value)
    all_ids = {int(row["client_id"]) for row in assignments}
    if feature_ids != all_ids or label_ids != all_ids:
        raise ValueError("Export IDs differ from complete frozen assignment")
    records = []
    for row in development:
        identifier = row["client_id"]
        if financial_fingerprint(features[identifier]) != row["fingerprint"]:
            raise ValueError("Development financial profile differs from frozen fingerprint")
        records.append({"client_id": identifier, "fold": row["fold"],
                        "fingerprint": row["fingerprint"],
                        "default_next_month": labels[identifier], **features[identifier]})
    for fold in range(5):
        for is_validation in (True, False):
            if {row["default_next_month"] for row in records
                    if (row["fold"] == fold) == is_validation} != {0, 1}:
                raise ValueError("Each development fit/validation fold requires both classes")
    return records


def load_development(base, export_path, receipt_path, root):
    """Bind current bytes to canonical Phase 1 evidence, then select development."""
    root = Path(root)
    export_path, receipt_path = root / export_path, root / receipt_path
    export = json.loads(export_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    if file_sha256(receipt_path) != receipt_path.stem:
        raise ValueError("Content-addressed frozen split receipt changed")
    source = json.loads((root / base["provenance"]).read_text())
    source_hash = source["workbook"]["sha256"]
    expected = {
        base["workbook"]: source_hash,
        base["split_manifest"]: receipt["manifest_file_sha256"],
        base["feature_contract"]: export["feature_contract_sha256"],
        str(Path(base["processed_dir"]) / "financial_features_v1.csv"):
            export["financial_export_sha256"],
        str(Path(base["processed_dir"]) / "labels.csv"): export["label_export_sha256"],
    }
    for relative, checksum in expected.items():
        if file_sha256(root / relative) != checksum:
            raise ValueError(f"Pinned Phase 1 bytes changed: {relative}")
    contract = json.loads((root / base["feature_contract"]).read_text())
    if contract != feature_contract():
        raise ValueError("Code feature contract differs from frozen contract")
    if (export["source_sha256"] != source_hash or receipt["source_sha256"] != source_hash
            or receipt["feature_contract_sha256"] != export["feature_contract_sha256"]
            or export["dataset_version"] != base["dataset_version"]
            or receipt["dataset_version"] != base["dataset_version"]
            or receipt["source_reader_evidence"] != "canonical-xlrd"
            or not receipt["integrity"] or not all(receipt["integrity"].values())
            or not export["counts_reconcile"] or not export["sql_python_all_rows_agree"]):
        raise ValueError("Canonical Phase 1 evidence disagrees or is incomplete")
    with (root / base["split_manifest"]).open(newline="") as stream:
        assignments = list(csv.DictReader(stream))
    records = select_development(
        root / base["processed_dir"] / "financial_features_v1.csv",
        root / base["processed_dir"] / "labels.csv", assignments, source_hash)
    if len(assignments) != export["exported_rows"]:
        raise ValueError("Phase 1 export row counts disagree")
    hashes = {relative: checksum for relative, checksum in expected.items()}
    hashes[str(export_path.relative_to(root))] = file_sha256(export_path)
    hashes[str(receipt_path.relative_to(root))] = file_sha256(receipt_path)
    return records, hashes


def validate_oof(rows, expected_records):
    """Require exactly one finite prediction for each development ID and fold."""
    expected = {int(row["client_id"]): row for row in expected_records}
    if len(expected) != len(expected_records) or len(rows) != len(expected):
        raise ValueError("OOF prediction coverage is incomplete or duplicated")
    seen = set()
    for row in rows:
        identifier = int(row["client_id"])
        if identifier in seen or identifier not in expected:
            raise ValueError("OOF IDs duplicated or outside development")
        seen.add(identifier)
        original = expected[identifier]
        if (int(row["fold"]) != original["fold"]
                or int(row["default_next_month"]) != original["default_next_month"]
                or row["fingerprint"] != original["fingerprint"]):
            raise ValueError("OOF assignment/outcome differs from development input")
        probability = float(row["p_default"])
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("OOF probabilities must be finite and in [0,1]")
    return True
