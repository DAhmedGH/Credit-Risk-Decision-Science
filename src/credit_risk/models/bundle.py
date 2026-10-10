"""Trusted-local pre-test bundle and content-bound freeze verification."""

from dataclasses import dataclass
import json
from pathlib import Path

import joblib

from credit_risk.artifacts import file_sha256, json_bytes, sha256_bytes
from credit_risk.models.pipelines import positive_probability


@dataclass
class ProbabilityBundle:
    base: object
    probability_estimator: object
    mapping: str
    feature_schema: dict
    model_metadata: dict
    policy: dict
    references: dict

    def predict_probability(self, X):
        return positive_probability(self.probability_estimator, X)


def verify_freeze(path, *, require_review=True):
    path = Path(path)
    manifest = json.loads(path.read_text())
    identity = manifest.pop("freeze_sha256")
    if sha256_bytes(json_bytes(manifest)) != identity:
        raise ValueError("Freeze manifest content identity changed")
    if not manifest["complete_bundle_frozen"] or not manifest["explanations_complete"]:
        raise ValueError("Incomplete pre-test bundle")
    if require_review and manifest.get("independent_review_status") != "PASS":
        raise ValueError("Independent review has not passed")
    required = {manifest['bundle_path'], 'feature_schema.json', 'policy.json',
                'model_metadata.json', 'report_definitions.json', 'calibration_fit_evidence.json',
                'serialization_evidence.json', 'model_card.md', 'explanations/metadata.json',
                'explanations/shap_values.npz', 'explanations/shap_global.png',
                'explanations/shap_dependence_1.png', 'explanations/shap_dependence_2.png'}
    for candidate in ('dummy_prior', 'logistic_00_engineered_none',
                      'random_forest_02_engineered_none', 'xgboost_04_engineered_none',
                      'xgboost_05_engineered_none'):
        required.update({f'accepted_models/{candidate}/development_pipeline.joblib',
                         f'accepted_models/{candidate}/metadata.json'})
    artifacts = manifest['artifacts']
    if not required <= set(artifacts):
        raise ValueError('Freeze omits required bundle/report/reference/explanation artifacts')
    if artifacts['report_definitions.json'] != manifest.get('report_definitions_sha256'):
        raise ValueError('Report definition hash is not bound to the freeze')
    if require_review and not {'review.json', 'review.md'} <= set(artifacts):
        raise ValueError('Freeze omits independent review evidence')
    for name, digest in artifacts.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('Frozen artifact paths must be safe relative paths')
        target = path.parent / relative
        if (target.is_symlink() or not target.resolve().is_relative_to(path.parent.resolve())
                or file_sha256(target) != digest):
            raise ValueError(f"Frozen artifact changed: {name}")
    explanation = json.loads((path.parent / 'explanations/metadata.json').read_text())
    cases = explanation.get('diagnostic_cases', {})
    if set(cases) != {'correct_default', 'correct_nondefault', 'missed_default', 'false_alarm'}:
        raise ValueError('Explanation case availability must be explicit')
    for name, case in cases.items():
        if case.get('available') and f'explanations/shap_local_{name}.png' not in artifacts:
            raise ValueError(f'Freeze omits available local SHAP explanation: {name}')
    if require_review:
        receipt = json.loads((path.parent / 'review.json').read_text())
        reviewed = {name: digest for name, digest in artifacts.items()
                    if name not in {'review.json', 'review.md'}}
        if (receipt.get('disposition') != 'PASS' or receipt.get('run_id') != manifest.get('run_id')
                or receipt.get('reviewed_artifacts_sha256') != sha256_bytes(json_bytes(reviewed))
                or receipt.get('review_sha256') != artifacts['review.md']):
            raise ValueError('Independent review does not bind frozen artifacts')
    return manifest


def load_frozen_bundle(path):
    manifest = verify_freeze(path)
    return joblib.load(Path(path).parent / manifest["bundle_path"])
