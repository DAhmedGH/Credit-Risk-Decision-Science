"""Verify and safely restore the separately versioned public scoring distribution.

This module uses only the standard library and never deserializes a model.
Historical freeze verification remains in models.bundle.
"""

import hashlib
import gzip
from importlib import metadata
import io
import json
from pathlib import Path
import re
import sys
import tarfile
import tempfile

VERSION = 'public-scoring-v1'
DELIVERY_ID = 'a2a9b2883f5543a1d4da2d8026f79e4ef60be79b97343357e946f3c7a906d40c'
MEMBERS = {'manifest.json', 'pipeline.joblib', 'feature_schema.json', 'policy.json', 'NOTICE.md'}
TRANSFORMS = ('features/__init__.py', 'data/schema.py', 'models/pipelines.py',
              'decisioning/policy.py')
RUNTIME = {'numpy': '2.2.6', 'pandas': '2.3.3', 'scipy': '1.15.3',
           'scikit-learn': '1.7.2', 'joblib': '1.5.2', 'threadpoolctl': '3.6.0',
           'xgboost-cpu': '3.0.5', 'pyarrow': '21.0.0'}
ORIGIN = {
    'phase4_run_id': '9ca62eca2665438c9c97b4889413acfa',
    'freeze_content_sha256': '89bcf0263890353b2c72f7b6490bd8ec374f8935af2f621793c867dd03a8aa8b',
    'probability_bundle_sha256': '45d24e21b67e27c5a522863457d7774536b6af3608bb5e9bf6e6b06c030bdbcd',
    'pipeline_sha256': '265db2cbe02e88ca7c75c29f39b5c0230a29ba40e4735ea808aea08df4a5e83c',
    'candidate_id': 'xgboost_05_engineered_none',
    'mapping': 'raw',
    'positive_class': 1,
}
MAX_ARCHIVE_BYTES = 5_000_000
MAX_MEMBER_BYTES = 1_000_000


class _BoundedReader:
    """Bound total decompression, including hidden GNU/PAX extension headers."""

    def __init__(self, stream):
        self.stream = stream
        self.remaining = len(MEMBERS) * MAX_MEMBER_BYTES + 64_000

    def read(self, size):
        data = self.stream.read(min(size, self.remaining + 1))
        self.remaining -= len(data)
        if self.remaining < 0:
            raise ValueError('Archive exceeds uncompressed size bound')
        return data


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate manifest key: {key}')
        result[key] = value
    return result


def read_verified_package(location, *, check_runtime=True):
    """Return verified in-memory bytes so deserialization uses exactly checked bytes."""
    root = Path(location)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Artifacts must be an existing package directory, not a symlink')
    if {p.name for p in root.iterdir()} != MEMBERS:
        raise ValueError('Package has missing or unexpected artifacts')
    contents = {}
    for name in sorted(MEMBERS):
        path = root / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MEMBER_BYTES:
            raise ValueError(f'Unsafe or oversized package artifact: {name}')
        contents[name] = path.read_bytes()
    try:
        manifest = json.loads(contents['manifest.json'], object_pairs_hook=_unique_object)
        if not isinstance(manifest, dict):
            raise ValueError('Invalid public delivery manifest object')
        payload = {k: v for k, v in manifest.items() if k != 'delivery_sha256'}
        if (manifest['version'] != VERSION or manifest['delivery_sha256'] != DELIVERY_ID
                or digest(canonical(payload)) != DELIVERY_ID):
            raise ValueError('Unsupported or altered public delivery manifest')
        if manifest['original_model'] != ORIGIN or manifest['runtime']['dependencies'] != RUNTIME:
            raise ValueError('Public package model identity or runtime contract differs')
        if manifest['runtime']['python_major_minor'] != '3.12':
            raise ValueError('Unsupported Python contract')
        files = manifest['files']
        if set(files) != MEMBERS - {'manifest.json'}:
            raise ValueError('Manifest inventory differs from the public package contract')
        for name, record in files.items():
            if (digest(contents[name]) != record['sha256']
                    or len(contents[name]) != record['byte_length']):
                raise ValueError(f'Package artifact checksum/length mismatch: {name}')
        if files['pipeline.joblib']['sha256'] != ORIGIN['pipeline_sha256']:
            raise ValueError('Fitted pipeline differs from the accepted model')
        transforms = manifest['transformation_sha256']
        if set(transforms) != set(TRANSFORMS):
            raise ValueError('Missing financial transformation compatibility information')
        for relative, expected in transforms.items():
            if digest((Path(__file__).parent / relative).read_bytes()) != expected:
                raise ValueError(f'Incompatible financial transformation: {relative}')
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError('Invalid public delivery manifest') from exc
    if check_runtime:
        if sys.version_info[:2] != (3, 12):
            raise ValueError('Public scoring requires Python 3.12; validated with 3.12.11')
        for name, expected in RUNTIME.items():
            try:
                actual = metadata.version(name)
            except metadata.PackageNotFoundError as exc:
                raise ValueError(f'Missing scoring dependency: {name}=={expected}') from exc
            if actual != expected:
                raise ValueError(f'Incompatible scoring dependency {name}: '
                                 f'expected {expected}, found {actual}')
    return manifest, contents


def verify_package(location, *, check_runtime=True):
    return read_verified_package(location, check_runtime=check_runtime)[0]


def restore_package(archive_path, destination, *, expected_sha256):
    """Checksum-check an archive and install only the five verified regular members."""
    if not re.fullmatch('[0-9a-f]{64}', expected_sha256):
        raise ValueError('Expected SHA-256 must be 64 lowercase hexadecimal characters')
    archive_path, destination = Path(archive_path), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination must be new; refusing to overwrite an installation')
    if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError('Archive exceeds public package size bound')
    data = archive_path.read_bytes()
    if digest(data) != expected_sha256:
        raise ValueError('Archive SHA-256 mismatch')
    contents = {}
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as compressed:
        with tarfile.open(fileobj=_BoundedReader(compressed), mode='r|') as archive:
            for member in archive:
                if member.name not in MEMBERS or member.name in contents:
                    raise ValueError('Unsafe, duplicate or unexpected archive members')
                if (not member.isreg() or member.sparse is not None
                        or not 0 <= member.size <= MAX_MEMBER_BYTES):
                    raise ValueError('Unsafe archive member type or size')
                with archive.extractfile(member) as stream:
                    content = stream.read(MAX_MEMBER_BYTES + 1)
                if len(content) != member.size:
                    raise ValueError('Archive member size mismatch')
                contents[member.name] = content
    if set(contents) != MEMBERS:
        raise ValueError('Missing archive members')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.scoring-install-', dir=destination.parent) as tmp:
        staged = Path(tmp) / 'package'
        staged.mkdir()
        for name, content in contents.items():
            target = staged / name
            target.write_bytes(content)
            target.chmod(0o644)
        manifest = verify_package(staged, check_runtime=False)
        # mkdir is exclusive, including a destination created during verification.
        destination.mkdir()
        for file in staged.iterdir():
            file.rename(destination / file.name)
    return {'version': manifest['version'], 'delivery_sha256': manifest['delivery_sha256'],
            'archive_sha256': expected_sha256, 'artifact_count': len(MEMBERS),
            'deserialization': False}
