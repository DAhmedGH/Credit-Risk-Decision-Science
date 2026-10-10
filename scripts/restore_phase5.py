"""Restore a trusted local project archive only after checking its recorded digest."""
import argparse
import hashlib
from pathlib import Path
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument('archive', type=Path)
parser.add_argument('--sha256', required=True)
parser.add_argument('--destination', type=Path, required=True)
args = parser.parse_args()
digest = hashlib.sha256(args.archive.read_bytes()).hexdigest()
if digest != args.sha256:
    raise SystemExit('Archive SHA-256 mismatch')
if args.destination.exists():
    raise SystemExit('Destination must be new; never overwrite accepted work')
with tarfile.open(args.archive) as archive:
    for entry in archive.getmembers():
        path = Path(entry.name)
        if (path.is_absolute() or '..' in path.parts or entry.issym() or entry.islnk()
                or not (entry.isfile() or entry.isdir())):
            raise SystemExit('Unsafe archive entry')
    args.destination.mkdir(parents=True)
    archive.extractall(args.destination, filter='data')
print('Restored digest-checked archive; follow the documented scoring or historical replay workflow')
