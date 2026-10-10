"""Create a local trusted restoration payload; never include credentials or environments."""
from pathlib import Path
import tarfile
from credit_risk.artifacts import file_sha256,write_json
from credit_risk.models.bundle import verify_freeze
root=Path('.').resolve()
manifest=root/'artifacts/models/phase4/9ca62eca2665438c9c97b4889413acfa/freeze_manifest.json'
m=verify_freeze(manifest)
files={manifest, *(manifest.parent/p for p in m['artifacts'])}
files.update(root/p for p in m['integrity']['input_hashes'])
files.add(root/'artifacts/source_manifest.json')
for folder in ['artifacts/runtime/phase5/final_evaluation','artifacts/runtime/phase5/example_score']:
    files.update(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
files.add(root/'examples/scoring_batch.csv')
archive=root/'artifacts/runtime/phase5/credit-risk-phase5-artifacts.tar.gz'
if archive.exists():
    raise SystemExit('Archive exists; do not overwrite durable evidence')
with tarfile.open(archive,'w:gz') as tar:
    for p in sorted(files):
        if p.is_symlink():
            raise SystemExit('Payload must use regular local files')
        tar.add(p,arcname=str(p.relative_to(root)),recursive=False)
write_json(root/'reports/phase5/artifact_delivery.json',{'archive':str(archive.relative_to(root)),
           'archive_sha256':file_sha256(archive),'bytes':archive.stat().st_size,
           'files':{str(p.relative_to(root)):file_sha256(p) for p in sorted(files)},
           'scope':'trusted local scientific payload; combine with tracked source checkout',
           'credentials_environments_runtime_tracking_included':False})
print('Saved durable scientific payload: '+file_sha256(archive))
