"""Versioned UCI 350 training-record contract; no population-fitted transforms."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from numbers import Real
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "uci350-v1.1"
MONTHS = tuple(f"2005_{month:02d}" for month in range(4, 10))
SOURCE_COLUMNS = (
    "ID", "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
    "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
    "BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6",
    "PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6",
    "default payment next month",
)
NORMALIZED_COLUMNS = (
    "client_id", "limit_bal", "sex", "education", "marriage", "age",
    *(f"pay_status_{month}" for month in reversed(MONTHS)),
    *(f"bill_amt_{month}" for month in reversed(MONTHS)),
    *(f"pay_amt_{month}" for month in reversed(MONTHS)),
    "default_next_month",
)
SOURCE_TO_NORMALIZED = dict(zip(SOURCE_COLUMNS, NORMALIZED_COLUMNS, strict=True))
RAW_PREDICTORS = (
    "limit_bal",
    *(f"pay_status_{month}" for month in MONTHS),
    *(f"bill_amt_{month}" for month in MONTHS),
    *(f"pay_amt_{month}" for month in MONTHS),
)
AUDIT_COLUMNS = ("sex", "age", "education", "marriage")
STATUS_COLUMNS = tuple(f"pay_status_{month}" for month in MONTHS)
BILL_COLUMNS = tuple(f"bill_amt_{month}" for month in MONTHS)
PAYMENT_COLUMNS = tuple(f"pay_amt_{month}" for month in MONTHS)
REPAYMENT_CODES = frozenset(range(-2, 10))
POSTGRES_BIGINT_MAX = 2**63 - 1
POSTGRES_INTEGER_MIN = -(2**31)
POSTGRES_INTEGER_MAX = 2**31 - 1
DOCUMENTED_DEMOGRAPHIC_CODES = {
    "sex": frozenset((1, 2)),
    "education": frozenset((1, 2, 3, 4)),
    "marriage": frozenset((1, 2, 3)),
}


class DataContractError(ValueError):
    """Structural failure that prevents trustworthy row reconciliation."""


@dataclass(frozen=True)
class ValidationResult:
    accepted: list[dict[str, int | float | None]]
    rejected: list[dict[str, Any]]
    summary: dict[str, Any]


def _numeric(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _finite(value: Any) -> bool:
    if not _numeric(value):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _integer(value: Any) -> bool:
    return _finite(value) and int(value) == value


def audit_group(column: str, value: Any) -> str:
    """Keep raw audit codes; group undocumented demographic values as unknown."""
    groups = {
        "sex": {1: "male", 2: "female"},
        "education": {1: "graduate_school", 2: "university", 3: "high_school", 4: "other"},
        "marriage": {1: "married", 2: "single", 3: "other"},
    }
    if column not in groups:
        raise ValueError(f"No categorical audit grouping is defined for {column!r}")
    return groups[column].get(value, "unknown")


def validate_records(records: Iterable[Mapping[str, Any]]) -> ValidationResult:
    """Validate without computing label distributions or learning cleaning rules.

    Schema/identifier failures abort ingestion. Other invalid rows are quarantined.
    Missing financial histories remain missing for later fold-fitted imputation;
    credit limits and training labels are mandatory. Signed monetary values and
    special repayment codes are preserved. Undocumented integer demographic
    codes remain available for auditing and are grouped as ``unknown``.
    """
    rows = list(records)
    expected = set(NORMALIZED_COLUMNS)
    seen_ids: set[int] = set()
    for index, row in enumerate(rows):
        if set(row) != expected:
            missing, extra = expected - set(row), set(row) - expected
            raise DataContractError(
                f"Record {index}: schema mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
            )
        identifier = row["client_id"]
        if not _integer(identifier) or not 0 < identifier <= POSTGRES_BIGINT_MAX:
            raise DataContractError(f"Record {index}: client_id must fit a non-null positive PostgreSQL bigint")
        identifier = int(identifier)
        if identifier in seen_ids:
            raise DataContractError(f"Record {index}: duplicate client_id {identifier}")
        seen_ids.add(identifier)

    accepted: list[dict[str, int | float | None]] = []
    rejected: list[dict[str, Any]] = []
    reasons_count: Counter[str] = Counter()
    missing_counts: Counter[str] = Counter()
    inventory: dict[str, Counter[str]] = {
        column: Counter() for column in (*DOCUMENTED_DEMOGRAPHIC_CODES, *STATUS_COLUMNS)
    }
    unknown_demographics: Counter[str] = Counter()
    for index, row in enumerate(rows):
        reasons: list[str] = []
        normalized: dict[str, int | float | None] = {}
        for column in NORMALIZED_COLUMNS:
            value = row[column]
            if value is None:
                normalized[column] = None
                if column not in ("client_id", "default_next_month"):
                    missing_counts[column] += 1
                if column in ("limit_bal", "default_next_month"):
                    reasons.append(f"{column}:required")
                continue
            if not _numeric(value):
                reasons.append(f"{column}:non_numeric")
                continue
            if not _finite(value):
                reasons.append(f"{column}:non_finite")
                continue
            normalized[column] = int(value) if _integer(value) else float(value)
            if column in (*STATUS_COLUMNS, *AUDIT_COLUMNS, "default_next_month"):
                if not _integer(value):
                    reasons.append(f"{column}:non_integer")
                    continue
            if column in AUDIT_COLUMNS and not POSTGRES_INTEGER_MIN <= value <= POSTGRES_INTEGER_MAX:
                reasons.append(f"{column}:integer_storage_range")
            if column == "limit_bal" and value <= 0:
                reasons.append("limit_bal:non_positive")
            elif column == "default_next_month" and value not in (0, 1):
                reasons.append("default_next_month:not_binary")
            elif column in STATUS_COLUMNS and value not in REPAYMENT_CODES:
                reasons.append(f"{column}:unsupported_code")
            elif column == "age" and value <= 0:
                reasons.append("age:non_positive")
            if column in inventory:
                inventory[column][str(int(value))] += 1
            if column in DOCUMENTED_DEMOGRAPHIC_CODES:
                if value not in DOCUMENTED_DEMOGRAPHIC_CODES[column]:
                    unknown_demographics[column] += 1
        if not reasons:
            # A fixed row-level representation rule, never a population cutoff.
            from credit_risk.features import build_features

            try:
                build_features(normalized)
            except (ArithmeticError, ValueError):
                reasons.append("engineered_features:arithmetic_range")
        if reasons:
            reasons_count.update(reasons)
            rejected.append({
                "record_index": index,
                "client_id": int(row["client_id"]),
                "reasons": reasons,
                "record": dict(row),
            })
        else:
            accepted.append(normalized)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "source_rows": len(rows),
        "accepted_rows": len(accepted),
        "rejected_rows": len(rejected),
        "counts_reconcile": len(rows) == len(accepted) + len(rejected),
        "identifiers_unique_and_non_null": True,
        "accepted_targets_binary_and_non_null": True,
        "rejection_reason_counts": dict(sorted(reasons_count.items())),
        "missing_by_column": dict(sorted(missing_counts.items())),
        "category_code_inventory": {
            column: dict(sorted(counts.items())) for column, counts in inventory.items()
        },
        "unknown_demographic_code_counts": dict(sorted(unknown_demographics.items())),
        "inventory_scope": "source integrity only; target distributions are never computed",
    }
    return ValidationResult(accepted, rejected, summary)
