"""Fixture evidence for held-out calibration, selection, and fail-closed freezing."""

import copy
import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from credit_risk.artifacts import file_sha256, json_bytes, sha256_bytes, write_json
from credit_risk.models.bundle import ProbabilityBundle, load_frozen_bundle, verify_freeze
from credit_risk.models.calibration import fit_mappings, select_mapping, reliability_bins, verify_fit_scope
from credit_risk.models.phase4_inputs import routed_partitions
from credit_risk.models.pipelines import positive_probability
from credit_risk.features import PREDICTORS, build_features
from credit_risk.splits import allocate_records
from credit_risk.artifacts import write_csv
from fixtures.records import make_records


@pytest.fixture
def calibrated():
    rng = np.random.default_rng(42)
    X = pd.DataFrame(rng.normal(size=(120, 2)), columns=['a', 'b'])
    y = (X.a + rng.normal(size=120) > 0).astype(int)
    base = make_pipeline(StandardScaler(), LogisticRegression()).fit(X.iloc[:60], y.iloc[:60])
    before = joblib.hash(base)
    variants = fit_mappings(base, X.iloc[60:100], y.iloc[60:100], partition='calibration',
                            calibration_ids=list(range(60, 100)), development_ids=list(range(60)))
    return base, variants, X, y, before


def test_frozen_api_preserves_base_and_preprocessing(calibrated):
    base, variants, X, _, before = calibrated
    assert joblib.hash(base) == before
    for method in ('sigmoid', 'isotonic'):
        mapped = variants[method]
        assert len(mapped.calibrated_classifiers_) == 1
        assert mapped.estimator.estimator is base
        assert np.array_equal(positive_probability(base, X),
                              positive_probability(mapped.estimator, X))
        p = positive_probability(mapped, X.iloc[100:])
        assert np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()


def test_mapping_fit_rejects_incorrect_scope(calibrated):
    base, _, X, y, _ = calibrated
    for partition, ids in [('policy_validation', list(range(60, 100))),
                           ('calibration', list(range(40)))]:
        with pytest.raises(ValueError):
            fit_mappings(base, X.iloc[60:100], y.iloc[60:100], partition=partition,
                         calibration_ids=ids, development_ids=list(range(60)))
    with pytest.raises(ValueError, match='overlap'):
        verify_fit_scope([1], [2], [3], [1, 4])
    verify_fit_scope([1], [2], [3], [4])


def test_mapping_selection_boundary_and_order():
    def scores(a,b,c):
        return dict(zip(('raw', 'sigmoid', 'isotonic'), [{'log_loss': x} for x in (a,b,c)], strict=True))
    assert select_mapping(scores(.425, .424, .420)) == 'raw'
    assert select_mapping(scores(.4251, .424, .420)) == 'sigmoid'
    assert select_mapping(scores(.427, .426, .420)) == 'isotonic'
    with pytest.raises(ValueError):
        select_mapping(scores(.425, .424, .420), partition='final_test')
    with pytest.raises(ValueError):
        select_mapping(scores(.425, .424, float('nan')))


def test_fixed_bins_endpoints_empty_and_sparse():
    bins = reliability_bins([0, 1, 1], [0, .1, 1])
    assert sum(row['count'] for row in bins) == 3
    assert bins[0]['count'] == bins[1]['count'] == bins[9]['count'] == 1
    assert bins[2]['observed_rate'] is None and bins[2]['sparse']


class ReversedClassifier(ClassifierMixin, BaseEstimator):
    classes_ = np.array([1, 0])

    def predict_proba(self, X):
        return np.tile([.7, .3], (len(X), 1))


def test_probability_class_lookup():
    assert np.all(positive_probability(ReversedClassifier(), np.zeros((4, 1))) == .7)


