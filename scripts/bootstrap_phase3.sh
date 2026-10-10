#!/usr/bin/env bash
# Preserve the accepted environment; validate the addition before updating its lock.
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/credit-risk-phase3-uv}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
.venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12)'
.venv/bin/python - <<'PY'
from pathlib import Path
import hashlib
archive = Path('requirements-phase2.lock')
candidate = archive if archive.exists() else Path('requirements.lock')
expected = 'b8f4f36250c998b0d9850d8d99d6968b6810c244c06aa7c1262bb28d91c00fd5'
if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
    raise ValueError('Accepted Phase 2 lock missing/changed; do not replace it')
PY
phase3_lock="$(mktemp /tmp/credit-risk-phase3-resolved.XXXXXX.lock)"
trap 'rm -f -- "$phase3_lock"' EXIT
.tools/bin/uv pip compile --python .venv/bin/python requirements-phase3.in --output-file "$phase3_lock"
.tools/bin/uv pip install --python .venv/bin/python -r "$phase3_lock"
.tools/bin/uv pip install --python .venv/bin/python --no-deps --no-build-isolation -e .
.tools/bin/uv pip check --python .venv/bin/python
.venv/bin/python scripts/phase2_smoke.py
.venv/bin/python scripts/phase3_smoke.py
.venv/bin/ruff check . --no-cache
.venv/bin/python -m pytest -q -p no:cacheprovider
if [ ! -e requirements-phase2.lock ]; then
  cp requirements.lock requirements-phase2.lock
fi
cp "$phase3_lock" requirements.lock
printf '%s\n' 'Phase 3 compatibility verified and lock updated. Next: phase3-profile, then bounded family searches.'
