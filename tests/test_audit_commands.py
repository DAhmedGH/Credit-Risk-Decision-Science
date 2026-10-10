"""Public-command errors must precede artifact access or scientific execution."""

from pathlib import Path
import subprocess
import sys

import pytest

from credit_risk import phase5


@pytest.mark.parametrize('argv, message', [
    (['score'], 'score requires --input and --output'),
    (['score', '--input', 'batch.csv'], 'score requires --input and --output'),
    (['monitor'], 'monitor requires --output'),
])
def test_missing_command_paths_fail_before_artifact_loading(monkeypatch, capsys, argv, message):
    def forbidden(*args, **kwargs):
        raise AssertionError('Missing arguments must fail before artifact loading')
    monkeypatch.setattr(phase5, 'preflight', forbidden)
    import credit_risk.inference
    monkeypatch.setattr(credit_risk.inference, 'score_file', forbidden)
    with pytest.raises(SystemExit) as error:
        phase5.main(argv)
    assert error.value.code == 2
    assert message in capsys.readouterr().err


@pytest.mark.parametrize('absolute', [False, True])
def test_readiness_is_resolved_under_explicit_project_root(tmp_path, monkeypatch, absolute):
    root = tmp_path / 'restored'
    path = root / 'reports/review.json'
    observed = []
    def evaluation(project, readiness):
        observed.append((project, readiness))
        return {'scope': 'fixture only; no evaluation'}
    monkeypatch.setattr(phase5, 'evaluate', evaluation)
    phase5.main(['evaluate', '--root', str(root), '--readiness',
                 str(path) if absolute else 'reports/review.json'])
    assert observed == [(root.resolve(), path)]


def test_optimized_python_cannot_bypass_reproduction_validation(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'scripts/reproduce_phase5.py'
    output = tmp_path / 'output'
    result = subprocess.run([sys.executable, '-O', str(script), '--output', str(output)],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'requires assertions enabled' in result.stderr
    assert not output.exists()
