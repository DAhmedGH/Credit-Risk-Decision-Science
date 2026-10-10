"""Small deterministic artifacts, content hashes, and immutable freeze checks."""

import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def file_sha256(path):
    return sha256_bytes(Path(path).read_bytes())


def atomic_write(path, content, frozen=False):
    path = Path(path)
    if frozen and path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Refusing to overwrite frozen/stale artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value, frozen=False):
    atomic_write(path, json_bytes(value), frozen=frozen)


def write_run_evidence(path, value):
    """Preserve prior reports while refreshing execution-only code/commit provenance.

    A change to scientific dependencies or results must use a new version/path.
    Initializing Git or adding unrelated phase code may refresh execution metadata.
    """
    path = Path(path)
    content = json_bytes(value)
    if path.exists() and path.read_bytes() != content:
        prior = json.loads(path.read_text())
        execution_only = {"git_commit", "code_tree_sha256"}
        def stable(report):
            return {key: item for key, item in report.items() if key not in execution_only}
        if stable(prior) != stable(value):
            raise ValueError(f"Scientific evidence changed; version the report rather than replacing {path}")
        snapshot = path.parent / "history" / f"{path.stem}_{file_sha256(path)[:16]}.json"
        atomic_write(snapshot, path.read_bytes(), frozen=True)
    atomic_write(path, content)


def write_csv(path, rows, columns, frozen=False):
    import io

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(path, stream.getvalue().encode(), frozen=frozen)


def read_csv(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))
