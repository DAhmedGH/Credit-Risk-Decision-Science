"""Portable public scoring, verification and restoration; no historical workflow."""

import argparse
import io
import json
from pathlib import Path
import tarfile

from credit_risk.scoring_package import (
    ORIGIN, digest, read_verified_package, restore_package, verify_package,
)


def load_public_bundle(artifacts, *, trust_artifacts=False):
    if not trust_artifacts:
        raise ValueError('Serialized models require explicit trust: use --trust-artifacts')
    manifest, contents = read_verified_package(artifacts)
    import joblib
    import numpy as np
    from credit_risk.features import feature_contract, PREDICTORS
    from credit_risk.models.bundle import ProbabilityBundle
    from credit_risk.decisioning.policy import FrozenPolicy, Scenario

    schema = json.loads(contents['feature_schema.json'])
    if schema != feature_contract():
        raise ValueError('Public package financial feature schema differs')
    policy = json.loads(contents['policy.json'])
    for definitions in [{'scenario': Scenario().to_dict(), 'policies': policy['base_policies']},
                        *policy['sensitivity']['scenarios']]:
        Scenario.from_dict(definitions['scenario'])
        for definition in definitions['policies']:
            FrozenPolicy.from_dict(definition)
    pipeline = joblib.load(io.BytesIO(contents['pipeline.joblib']))
    if (not np.array_equal(pipeline.classes_, [0, 1])
            or tuple(pipeline.named_steps['features'].columns) != tuple(PREDICTORS)):
        raise ValueError('Loaded fitted model class mapping or feature allowlist differs')
    provenance = {**ORIGIN, 'verified_manifest_sha256': digest(contents['manifest.json'])}
    return ProbabilityBundle(pipeline, pipeline, 'raw', schema, provenance, policy, {}), manifest


def score_public_file(artifacts, input_path, output_dir, *, trust_artifacts=False,
                      scenario_id='base', policy_id='empirical'):
    bundle, manifest = load_public_bundle(artifacts, trust_artifacts=trust_artifacts)
    from credit_risk.artifacts import file_sha256, write_json
    from credit_risk.inference import read_batch, score_frame

    scored, rejected, receipt = score_frame(
        bundle, read_batch(input_path), scenario_id=scenario_id, policy_id=policy_id,
        model_version=ORIGIN['probability_bundle_sha256'])
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    scored.to_csv(output / 'scored.csv', index=False)
    rejected.to_csv(output / 'quarantined.csv', index=False)
    receipt.update({'input_sha256': file_sha256(input_path),
                    'bundle_sha256': ORIGIN['probability_bundle_sha256'],
                    'fitted_pipeline_sha256': ORIGIN['pipeline_sha256'],
                    'original_freeze_sha256': ORIGIN['freeze_content_sha256'],
                    'distribution_version': manifest['version'],
                    'delivery_sha256': manifest['delivery_sha256'],
                    'manifest_sha256': bundle.model_metadata['verified_manifest_sha256'],
                    'scenario_id': scenario_id, 'policy_id': policy_id})
    write_json(output / 'receipt.json', receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    score = commands.add_parser('score', help='Score unlabeled records with a trusted public package')
    score.add_argument('--artifacts', required=True, type=Path)
    score.add_argument('--trust-artifacts', required=True, action='store_true')
    score.add_argument('--input', required=True, type=Path)
    score.add_argument('--output', required=True, type=Path)
    score.add_argument('--scenario', default='base')
    score.add_argument('--policy', default='empirical')
    verify = commands.add_parser('verify', help='Verify files and runtime without deserializing')
    verify.add_argument('--artifacts', required=True, type=Path)
    restore = commands.add_parser('restore', help='Safely restore a checksum-verified package')
    restore.add_argument('--archive', required=True, type=Path)
    restore.add_argument('--sha256', required=True)
    restore.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'score':
            result = score_public_file(args.artifacts, args.input, args.output,
                                      trust_artifacts=args.trust_artifacts,
                                      scenario_id=args.scenario, policy_id=args.policy)
        elif args.command == 'restore':
            result = restore_package(args.archive, args.destination, expected_sha256=args.sha256)
        else:
            manifest = verify_package(args.artifacts)
            result = {'version': manifest['version'], 'delivery_sha256': manifest['delivery_sha256'],
                      'verified': True, 'deserialization': False}
    except (ValueError, OSError, EOFError, tarfile.TarError) as exc:
        parser.exit(1, f'Public scoring error: {exc}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
