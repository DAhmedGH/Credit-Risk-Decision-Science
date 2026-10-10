"""Prepare the minimal public distribution from read-only accepted Phase 4 artifacts."""

import argparse
import gzip
import io
import json
from pathlib import Path
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from credit_risk.models.bundle import verify_freeze
from credit_risk.scoring_package import ORIGIN, RUNTIME, TRANSFORMS, VERSION, canonical, digest


def package(accepted_directory, output):
    source, output = Path(accepted_directory), Path(output)
    repository = Path(__file__).resolve().parents[1]
    if output.exists():
        raise ValueError('Package output directory must be new')
    frozen = verify_freeze(source / 'freeze_manifest.json')
    freeze_identity = json.loads((source / 'freeze_manifest.json').read_text())['freeze_sha256']
    if freeze_identity != ORIGIN['freeze_content_sha256']:
        raise ValueError('Unexpected accepted freeze identity')
    if frozen['run_id'] != ORIGIN['phase4_run_id'] or frozen['selected_mapping'] != 'raw':
        raise ValueError('Unexpected accepted model or probability mapping')
    if digest((source / 'probability_bundle.joblib').read_bytes()) != ORIGIN['probability_bundle_sha256']:
        raise ValueError('Unexpected original probability bundle hash')
    pipeline_path = 'accepted_models/xgboost_05_engineered_none/development_pipeline.joblib'
    pipeline = (source / pipeline_path).read_bytes()
    if digest(pipeline) != ORIGIN['pipeline_sha256']:
        raise ValueError('Accepted selected fitted pipeline hash differs')
    full_policy = json.loads((source / 'policy.json').read_text())
    policy = {'base_policies': full_policy['base_policies'], 'sensitivity': {
        'scenarios': [{'scenario': row['scenario'], 'policies': row['policies']}
                      for row in full_policy['sensitivity']['scenarios']]}}
    contents = {'pipeline.joblib': pipeline,
                'feature_schema.json': (source / 'feature_schema.json').read_bytes(),
                'policy.json': canonical(policy),
                'NOTICE.md': (repository / 'docs/scoring-package-notice.md').read_bytes()}
    hashes = {}
    for name in TRANSFORMS:
        relative = Path('src/credit_risk') / name
        live = (repository / relative).read_bytes()
        if digest(live) != digest((source / 'completion_source' / relative).read_bytes()):
            raise ValueError(f'Financial transformation differs from accepted source: {name}')
        hashes[name] = digest(live)
    manifest = {
        'version': VERSION,
        'scope': 'Inference-only distribution metadata; not an original acceptance receipt',
        'original_model': ORIGIN,
        'original_freeze_file_sha256': digest((source / 'freeze_manifest.json').read_bytes()),
        'original_feature_schema_sha256': frozen['artifacts']['feature_schema.json'],
        'original_policy_evidence_sha256': frozen['artifacts']['policy.json'],
        'policy_projection': 'base_policies plus sensitivity.scenarios[*].scenario/policies only; values unchanged',
        'base_scenario': {'scenario_id': 'base', 'gain': 50.0, 'loss': 500.0, 'cost': 0.0},
        'scenario_count': 11, 'policy_definition_count': 88,
        'runtime': {'python_major_minor': '3.12', 'validated_python': '3.12.11',
                    'dependencies': RUNTIME},
        'transformation_sha256': hashes,
        'files': {name: {'byte_length': len(data), 'sha256': digest(data)}
                  for name, data in sorted(contents.items())},
    }
    manifest['delivery_sha256'] = digest(canonical(manifest))
    contents['manifest.json'] = canonical(manifest)
    output.mkdir(parents=True)
    archive_path = output / 'credit-risk-scoring-v1.tar.gz'
    with archive_path.open('xb') as stream:
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for name, data in sorted(contents.items()):
                    info = tarfile.TarInfo(name)
                    info.size, info.mode, info.mtime = len(data), 0o644, 0
                    archive.addfile(info, io.BytesIO(data))
    archive_hash = digest(archive_path.read_bytes())
    (output / 'credit-risk-scoring-v1.sha256').write_text(
        f'{archive_hash}  {archive_path.name}\n')
    (output / 'credit-risk-scoring-v1.manifest.json').write_bytes(contents['manifest.json'])
    return {'archive': archive_path.name, 'archive_sha256': archive_hash,
            'archive_bytes': archive_path.stat().st_size,
            'delivery_sha256': manifest['delivery_sha256'], 'member_names': sorted(contents)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accepted-directory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.accepted_directory, args.output), indent=2))


if __name__ == '__main__':
    main()
