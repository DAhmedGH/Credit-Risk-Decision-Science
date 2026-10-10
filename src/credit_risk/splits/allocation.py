"""Allocate whole financial profiles without learning predictor transforms.

The declared algorithm is a deterministic greedy minimization of normalized
squared row-count and binary-class-count deviations. Larger/rarer groups are
placed first. A seed-derived SHA-256 key breaks ties. A feasibility guard
reserves enough groups carrying each class for all partitions and all five
development folds. Both labels of a mixed-label group contribute to the
objective; a group is never represented by a majority label or separated.

Labels are read only for stratification and structural two-class checks.
Returned summaries deliberately omit held-out class counts and prevalence.
This is a fixed allocation rule, not a search across seeds or allocations.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from numbers import Integral, Real
from typing import Any

FINGERPRINT_VERSION = "financial-profile-v1"
SPLIT_VERSION = "stratified-group-greedy-v1"
PARTITION_FRACTIONS = {
    "development": 0.60,
    "calibration": 0.15,
    "policy_validation": 0.10,
    "final_test": 0.15,
}
MANIFEST_COLUMNS = (
    "client_id",
    "partition",
    "fold",
    "fingerprint",
    "seed",
    "source_sha256",
)
_FORBIDDEN_PREDICTORS = frozenset(
    {
        "id",
        "client_id",
        "target",
        "default_next_month",
        "default payment next month",
        "sex",
        "age",
        "education",
        "marriage",
        "marital_status",
    }
)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _columns(predictor_columns: Sequence[str] | None) -> tuple[str, ...]:
    if predictor_columns is None:
        from credit_risk.data.schema import RAW_PREDICTORS

        predictor_columns = RAW_PREDICTORS
    columns = tuple(predictor_columns)
    if not columns or len(set(columns)) != len(columns):
        raise ValueError("Fingerprint columns must be nonempty and unique")
    if any(
        not isinstance(column, str)
        or column.lower() in _FORBIDDEN_PREDICTORS
        for column in columns
    ):
        raise ValueError("Fingerprint columns must exclude identifiers, target and audits")
    return columns


def _number(value: Any) -> str | None:
    """Canonical finite numbers; None is distinct from every numeric value."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
        raise ValueError("Financial fingerprint values must be numeric or None")
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("Financial fingerprint values must be numeric") from error
    if not number.is_finite():
        raise ValueError("Financial fingerprint values must be finite")
    if number == 0:
        return "0"
    rendered = format(number, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def financial_fingerprint(
    record: Mapping[str, Any], predictor_columns: Sequence[str] | None = None
) -> str:
    """Hash the versioned raw-financial schema and row values, never its label.

    Integer/float/Decimal equivalents and signed zero share a profile. Missing
    values retain an explicit null marker. Missing *columns* fail the contract.
    Learned imputation, clipping and category fitting do not occur here.
    """
    columns = _columns(predictor_columns)
    try:
        values = [[column, _number(record[column])] for column in columns]
    except KeyError as error:
        raise ValueError(f"Missing financial predictor: {error.args[0]}") from error
    return hashlib.sha256(_json_bytes([FINGERPRINT_VERSION, values])).hexdigest()


def _integer(value: Any, field: str, *, from_csv: bool = False) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    if isinstance(value, Integral):
        return int(value)
    if from_csv and isinstance(value, str) and re.fullmatch(r"-?\d+", value):
        return int(value)
    raise ValueError(f"{field} must be an integer")


def _source_hash(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("source_sha256 must be a lowercase SHA-256 hexadecimal digest")
    return value


@dataclass(frozen=True)
class _Group:
    fingerprint: str
    ids: tuple[int, ...]
    zeros: int
    ones: int

    @property
    def size(self) -> int:
        return len(self.ids)

    @property
    def kind(self) -> str:
        return "mixed" if self.zeros and self.ones else "zero" if self.zeros else "one"


def _prepare(
    records: Iterable[Mapping[str, Any]], columns: tuple[str, ...]
) -> tuple[dict[int, Mapping[str, Any]], list[_Group]]:
    by_id: dict[int, Mapping[str, Any]] = {}
    group_ids: dict[str, list[int]] = defaultdict(list)
    group_labels: dict[str, Counter[int]] = defaultdict(Counter)
    for record in records:
        try:
            client_id = _integer(record["client_id"], "client_id")
            target = _integer(record["default_next_month"], "default_next_month")
        except KeyError as error:
            raise ValueError(f"Missing required field: {error.args[0]}") from error
        if client_id <= 0 or client_id in by_id:
            raise ValueError("client_id values must be positive and unique")
        if target not in (0, 1):
            raise ValueError("default_next_month must be binary 0/1")
        fingerprint = financial_fingerprint(record, columns)
        by_id[client_id] = record
        group_ids[fingerprint].append(client_id)
        group_labels[fingerprint][target] += 1
    if not by_id:
        raise ValueError("Cannot allocate an empty dataset")
    groups = [
        _Group(
            fingerprint,
            tuple(sorted(group_ids[fingerprint])),
            group_labels[fingerprint][0],
            group_labels[fingerprint][1],
        )
        for fingerprint in sorted(group_ids)
    ]
    return by_id, groups


def _tie_key(seed: int, namespace: str, *parts: Any) -> str:
    return hashlib.sha256(_json_bytes([SPLIT_VERSION, seed, namespace, *parts])).hexdigest()


def _can_fill(
    assigned_carriers: list[list[int]], requirements: Sequence[int], remaining: Counter[str]
) -> bool:
    """Check exact feasibility of missing class-carrier quotas.

    Each remaining group carries class 0, class 1, or both. A mixed group may
    cover one missing quota of each class in the same destination. Enumerating
    how many mixed groups perform that double duty gives a small exact check.
    """
    missing = [
        [max(0, requirement - counts[0]), max(0, requirement - counts[1])]
        for counts, requirement in zip(assigned_carriers, requirements, strict=True)
    ]
    zero_demand = sum(counts[0] for counts in missing)
    one_demand = sum(counts[1] for counts in missing)
    double_capacity = sum(min(counts) for counts in missing)
    for doubles in range(min(double_capacity, remaining["mixed"]) + 1):
        mixed_needed = (
            doubles
            + max(0, zero_demand - doubles - remaining["zero"])
            + max(0, one_demand - doubles - remaining["one"])
        )
        if mixed_needed <= remaining["mixed"]:
            return True
    return False


def _allocate_groups(
    groups: list[_Group],
    names: Sequence[str],
    fractions: Sequence[float],
    requirements: Sequence[int],
    seed: int,
    namespace: str,
) -> dict[str, str]:
    totals = [sum(group.size for group in groups)]
    totals.extend(sum(getattr(group, attr) for group in groups) for attr in ("zeros", "ones"))
    remaining = Counter(group.kind for group in groups)
    carriers = [[0, 0] for _ in names]
    if not all(totals) or not _can_fill(carriers, requirements, remaining):
        raise ValueError(
            "Insufficient distinct financial-profile groups carrying both classes "
            "for four two-class partitions and five two-class development folds"
        )
    counts = [[0, 0, 0] for _ in names]
    ordered = sorted(
        groups,
        key=lambda group: (
            -max(group.zeros / totals[1], group.ones / totals[2]),
            -group.size,
            _tie_key(seed, namespace, "group", group.fingerprint),
        ),
    )
    allocation: dict[str, str] = {}
    for group in ordered:
        remaining[group.kind] -= 1
        increments = (group.size, group.zeros, group.ones)
        carrier_increments = (int(group.zeros > 0), int(group.ones > 0))
        choices = []
        for index, (name, fraction) in enumerate(zip(names, fractions, strict=True)):
            carriers[index][0] += carrier_increments[0]
            carriers[index][1] += carrier_increments[1]
            feasible = _can_fill(carriers, requirements, remaining)
            carriers[index][0] -= carrier_increments[0]
            carriers[index][1] -= carrier_increments[1]
            if not feasible:
                continue
            delta = sum(
                (2 * (count - total * fraction) * increment + increment * increment)
                / (total * total * fraction)
                for count, total, increment in zip(counts[index], totals, increments, strict=True)
            )
            choices.append(
                (delta, _tie_key(seed, namespace, "destination", group.fingerprint, name), index)
            )
        if not choices:
            raise RuntimeError("Class-carrier reservation failed during group allocation")
        chosen = min(choices)[2]
        allocation[group.fingerprint] = names[chosen]
        for component, increment in enumerate(increments):
            counts[chosen][component] += increment
        for component, increment in enumerate(carrier_increments):
            carriers[chosen][component] += increment
    return allocation


def _summarize(
    records_by_id: Mapping[int, Mapping[str, Any]],
    groups: list[_Group],
    manifest: list[dict[str, Any]],
    source_sha256: str,
    seed: int,
    columns: tuple[str, ...],
) -> dict[str, Any]:
    """Structural evidence only: never emit held-out target frequencies."""
    assignments = {row["client_id"]: row for row in manifest}
    fingerprints_by_partition: dict[str, set[str]] = defaultdict(set)
    fingerprints_by_fold: dict[int, set[str]] = defaultdict(set)
    partition_labels: dict[str, set[int]] = defaultdict(set)
    fold_labels: dict[int, set[int]] = defaultdict(set)
    partition_rows: Counter[str] = Counter()
    fold_rows: Counter[int] = Counter()
    for client_id, row in assignments.items():
        partition_rows[row["partition"]] += 1
        fingerprints_by_partition[row["partition"]].add(row["fingerprint"])
        label = int(records_by_id[client_id]["default_next_month"])
        partition_labels[row["partition"]].add(label)
        if row["partition"] == "development":
            fold_rows[row["fold"]] += 1
            fingerprints_by_fold[row["fold"]].add(row["fingerprint"])
            fold_labels[row["fold"]].add(label)
    partition_disjoint = all(
        len({assignments[client_id]["partition"] for client_id in group.ids}) == 1
        for group in groups
    )
    fold_disjoint = all(
        len({assignments[client_id]["fold"] for client_id in group.ids}) == 1
        for group in groups
    )
    integrity = {
        "complete_unique_assignment": len(manifest) == len(records_by_id) == len(assignments)
        and set(assignments) == set(records_by_id),
        "fingerprint_groups_partition_disjoint": partition_disjoint,
        "fingerprint_groups_fold_disjoint": fold_disjoint,
        "nonempty_partitions": all(partition_rows[name] > 0 for name in PARTITION_FRACTIONS),
        "two_classes_in_each_partition": all(
            partition_labels[name] == {0, 1} for name in PARTITION_FRACTIONS
        ),
        "nonempty_development_folds": all(fold_rows[fold] > 0 for fold in range(5)),
        "two_classes_in_each_development_fold": all(
            fold_labels[fold] == {0, 1} for fold in range(5)
        ),
        "folds_only_on_development": all(
            (row["fold"] in range(5) if row["partition"] == "development" else row["fold"] is None)
            for row in manifest
        ),
    }
    if not all(integrity.values()):
        raise ValueError("Partition/fold structural integrity validation failed")
    count = len(records_by_id)
    development_count = partition_rows["development"]
    return {
        "split_version": SPLIT_VERSION,
        "fingerprint_version": FINGERPRINT_VERSION,
        "source_sha256": source_sha256,
        "seed": seed,
        "predictor_columns": list(columns),
        "predictor_schema_sha256": hashlib.sha256(_json_bytes(list(columns))).hexdigest(),
        "assignment_sha256": hashlib.sha256(_json_bytes(manifest)).hexdigest(),
        "row_count": count,
        "group_count": len(groups),
        "largest_profile_group_rows": max(group.size for group in groups),
        "duplicate_profile_groups": sum(group.size > 1 for group in groups),
        "rows_in_duplicate_profile_groups": sum(group.size for group in groups if group.size > 1),
        "partitions": {
            name: {
                "rows": partition_rows[name],
                "groups": len(fingerprints_by_partition[name]),
                "target_fraction": fraction,
                "actual_fraction": partition_rows[name] / count,
                "target_rows": count * fraction,
                "row_deviation": partition_rows[name] - count * fraction,
                "fraction_deviation": partition_rows[name] / count - fraction,
            }
            for name, fraction in PARTITION_FRACTIONS.items()
        },
        "development_folds": {
            str(fold): {
                "rows": fold_rows[fold],
                "groups": len(fingerprints_by_fold[fold]),
                "target_rows": development_count / 5,
                "row_deviation": fold_rows[fold] - development_count / 5,
            }
            for fold in range(5)
        },
        "integrity": integrity,
        "label_access": "stratification and two-class structural checks only",
        "allocation_objective": (
            "Greedy normalized squared row/class-count deviations; larger and rarer "
            "groups first; seed-derived hash ties; class-carrier feasibility guard"
        ),
    }


def allocate_records(
    records: Iterable[Mapping[str, Any]],
    source_sha256: str,
    seed: int = 42,
    predictor_columns: Sequence[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Create fixed 60/15/10/15 partitions and five development folds.

    This function does not write files or inspect outcome distributions.
    Source and predictor schema versions are bound into returned evidence.
    Input record order has no effect. Infeasible two-class inputs fail rather
    than weakening the grouping rule or retrying another random seed.
    """
    source_sha256 = _source_hash(source_sha256)
    seed = _integer(seed, "seed")
    columns = _columns(predictor_columns)
    records_by_id, groups = _prepare(records, columns)
    names = tuple(PARTITION_FRACTIONS)
    partition_assignments = _allocate_groups(
        groups,
        names,
        tuple(PARTITION_FRACTIONS.values()),
        (5, 1, 1, 1),
        seed,
        "partition",
    )
    development_groups = [
        group for group in groups if partition_assignments[group.fingerprint] == "development"
    ]
    fold_assignments = _allocate_groups(
        development_groups,
        tuple(str(fold) for fold in range(5)),
        (0.2,) * 5,
        (1,) * 5,
        seed,
        "development_fold",
    )
    manifest = []
    for group in groups:
        partition = partition_assignments[group.fingerprint]
        fold = int(fold_assignments[group.fingerprint]) if partition == "development" else None
        manifest.extend(
            {
                "client_id": client_id,
                "partition": partition,
                "fold": fold,
                "fingerprint": group.fingerprint,
                "seed": seed,
                "source_sha256": source_sha256,
            }
            for client_id in group.ids
        )
    manifest.sort(key=lambda row: row["client_id"])
    summary = _summarize(records_by_id, groups, manifest, source_sha256, seed, columns)
    return manifest, summary


def validate_manifest(
    records: Iterable[Mapping[str, Any]],
    manifest_rows: Iterable[Mapping[str, Any]],
    source_sha256: str,
    predictor_columns: Sequence[str] | None = None,
    *,
    seed: int = 42,
) -> dict[str, Any]:
    """Reproduce assignments and reject stale, incomplete or altered manifests.

    CSV strings for IDs, fold and seed are accepted, with blank held-out folds.
    Validation also recomputes every financial fingerprint. The source hash
    must come from independently verified original workbook bytes, not from
    the manifest being validated. Outcome access remains stratification only.
    """
    expected, summary = allocate_records(records, source_sha256, seed, predictor_columns)
    normalized = []
    for row in manifest_rows:
        if set(row) != set(MANIFEST_COLUMNS):
            raise ValueError("Manifest columns do not match the frozen schema")
        client_id = _integer(row["client_id"], "manifest client_id", from_csv=True)
        row_seed = _integer(row["seed"], "manifest seed", from_csv=True)
        fold = row["fold"]
        if fold == "" or fold is None:
            fold = None
        else:
            fold = _integer(fold, "manifest fold", from_csv=True)
        normalized.append(
            {
                "client_id": client_id,
                "partition": row["partition"],
                "fold": fold,
                "fingerprint": row["fingerprint"],
                "seed": row_seed,
                "source_sha256": row["source_sha256"],
            }
        )
    normalized.sort(key=lambda row: row["client_id"])
    if normalized != expected:
        raise ValueError(
            "Manifest differs from the fixed allocation: check IDs, financial profiles, "
            "source hash, seed, partition and fold"
        )
    return summary
