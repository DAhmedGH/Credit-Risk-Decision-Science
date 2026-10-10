"""Frozen, target-stratified allocation of exact financial-profile groups."""

from .allocation import (
    FINGERPRINT_VERSION,
    MANIFEST_COLUMNS,
    SPLIT_VERSION,
    allocate_records,
    financial_fingerprint,
    validate_manifest,
)

__all__ = [
    "FINGERPRINT_VERSION",
    "MANIFEST_COLUMNS",
    "SPLIT_VERSION",
    "allocate_records",
    "financial_fingerprint",
    "validate_manifest",
]
