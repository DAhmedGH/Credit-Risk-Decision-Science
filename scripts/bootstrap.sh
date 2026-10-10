#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"
export UV_CACHE_DIR="$task_root/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$task_root/.tools/python"
export UV_PYTHON_BIN_DIR="$task_root/.tools/bin"
mkdir -p .tools/bin
if [ ! -x .tools/bin/uv ]; then
  curl --fail --location --silent --show-error \
    https://astral.sh/uv/0.8.22/install.sh --output .tools/uv-install.sh
  UV_INSTALL_DIR="$task_root/.tools/bin" UV_NO_MODIFY_PATH=1 sh .tools/uv-install.sh
fi
.tools/bin/uv python install 3.12
if [ -e .venv ]; then
  .venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12), "Existing .venv is not Python 3.12; preserve it and resolve manually"'
else
  .tools/bin/uv venv --python 3.12 .venv
fi
.tools/bin/uv pip sync --python .venv/bin/python requirements.lock
.tools/bin/uv pip install --python .venv/bin/python --no-deps --no-build-isolation -e .
.tools/bin/uv pip check --python .venv/bin/python
.venv/bin/python scripts/environment_smoke.py
printf '%s\n' 'Project Python 3.12 environment ready. No other Python environment was changed.'