def test_serialized_bundle_and_tamper_guard(calibrated, tmp_path):
    base, variants, X, _, _ = calibrated
    bundle = ProbabilityBundle(base, variants['sigmoid'], 'sigmoid', {}, {}, {}, {})
    target = tmp_path / 'bundle.joblib'
    joblib.dump(bundle, target)
    assert np.array_equal(bundle.predict_probability(X), joblib.load(target).predict_probability(X))
    required = {'feature_schema.json', 'policy.json', 'model_metadata.json',
                'report_definitions.json', 'calibration_fit_evidence.json',
                'serialization_evidence.json', 'model_card.md', 'explanations/metadata.json',
                'explanations/shap_values.npz', 'explanations/shap_global.png',
                'explanations/shap_dependence_1.png', 'explanations/shap_dependence_2.png'}
    for candidate in ('dummy_prior', 'logistic_00_engineered_none',
                      'random_forest_02_engineered_none', 'xgboost_04_engineered_none',
                      'xgboost_05_engineered_none'):
        required.update({f'accepted_models/{candidate}/development_pipeline.joblib',
                         f'accepted_models/{candidate}/metadata.json'})
    for name in required:
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('fixture')
    write_json(tmp_path / 'explanations/metadata.json', {'diagnostic_cases': {
        name: {'available': False} for name in
        ('correct_default', 'correct_nondefault', 'missed_default', 'false_alarm')}})
    artifacts = {name: file_sha256(tmp_path / name) for name in required}
    artifacts['bundle.joblib'] = file_sha256(target)
    write_json(tmp_path / 'review.json', {'run_id': 'fixture', 'disposition': 'PASS',
               'reviewed_artifacts_sha256': sha256_bytes(json_bytes(artifacts)),
               'review_sha256': sha256_bytes(b'fixture review')})
    (tmp_path / 'review.md').write_bytes(b'fixture review')
    artifacts.update({'review.json': file_sha256(tmp_path / 'review.json'),
                      'review.md': file_sha256(tmp_path / 'review.md')})
    manifest = {'run_id': 'fixture', 'bundle_path': 'bundle.joblib', 'complete_bundle_frozen': True,
                'explanations_complete': True, 'independent_review_status': 'PASS',
                'artifacts': artifacts, 'report_definitions_sha256': artifacts['report_definitions.json']}
    def save(value):
        value = copy.deepcopy(value)
        value['freeze_sha256'] = sha256_bytes(json_bytes(value))
        write_json(tmp_path / 'freeze.json', value)
    save(manifest)
    assert np.array_equal(load_frozen_bundle(tmp_path / 'freeze.json').predict_probability(X),
                          bundle.predict_probability(X))
    for name, bad in [('complete_bundle_frozen', False), ('explanations_complete', False),
                      ('independent_review_status', 'PENDING')]:
        save({**manifest, name: bad})
        with pytest.raises(ValueError):
            verify_freeze(tmp_path / 'freeze.json')
    for omitted in ('bundle.joblib', 'report_definitions.json', 'policy.json',
                    'accepted_models/dummy_prior/development_pipeline.joblib'):
        missing = {**manifest, 'artifacts': {name: value for name, value in artifacts.items() if name != omitted}}
        save(missing)
        with pytest.raises(ValueError, match='omits'):
            verify_freeze(tmp_path / 'freeze.json')
    save({**manifest, 'report_definitions_sha256': '0' * 64})
    with pytest.raises(ValueError, match='Report'):
        verify_freeze(tmp_path / 'freeze.json')
    save({**manifest, 'artifacts': {**artifacts, '../unsafe': '0' * 64}})
    with pytest.raises(ValueError, match='safe relative'):
        verify_freeze(tmp_path / 'freeze.json')
    save(manifest)
    changed = json.loads((tmp_path / 'freeze.json').read_text())
    changed['bundle_path'] = 'other.joblib'
    write_json(tmp_path / 'freeze.json', changed)
    with pytest.raises(ValueError, match='identity'):
        verify_freeze(tmp_path / 'freeze.json')
    save(manifest)
    target.write_bytes(b'tampered')
    with pytest.raises(ValueError, match='changed'):
        verify_freeze(tmp_path / 'freeze.json')


