#!/usr/bin/env bash
# Install only into the existing project environment; freeze after smoke/tests.
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$task_root/.cache/uv}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12), "Preserve existing environment; Python 3.12 required"'
# An archive called Phase 1 must contain the actual Phase 1 lock, not a later one.
.venv/bin/python - <<'PY'
import hashlib
import json
from pathlib import Path
receipt = json.loads(Path("reports/phase1_handoff.json").read_text())
expected = receipt["artifact_inspection"]["verified_file_sha256"]["requirements.lock"]
archive = Path("requirements-phase1.lock")
candidate = archive if archive.exists() else Path("requirements.lock")
if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
    raise ValueError("Phase 1 lock archive is missing or changed; inspect before replacing a lock")
PY
phase2_lock="$(mktemp /tmp/credit-risk-phase2-resolved.XXXXXX.lock)"
trap 'rm -f -- "$phase2_lock"' EXIT
.tools/bin/uv pip compile --python .venv/bin/python requirements-phase2.in --output-file "$phase2_lock"
.tools/bin/uv pip install --python .venv/bin/python -r "$phase2_lock"
.tools/bin/uv pip install --python .venv/bin/python --no-deps --no-build-isolation -e .
.tools/bin/uv pip check --python .venv/bin/python
.venv/bin/python scripts/environment_smoke.py
.venv/bin/python scripts/phase2_smoke.py
.venv/bin/ruff check . --no-cache
.venv/bin/python -m pytest -q -p no:cacheprovider
if [ ! -e requirements-phase1.lock ]; then
  cp requirements.lock requirements-phase1.lock
fi
cp "$phase2_lock" requirements.lock
printf '%s\n' 'Phase 2 dependency closure verified and locked; actual development baselines are the next command.'
