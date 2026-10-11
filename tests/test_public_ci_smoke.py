"""Public fixture smoke must work without weakening historical acceptance guards."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from credit_risk.models.phase4_inputs import accepted_integrity


def test_phase4_smoke_with_only_public_runtime_code_and_no_receipts(tmp_path):
    repository = Path(__file__).resolve().parents[1]
    isolated = tmp_path / 'public-fixture'
    shutil.copytree(repository / 'src', isolated / 'src',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    scripts = isolated / 'scripts'
    scripts.mkdir()
    smoke = scripts / 'phase4_smoke.py'
    shutil.copyfile(repository / 'scripts/phase4_smoke.py', smoke)
    assert not (isolated / 'reports').exists()
    assert not (isolated / 'artifacts').exists()
    assert not (isolated / 'data').exists()
    environment = {**os.environ, 'PYTHONPATH': str(isolated / 'src'),
                   'PYTHONDONTWRITEBYTECODE': '1',
                   'MLFLOW_TRACKING_URI': 'http://unusable.invalid:1',
                   'POSTGRES_DB': 'unusable_database',
                   'POSTGRES_HOST_PORT': '1'}
    result = subprocess.run([sys.executable, str(smoke)], cwd=isolated,
                            env=environment, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert ('Synthetic calibration/TreeSHAP/plot/save-load smoke passed; '
            'no real-data fitting or test exposure.') in result.stdout
    assert not (isolated / 'reports').exists()
    assert not (isolated / 'artifacts').exists()


def test_historical_integrity_still_requires_the_actual_acceptance_receipt(tmp_path):
    with pytest.raises(FileNotFoundError) as error:
        accepted_integrity(tmp_path, model_root=tmp_path / 'historical-models')
    assert Path(error.value.filename) == tmp_path / 'reports/phase3_acceptance.json'
