"""Public distribution regression checks use only the shipped model and synthetic inputs."""

import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tarfile

import joblib
import numpy as np
import pytest

from credit_risk import scoring_package as package
from credit_risk.scoring import load_public_bundle, score_public_file

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'bundles/credit-risk-scoring-v1.tar.gz'
ARCHIVE_SHA = (ROOT / 'bundles/credit-risk-scoring-v1.sha256').read_text().split()[0]


@pytest.fixture
def installed(tmp_path):
    directory = tmp_path / 'installed'
    receipt = package.restore_package(ARCHIVE, directory, expected_sha256=ARCHIVE_SHA)
    assert receipt['artifact_count'] == 5 and not receipt['deserialization']
    return directory


def test_restoration_identity_and_manifest_copy(installed):
    manifest = package.verify_package(installed)
    assert manifest['delivery_sha256'] == package.DELIVERY_ID
    assert (installed / 'manifest.json').read_bytes() == (
        ROOT / 'bundles/credit-risk-scoring-v1.manifest.json').read_bytes()
    assert manifest['original_model'] == package.ORIGIN
    assert package.digest((installed / 'pipeline.joblib').read_bytes()) == package.ORIGIN['pipeline_sha256']


def test_trust_required_before_deserialization(installed, monkeypatch):
    monkeypatch.setattr(joblib, 'load', lambda *a, **k: pytest.fail('Deserialized without trust'))
    with pytest.raises(ValueError, match='explicit trust'):
        load_public_bundle(installed)


@pytest.mark.parametrize('name', sorted(package.MEMBERS))
@pytest.mark.parametrize('operation', ['missing', 'altered', 'symlink'])
def test_artifact_failure_before_deserialization(installed, monkeypatch, name, operation):
    path = installed / name
    if operation == 'missing':
        path.unlink()
    elif operation == 'altered':
        path.write_bytes(path.read_bytes() + b'alteration')
    else:
        copy = installed.parent / name
        shutil.move(path, copy)
        path.symlink_to(copy)
    monkeypatch.setattr(joblib, 'load', lambda *a, **k: pytest.fail('Loaded corrupt artifacts'))
    with pytest.raises(ValueError):
        load_public_bundle(installed, trust_artifacts=True)


def test_manifest_rehash_cannot_change_policy_identity(installed, monkeypatch):
    policy_path = installed / 'policy.json'
    policy = json.loads(policy_path.read_text())
    policy['base_policies'][-1]['cutoff'] = 0.9
    policy_path.write_bytes(package.canonical(policy))
    manifest_path = installed / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['files']['policy.json'] = {'sha256': package.digest(policy_path.read_bytes()),
                                       'byte_length': policy_path.stat().st_size}
    manifest.pop('delivery_sha256')
    manifest['delivery_sha256'] = package.digest(package.canonical(manifest))
    manifest_path.write_bytes(package.canonical(manifest))
    monkeypatch.setattr(joblib, 'load', lambda *a, **k: pytest.fail('Loaded an unpinned policy'))
    with pytest.raises(ValueError, match='altered public delivery'):
        load_public_bundle(installed, trust_artifacts=True)


def test_incompatible_dependency_precedes_deserialization(installed, monkeypatch):
    monkeypatch.setattr(package.metadata, 'version', lambda name: 'incompatible')
    monkeypatch.setattr(joblib, 'load', lambda *a, **k: pytest.fail('Loaded incompatible runtime'))
    with pytest.raises(ValueError, match='Incompatible scoring dependency'):
        load_public_bundle(installed, trust_artifacts=True)


def test_missing_dependency_precedes_deserialization(installed, monkeypatch):
    def missing(name):
        raise package.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(package.metadata, 'version', missing)
    with pytest.raises(ValueError, match='Missing scoring dependency'):
        package.verify_package(installed)


def test_incompatible_code_precedes_deserialization(installed, tmp_path, monkeypatch):
    for name in package.TRANSFORMS:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'src/credit_risk' / name, target)
    monkeypatch.setattr(package, '__file__', str(tmp_path / 'scoring_package.py'))
    (tmp_path / 'features/__init__.py').write_text('altered transformation')
    monkeypatch.setattr(joblib, 'load', lambda *a, **k: pytest.fail('Loaded incompatible code'))
    with pytest.raises(ValueError, match='Incompatible financial transformation'):
        load_public_bundle(installed, trust_artifacts=True)


def test_no_overwrite_or_bad_archive_digest(installed, tmp_path):
    sentinel = installed / 'sentinel'
    sentinel.write_text('preserve')
    with pytest.raises(ValueError, match='refusing to overwrite'):
        package.restore_package(ARCHIVE, installed, expected_sha256=ARCHIVE_SHA)
    assert sentinel.read_text() == 'preserve'
    destination = tmp_path / 'bad'
    with pytest.raises(ValueError, match='SHA-256 mismatch'):
        package.restore_package(ARCHIVE, destination, expected_sha256='0' * 64)
    assert not destination.exists()