def test_final_test_sentinels_never_interpreted(tmp_path):
    records = make_records(200)
    assignments, _ = allocate_records(records, 'a' * 64)
    forbidden = {int(row['client_id']) for row in assignments if row['partition'] == 'final_test'}
    policy_ids = {int(row['client_id']) for row in assignments if row['partition'] == 'policy_validation'}
    financial, labels, audits = [], [], []
    for row in records:
        identifier = row['client_id']
        financial.append({'client_id': identifier, **build_features(row)})
        labels.append({'client_id': identifier, 'default_next_month': row['default_next_month']})
        audits.append({'client_id': identifier, **{name: row[name] for name in ('sex','age','education','marriage')},
                       'sex_group': 'group', 'education_group': 'group', 'marriage_group': 'group'})
        if identifier in forbidden:
            financial[-1].update({name: 'SEALED' for name in PREDICTORS})
            labels[-1]['default_next_month'] = 'SEALED'
        if identifier not in policy_ids:
            audits[-1].update({name: 'SEALED' for name in ('sex', 'age', 'education', 'marriage')})
    folder = tmp_path / 'data/processed'
    folder.mkdir(parents=True)
    write_csv(folder / 'financial_features_v1.csv', financial, ('client_id', *PREDICTORS))
    write_csv(folder / 'labels.csv', labels, ('client_id', 'default_next_month'))
    write_csv(folder / 'audit_attributes.csv', audits, tuple(audits[0]))
    parts = routed_partitions(tmp_path, assignments)
    assert set(parts) == {'development', 'calibration', 'policy_validation'}
    assert sum(map(len, parts.values())) == 170
    assert not any(set(frame.client_id) & forbidden for frame in parts.values())


def test_finalize_refuses_pending_explanations(tmp_path, monkeypatch):
    from credit_risk import phase4
    monkeypatch.setattr(phase4, '_verify_checkpoint', lambda _: {'explanations_complete': False})
    with pytest.raises(ValueError, match='SHAP'):
        phase4.finalize(tmp_path, tmp_path, tmp_path / 'does-not-exist.json')


@pytest.mark.parametrize('tamper', ['content_hash', 'scientific_identity'])
def test_finalize_does_not_legitimize_edited_manifest(tmp_path, monkeypatch, tamper):
    from credit_risk import phase4
    artifacts = {'fixture.txt': sha256_bytes(b'fixture')}
    state = {'explanations_complete': True, 'blockers': [], 'run_id': 'fixture',
             'artifacts': artifacts, 'completion_context': {}, 'integrity': {},
             'config': {'model_root': 'unused'}, 'selected_mapping': 'raw'}
    monkeypatch.setattr(phase4, '_verify_checkpoint', lambda _: copy.deepcopy(state))
    monkeypatch.setattr(phase4, 'source_context', lambda _: {})
    monkeypatch.setattr(phase4, 'accepted_integrity', lambda *args: (None, None, None, {}))
    review = tmp_path / 'review.md'
    review.write_text('Independent fixture review')
    receipt = {'run_id': 'fixture', 'disposition': 'PASS',
               'reviewed_artifacts_sha256': sha256_bytes(json_bytes(artifacts)),
               'review_path': str(review), 'review_sha256': file_sha256(review)}
    write_json(tmp_path / 'receipt.json', receipt)
    frozen = {'run_id': 'fixture', 'selected_mapping': 'sigmoid', 'integrity': {},
              'artifacts': artifacts}
    frozen['freeze_sha256'] = sha256_bytes(json_bytes(frozen))
    if tamper == 'content_hash':
        frozen['selected_mapping'] = 'isotonic'
    write_json(tmp_path / 'freeze_manifest.json', frozen)
    expected = 'content identity' if tamper == 'content_hash' else 'scientific identity'
    with pytest.raises(ValueError, match=expected):
        phase4.finalize(tmp_path, tmp_path, tmp_path / 'receipt.json')


def test_resume_cannot_unfreeze_completed_bundle(tmp_path, monkeypatch):
    from credit_risk import phase4
    write_json(tmp_path / 'freeze_manifest.json', {'complete_bundle_frozen': True})
    monkeypatch.setattr(phase4, 'accepted_integrity', lambda *args: pytest.fail('read real inputs'))
    with pytest.raises(ValueError, match='completed frozen'):
        phase4.explanations_and_freeze(tmp_path, tmp_path)
