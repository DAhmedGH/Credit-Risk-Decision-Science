"""Read versioned project settings and ignored local service credentials."""

import os
from pathlib import Path
import tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(path="configs/base.toml"):
    path = Path(path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    config = tomllib.loads(path.read_text())
    required = {"dataset_version", "workbook", "provenance", "processed_dir", "split_manifest",
                "split_summary", "feature_contract", "seed"}
    if set(config) != required or config["seed"] != 42:
        raise ValueError("Config schema changed or seed differs from the frozen Phase 1 contract")
    return config


def project_path(value):
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def database_settings():
    path = PROJECT_ROOT / ".env"
    values = {}
    if path.exists():
        values = dict(line.split("=", 1) for line in path.read_text().splitlines()
                      if line.strip() and not line.lstrip().startswith("#"))
    for key in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST_PORT"):
        if key in os.environ:
            values[key] = os.environ[key]
    if values.get("POSTGRES_DB", "credit_risk_dev") != "credit_risk_dev":
        raise ValueError("Only the dedicated credit_risk_dev database is supported")
    if values.get("POSTGRES_USER", "credit_risk_app") != "credit_risk_app":
        raise ValueError("Only the dedicated credit_risk_app database role is supported")
    password = values.get("POSTGRES_PASSWORD", "")
    if not password or password.startswith("REPLACE_"):
        raise ValueError("Start the local database with python3 scripts/dev_db.py up first")
    port = int(values.get("POSTGRES_HOST_PORT", 55432))
    if not 1024 <= port <= 65535:
        raise ValueError("Invalid local PostgreSQL host port")
    return {"host": "127.0.0.1", "port": port, "dbname": "credit_risk_dev",
            "user": "credit_risk_app", "password": password, "connect_timeout": 5,
            "application_name": "credit-risk-phase1"}