@pytest.mark.parametrize('mutation', ['traversal', 'absolute', 'symlink', 'hardlink',
                                    'directory', 'duplicate', 'fifo', 'extra', 'oversized', 'sparse'])
def test_unsafe_archive_rejected_without_installation(tmp_path, mutation):
    archive_path = tmp_path / 'unsafe.tar.gz'
    with tarfile.open(ARCHIVE) as original, tarfile.open(archive_path, 'w:gz') as altered:
        for member in original.getmembers():
            data = original.extractfile(member).read()
            if member.name == 'pipeline.joblib':
                if mutation == 'sparse':
                    member.type = tarfile.GNUTYPE_SPARSE
                if mutation == 'traversal':
                    member.name = '../pipeline.joblib'
                if mutation == 'absolute':
                    member.name = '/pipeline.joblib'
                if mutation in {'symlink', 'hardlink', 'directory', 'fifo'}:
                    member.type = {'symlink': tarfile.SYMTYPE, 'hardlink': tarfile.LNKTYPE,
                                   'directory': tarfile.DIRTYPE, 'fifo': tarfile.FIFOTYPE}[mutation]
                    member.linkname = '/outside'
                    member.size = 0
                if mutation == 'oversized':
                    data = b'x' * (package.MAX_MEMBER_BYTES + 1)
                    member.size = len(data)
            altered.addfile(member, io.BytesIO(data) if member.isreg() else None)
            if mutation == 'duplicate' and member.name == 'pipeline.joblib':
                altered.addfile(member, io.BytesIO(data))
        if mutation == 'extra':
            altered.addfile(tarfile.TarInfo('private-data.csv'), io.BytesIO())
    destination = tmp_path / 'install'
    with pytest.raises(ValueError):
        package.restore_package(archive_path, destination,
                                expected_sha256=package.digest(archive_path.read_bytes()))
    assert not destination.exists()


