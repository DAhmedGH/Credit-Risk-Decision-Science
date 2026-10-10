"""Explicit, versioned row-only financial predictor contract."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from credit_risk.data.schema import (
    BILL_COLUMNS,
    MONTHS,
    PAYMENT_COLUMNS,
    RAW_PREDICTORS,
    SOURCE_TO_NORMALIZED,
    STATUS_COLUMNS,
)

FEATURE_VERSION = "financial-row-v1.1"
ENGINEERED_PREDICTORS = (
    "recent_delinquency_count",
    "maximum_positive_delay",
    "recent_history_delay_contrast",
    "latest_utilization_proxy",
    "mean_utilization_proxy",
    "bill_balance_change",
    "bill_volatility_proxy",
    "mean_payment",
    "zero_payment_count",
    "payment_to_prior_bill_proxy",
    "payment_to_prior_bill_missing",
    "aggregate_payment_balance_proxy",
    "aggregate_payment_balance_missing",
)
PREDICTORS = RAW_PREDICTORS + ENGINEERED_PREDICTORS


def _complete(values: list[Any]) -> bool:
    return all(value is not None for value in values)


def build_features(record: Mapping[str, int | float | None]) -> dict[str, int | float | None]:
    """Return only allowlisted predictors, with no fitted state or imputation.

    Input is a validated normalized row (possibly without ID, label, or audits).
    Missing required columns are a schema error. Raw missingness propagates into
    dependent formulas; only nonpositive positive-delay values become zero for
    the explicitly defined delay summaries, never in the raw categorical inputs.
    """
    missing = set(RAW_PREDICTORS) - set(record)
    if missing:
        raise ValueError(f"Missing raw financial columns: {sorted(missing)}")
    result = {column: record[column] for column in RAW_PREDICTORS}
    limit = record["limit_bal"]
    if limit is not None and (not math.isfinite(limit) or limit <= 0):
        raise ValueError("Credit limit must be finite and positive when provided")
    status = [record[column] for column in STATUS_COLUMNS]
    bills = [record[column] for column in BILL_COLUMNS]
    payments = [record[column] for column in PAYMENT_COLUMNS]
    derived: dict[str, int | float | None] = dict.fromkeys(ENGINEERED_PREDICTORS)
    if _complete(status):
        positive_delays = [max(value, 0) for value in status]
        derived["recent_delinquency_count"] = sum(value > 0 for value in status)
        derived["maximum_positive_delay"] = max(positive_delays)
        derived["recent_history_delay_contrast"] = (
            sum(positive_delays[3:]) / 3 - sum(positive_delays[:3]) / 3
        )
    if limit is not None:
        if bills[-1] is not None:
            derived["latest_utilization_proxy"] = bills[-1] / limit
        if _complete(bills):
            mean_bill = sum(bills) / 6
            derived["mean_utilization_proxy"] = mean_bill / limit
            derived["bill_balance_change"] = (bills[-1] - bills[0]) / limit
            derived["bill_volatility_proxy"] = math.sqrt(
                sum((value - mean_bill) ** 2 for value in bills) / 6
            ) / limit
        elif bills[0] is not None and bills[-1] is not None:
            derived["bill_balance_change"] = (bills[-1] - bills[0]) / limit
    if _complete(payments):
        derived["mean_payment"] = sum(payments) / 6
        derived["zero_payment_count"] = sum(value == 0 for value in payments)
    prior_bill, latest_payment = bills[-2], payments[-1]
    if prior_bill is not None and prior_bill > 0 and latest_payment is not None:
        derived["payment_to_prior_bill_proxy"] = latest_payment / prior_bill
    derived["payment_to_prior_bill_missing"] = int(
        derived["payment_to_prior_bill_proxy"] is None
    )
    if _complete(bills) and _complete(payments):
        positive_bill_total = sum(max(value, 0) for value in bills)
        if positive_bill_total > 0:
            derived["aggregate_payment_balance_proxy"] = sum(payments) / positive_bill_total
    derived["aggregate_payment_balance_missing"] = int(
        derived["aggregate_payment_balance_proxy"] is None
    )
    result.update(derived)
    if any(value is not None and not math.isfinite(value) for value in result.values()):
        raise ValueError("Feature arithmetic exceeds the finite representation supported by v1")
    return result


def feature_contract() -> dict[str, Any]:
    """JSON-serializable definitions independent of a dataset or fitted model."""
    formulas = {
        "recent_delinquency_count": (STATUS_COLUMNS, "count(status > 0), April-September"),
        "maximum_positive_delay": (STATUS_COLUMNS, "max(max(status, 0)), April-September"),
        "recent_history_delay_contrast": (
            STATUS_COLUMNS, "mean(max(status, 0)), July-September minus April-June"
        ),
        "latest_utilization_proxy": ((BILL_COLUMNS[-1], "limit_bal"), "September bill / credit limit"),
        "mean_utilization_proxy": ((*BILL_COLUMNS, "limit_bal"), "mean(six bills) / credit limit"),
        "bill_balance_change": (
            (BILL_COLUMNS[0], BILL_COLUMNS[-1], "limit_bal"), "(September bill - April bill) / credit limit"
        ),
        "bill_volatility_proxy": (
            (*BILL_COLUMNS, "limit_bal"), "population SD(six bills) / credit limit"
        ),
        "mean_payment": (PAYMENT_COLUMNS, "mean(six payments) in source monetary units"),
        "zero_payment_count": (PAYMENT_COLUMNS, "count(payment == 0), April-September"),
        "payment_to_prior_bill_proxy": (
            (PAYMENT_COLUMNS[-1], BILL_COLUMNS[-2]),
            "September payment / August bill if bill > 0; otherwise missing",
        ),
        "payment_to_prior_bill_missing": (
            (PAYMENT_COLUMNS[-1], BILL_COLUMNS[-2]), "1 when payment_to_prior_bill_proxy is missing, else 0"
        ),
        "aggregate_payment_balance_proxy": (
            (*PAYMENT_COLUMNS, *BILL_COLUMNS),
            "sum(six payments) / sum(max(bill, 0)); missing if denominator = 0",
        ),
        "aggregate_payment_balance_missing": (
            (*PAYMENT_COLUMNS, *BILL_COLUMNS), "1 when aggregate_payment_balance_proxy is missing, else 0"
        ),
    }
    reverse = {normalized: source for source, normalized in SOURCE_TO_NORMALIZED.items()}
    return {
        "feature_version": FEATURE_VERSION,
        "months_oldest_to_latest": list(MONTHS),
        "raw_predictors": list(RAW_PREDICTORS),
        "engineered_predictors": list(ENGINEERED_PREDICTORS),
        "predictors": list(PREDICTORS),
        "categorical_predictors": list(STATUS_COLUMNS),
        "excluded": ["client_id", "default_next_month", "sex", "age", "education", "marriage"],
        "raw_source_mapping": {column: reverse[column] for column in RAW_PREDICTORS},
        "derived": {
            name: {"source_dependencies": list(dependencies), "formula": formula, "fit_scope": "row-only"}
            for name, (dependencies, formula) in formulas.items()
        },
        "missingness_rule": "Any missing required input propagates; no population statistics or imputation",
        "arithmetic_range_rule": "Quarantine rows whose v1 formulas overflow or produce non-finite values; no learned magnitude cutoff",
        "availability": "All released September fields available at existing-account month-end snapshot (assumption)",
        "ratio_interpretation": "Payment/balance ratios are proxies, not contractual repayment or debt-to-income",
        "learned_preprocessing": "Fit imputation, scaling, category vocabularies and cutoffs only on relevant training rows",
    }
