#!/usr/bin/env bash
# Add explanation packages without upgrading any accepted Phase 3 distribution.
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/credit-risk-phase4-uv}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
phase4_lock="$(mktemp /tmp/credit-risk-phase4-resolved.XXXXXX.lock)"
trap 'rm -f -- "$phase4_lock"' EXIT
.venv/bin/python -m credit_risk.phase4 integrity
.tools/bin/uv pip compile --python .venv/bin/python requirements-phase4.in --output-file "$phase4_lock"
.tools/bin/uv pip install --python .venv/bin/python -r "$phase4_lock"
.tools/bin/uv pip check --python .venv/bin/python
.venv/bin/python scripts/phase4_smoke.py
.venv/bin/ruff check . --no-cache
.venv/bin/python -m pytest -q -p no:cacheprovider
.venv/bin/python - "$phase4_lock" <<'PY'
import hashlib
import shutil
import sys
from pathlib import Path
accepted = Path('reports/phase3_source_snapshots/accepted/requirements.lock')
assert hashlib.sha256(accepted.read_bytes()).hexdigest() == '31e7241f3499567f92579f1381892351dcd433faf219fe8b0be70321937e6b57'
archive = Path('requirements-phase3.lock')
if archive.exists():
    assert archive.read_bytes() == accepted.read_bytes()
else:
    shutil.copyfile(accepted, archive)
shutil.copyfile(sys.argv[1], 'requirements.lock')
PY
printf '%s\n' 'Phase 4 explanation environment smoke passed; accepted pins preserved. Resume saved run without calibration refits.'