def test_saved_example_exact_and_no_fit_or_network(installed, tmp_path, monkeypatch):
    from sklearn.pipeline import Pipeline
    from credit_risk.models.pipelines import FoldLocalXGBClassifier
    def forbidden(*a, **k):
        raise AssertionError('Scoring attempted fitting or network access')
    monkeypatch.setattr(Pipeline, 'fit', forbidden)
    monkeypatch.setattr(FoldLocalXGBClassifier, 'fit', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setenv('POSTGRES_DB', 'unusable_database')
    monkeypatch.setenv('MLFLOW_TRACKING_URI', 'http://unusable.invalid:1')
    output = tmp_path / 'output'
    receipt = score_public_file(installed, ROOT / 'examples/scoring_batch.csv', output,
                                trust_artifacts=True)
    assert (receipt['input_count'], receipt['scored_count'], receipt['quarantined_count']) == (12, 12, 0)
    assert not receipt['fitting'] and not receipt['database_access']
    assert (output / 'scored.csv').read_bytes() == (ROOT / 'examples/scoring_output.csv').read_bytes()


def test_hidden_pax_decompression_bound(tmp_path):
    archive = tmp_path / 'pax-bomb.tar.gz'
    content = b'x' * (len(package.MEMBERS) * package.MAX_MEMBER_BYTES + 100_000)
    with tarfile.open(archive, 'w:gz', format=tarfile.USTAR_FORMAT) as stream:
        header = tarfile.TarInfo('pax-header')
        header.type = tarfile.XHDTYPE
        header.size = len(content)
        stream.addfile(header, io.BytesIO(content))
    destination = tmp_path / 'uninstalled'
    with pytest.raises(ValueError, match='uncompressed size bound'):
        package.restore_package(archive, destination, expected_sha256=package.digest(archive.read_bytes()))
    assert not destination.exists()


def test_receipt_binds_verified_manifest_snapshot(installed, tmp_path, monkeypatch):
    import credit_risk.scoring as scoring
    verified_hash = package.digest((installed / 'manifest.json').read_bytes())
    def load_then_change_file(*args, **kwargs):
        result = load_public_bundle(*args, **kwargs)
        (installed / 'manifest.json').write_text('changed after verification')
        return result
    monkeypatch.setattr(scoring, 'load_public_bundle', load_then_change_file)
    receipt = scoring.score_public_file(installed, ROOT / 'examples/scoring_batch.csv',
                                        tmp_path / 'snapshot', trust_artifacts=True)
    assert receipt['manifest_sha256'] == verified_hash
    assert (tmp_path / 'snapshot/scored.csv').read_bytes() == (ROOT / 'examples/scoring_output.csv').read_bytes()


@pytest.mark.parametrize('input_format', ['csv', 'parquet'])
def test_receipt_binds_scored_input_snapshot(installed, tmp_path, monkeypatch, input_format):
    import credit_risk.inference as inference

    input_path = tmp_path / f'input.{input_format}'
    frame = inference.read_batch(ROOT / 'examples/scoring_batch.csv')
    if input_format == 'csv':
        shutil.copyfile(ROOT / 'examples/scoring_batch.csv', input_path)
    else:
        frame.to_parquet(input_path, index=False)
    snapshot_hash = package.digest(input_path.read_bytes())
    original_score = inference.score_frame

    def score_then_replace(*args, **kwargs):
        result = original_score(*args, **kwargs)
        input_path.write_bytes(b'replacement batch')
        return result

    monkeypatch.setattr(inference, 'score_frame', score_then_replace)
    output = tmp_path / 'scored-snapshot'
    receipt = score_public_file(installed, input_path, output, trust_artifacts=True)
    assert receipt['input_sha256'] == snapshot_hash
    assert receipt['input_sha256'] != package.digest(input_path.read_bytes())
    assert (output / 'scored.csv').read_bytes() == (ROOT / 'examples/scoring_output.csv').read_bytes()


def test_all_quarantined_never_predicts(installed):
    from credit_risk.inference import read_batch, score_frame
    bundle, _ = load_public_bundle(installed, trust_artifacts=True)
    bundle.predict_probability = lambda *a: pytest.fail('Predicted with zero valid rows')
    frame = read_batch(ROOT / 'examples/scoring_batch.csv')
    frame['limit_bal'] = 0
    scored, quarantine, receipt = score_frame(bundle, frame)
    assert len(scored) == 0 and len(quarantine) == 12
    assert receipt['counts_reconcile']


def test_order_quarantine_empty_single_row_and_frozen_policies(installed, tmp_path):
    from credit_risk.inference import read_batch, score_frame
    bundle, _ = load_public_bundle(installed, trust_artifacts=True)
    frame = read_batch(ROOT / 'examples/scoring_batch.csv').astype(object)
    frame['record_id'] = [f'{i:04}' for i in range(len(frame))]
    frame.loc[1, 'limit_bal'] = 0
    frame.loc[3, 'pay_amt_2005_09'] = -1
    frame.loc[5, 'pay_status_2005_04'] = 999
    frame.loc[6, 'bill_amt_2005_04'] = -100
    frame.loc[7, 'bill_amt_2005_04'] = None
    scored, quarantine, receipt = score_frame(bundle, frame)
    assert receipt['counts_reconcile'] and len(scored) == 10 and len(quarantine) == 2
    assert quarantine.input_position.tolist() == [1, 3]
    assert quarantine.record_id.tolist() == ['0001', '0003']
    assert scored.record_id.tolist() == [f'{i:04}' for i in range(12) if i not in (1, 3)]
    one, _, _ = score_frame(bundle, frame.iloc[[0]])
    assert one.p_default.iloc[0] == scored.p_default.iloc[0]
    empty = tmp_path / 'empty.csv'
    frame.iloc[:0].to_csv(empty, index=False)
    empty_receipt = score_public_file(installed, empty, tmp_path / 'empty-output', trust_artifacts=True)
    assert [empty_receipt[k] for k in ['input_count', 'scored_count', 'quarantined_count']] == [0, 0, 0]
    scenarios = [{'scenario': {'scenario_id': 'base', 'gain': 50, 'loss': 500, 'cost': 0},
                  'policies': bundle.policy['base_policies']}, *bundle.policy['sensitivity']['scenarios']]
    before = joblib.hash(bundle.base)
    for cell in scenarios:
        s = cell['scenario']
        for policy in cell['policies']:
            result, _, _ = score_frame(bundle, frame, scenario_id=s['scenario_id'], policy_id=policy['policy_id'])
            p = result.p_default.to_numpy()
            accept = np.ones(len(p), dtype=bool) if policy['kind'] == 'all' else (
                np.zeros(len(p), dtype=bool) if policy['kind'] == 'none' else p < policy['cutoff'])
            assert result.decision_simulated.tolist() == np.where(accept, 'accept_simulated', 'abstain_simulated').tolist()
            utility = np.where(accept, (1-p)*s['gain'] - p*s['loss'] - s['cost'], 0)
            np.testing.assert_array_equal(result.expected_utility, utility)
    assert joblib.hash(bundle.base) == before


def test_cwd_independent_cli_and_clear_failures(installed, tmp_path):
    command = [sys.executable, '-m', 'credit_risk.scoring', 'score', '--artifacts', str(installed),
               '--input', str(ROOT / 'examples/scoring_batch.csv'), '--output', str(tmp_path / 'cli')]
    import os
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}
    result = subprocess.run(command + ['--trust-artifacts'], cwd=tmp_path, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / 'cli/scored.csv').read_bytes() == (ROOT / 'examples/scoring_output.csv').read_bytes()
    missing_trust = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True)
    assert missing_trust.returncode == 2 and '--trust-artifacts' in missing_trust.stderr
    missing_artifact = subprocess.run([sys.executable, '-m', 'credit_risk.scoring', 'verify',
                                       '--artifacts', str(tmp_path / 'absent')],
                                      cwd=tmp_path, env=env, capture_output=True, text=True)
    assert missing_artifact.returncode == 1 and 'Public scoring error' in missing_artifact.stderr
