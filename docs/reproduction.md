# Reproduce Phase 1

These are historical phase commands, retained for reproducibility. Run them only
in a separate private historical source/payload copy with its original receipts
and dependency checkpoint. The publication source uses the current pinned lock
and the [standalone scoring workflow](reproduction-phase5.md); it does not ship
all historical execution attachments.

This is the historical Phase 1 checkpoint. For the completed project and current
72-pin environment, start with [Phase 5 reproduction](reproduction-phase5.md).
Historical phase state, Git limitations and dependency counts below describe
their original checkpoints, not the current checkout.

This guide records the Phase 1 workflow. Phase 2 is now accepted; its current
58-pin `requirements.lock` supersedes the original 11-pin lock, preserved as
`requirements-phase1.lock`. Statements below about unchanged lock bytes and
future modeling dependencies describe the Phase 1 checkpoint. Use
[Phase 2 reproduction](reproduction-phase2.md) for the current baseline environment.

Do not replay the historical `reproduce` command merely for Phase 2 acceptance.
With the expanded lock, Phase 1 evidence has a changed lock identity and the
overwrite guard can reject writing over the canonical reports. Preserve those
reports; a future replay across dependency checkpoints needs separate versioned
evidence handling. This limitation does not affect the accepted Phase 2 workflow.

The project targets Python 3.12 in Ubuntu/WSL 2. Docker Desktop must be integrated
with that Ubuntu distribution. Use the ordinary WSL terminal: the original execution environment
session used for implementation could not access its network or Docker socket.
Existing user Python installations and unrelated Docker resources are untouched.

## Canonical workflow

```bash
cd '/mnt/c/Users/Danieal/Desktop/Credit Risk Project'
bash scripts/bootstrap.sh
python3 scripts/dev_db.py up
.venv/bin/python -m credit_risk reproduce --config configs/base.toml
.venv/bin/ruff check .
.venv/bin/python -m pytest -q
CREDIT_RISK_SQL_TEST=1 .venv/bin/python -m pytest -q tests/test_database.py
```

`bootstrap.sh` installs pinned uv 0.8.22 into `.tools/bin`, a managed Python 3.12
under `.tools/python`, and dependencies into `.venv`. Its cache is project-local.
It refuses to reuse a `.venv` with a different Python version. It does not edit
shell startup files, system Python, or another project's environment. The exact
Linux/Python-3.12 dependency pins are in `requirements.lock`. At checkpoint all 11
installed pins matched, and the Python 3.12.11 import/feature-serialization smoke
passed with xlrd 2.0.2 and psycopg 3.2.3. The lock's original pending-validation
comment is historical; its bytes remain unchanged for evidence continuity.
No predictive fit is performed by the smoke script. Modeling dependencies are
Phase 2 work.

`dev_db.py up` first checks Docker and ownership of existing project containers
and the named volume. It checks loopback bind availability, starting at 55432
and trying through 55451; it records the selected port in ignored `.env`. No host
port has been declared available in the restricted implementation session. A
random local password is generated without printing it. If `.env` already
exists, settings are validated and reused; an unavailable existing port fails
instead of rewriting credentials or interfering with another service.

The service is `postgres` under Compose project `credit-risk-phase1`, with volume
`credit-risk-phase1-pgdata`, database `credit_risk_dev`, and role
`credit_risk_app`. It binds only `127.0.0.1`. Project and disposable-development
server settings must match before any ingestion DDL/write. Runtime image identity
is recorded in ignored `artifacts/runtime/postgres.json`. The PostgreSQL
`16-bookworm` tag is not a pinned image digest; archive the resolved image ID for
an actual run before claiming identical container inputs.

`reproduce` executes source validation, actual ingestion **twice**, SQL feature
export and Python parity, frozen split validation/creation, then development-only
EDA. It fails on a changed source, incompatible stored ingestion rules, altered
split assignments, or mismatched financial/target/audit/source values. Existing
splits are reproduced, never replaced. It writes canonical evidence to
`reports/source_validation.json`, `reports/database_reconciliation.json`,
`artifacts/phase1_export_manifest.json`, `reports/phase1_run.json`, and
`reports/development_eda.json` only after their relevant checks run. Source and
feature schemas remain versioned. Pure execution-provenance refreshes preserve
the prior report in `history/`; changed scientific dependencies/results require
a new version/path.

Individual commands are available for diagnosis:

```bash
.venv/bin/python -m credit_risk validate --config configs/base.toml
.venv/bin/python -m credit_risk ingest --config configs/base.toml
.venv/bin/python -m credit_risk features --config configs/base.toml
.venv/bin/python -m credit_risk split --config configs/base.toml
.venv/bin/python -m credit_risk eda --config configs/base.toml
```

Training labels, audit attributes, feature CSVs, and quarantined rows stay in
ignored directories. Predictor export has exactly `client_id` plus 32 allowlisted
financial predictors; labels and audits are separate. Missing histories and
undefined ratios remain missing. No fitted imputation, scaling, vocabulary, or
distribution cutoff is generated. Ingestion failures roll back the transaction.

The fixture SQL integration check uses a separate synthetic source hash and an
outer rollback transaction, preserving real-data rows. It checks quarantine,
counts, missing-value formulas, SQL/Python agreement, reingestion, label tamper
detection, and rollback. CI uses an ephemeral PostgreSQL service; it downloads
dependencies only and never downloads the dataset or trains models. The CI
workflow is prepared; no remote CI run is claimed.

## Qualified independent diagnostic

The following reproduces the available measurements using only the Python
standard library; it **cannot satisfy the canonical runtime/SQL exit checks**:

```bash
cd '/mnt/c/Users/Danieal/Desktop/Credit Risk Project'
PYTHONPATH=src python3 scripts/reproduce_inspection.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Use the wrapper so source-label access is logged before binary cell decoding.
Do not use Python's `-O` flag: the deliberately bounded diagnostic requires its
assertions. It accepts the known OLE/BIFF8 layout, checks exact headers and cell
coverage, rejects unsupported cell records, and preserves source bytes. It is
independent diagnostic evidence, not an alternate official download or a claim
of `xlrd` parity. Its data CSV/JSONL outputs are ignored. It records first-access
attempts honestly; the original attempt window remains in provenance and the
test-exposure log.

Current reviewed inspection reports have suffix `uci350-v1.1`. Original
unversioned inspection reports and `feature_contract_v1.json` are retained draft
evidence from before integrity-review corrections. The existing split manifest
and summary remain byte-frozen, and `artifacts/split_checks/` records successful
validation under the revised feature/schema contract. All original and revised
allocations agree. Canonical reproduction has now confirmed the same manifest
using xlrd; the current receipt is identified in `reports/phase1.md`.
Future reproduction must verify it again: a mismatch is a blocker, never a reason
to choose another split.

## Git and service lifecycle

Generated customer-level data, credentials, environments and runtime artifacts
remain outside Git. Historical training provenance uses content hashes where
a Git commit was unavailable. The publication checkout has its own local history.

```bash
python3 scripts/dev_db.py status
python3 scripts/dev_db.py stop
```

Stopping preserves the dedicated volume and does not remove any resources.

The recorded Phase 1 gate passed with canonical reader/SQL evidence. No remote
CI or fresh-volume reproduction was claimed at that checkpoint. Later modeling
stages and their recorded results are documented in the phase-specific guides.
