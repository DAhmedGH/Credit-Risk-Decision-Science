"""No-fit provenance tests: reuse must not silently change modeling evidence."""

import copy

import pytest

from credit_risk.artifacts import json_bytes, sha256_bytes
from credit_risk.phase3 import validate_search_reuse


RUNNER = '''
XGB_PIN = "3.0.5"
def _inputs(config, root, stage):
    return ["development"], {}
def _fit_development(pipeline, X, y):
    return pipeline.fit(X, y)
def select(run_ids):
    records, hashes = _inputs({}, None, "development")
    candidates = [0]
    chosen = candidates[0]
    client, _, run_id = _tracker()
    try:
        frame = records
        X, y = frame, [0, 1]
        for candidate_id, candidate in {}.items():
            pipeline = _fit_development(candidate, X, y)
            metadata = {"role": "reference"}
        return chosen
    except Exception:
        raise
'''


def rehash(context):
    context["code_tree_sha256"] = sha256_bytes(json_bytes(context["code_file_hashes"]))
    context["dependency_lock_sha256"] = context["code_file_hashes"]["requirements.lock"]


@pytest.fixture
def contexts(tmp_path):
    snapshot = tmp_path / "provenance/original_code/src/credit_risk/phase3.py"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text(RUNNER)
    current = tmp_path / "src/credit_risk/phase3.py"
    current.parent.mkdir(parents=True)
    current.write_text(RUNNER + "\ndef provenance_only_guard():\n    return True\n")
    old_lock = "numpy==2.2.6\nscikit-learn==1.7.2\n"
    new_lock = old_lock + "xgboost-cpu==3.0.5\n"
    (tmp_path / "requirements.lock").write_text(new_lock)
    files = {"src/credit_risk/phase3.py": sha256_bytes(RUNNER.encode()),
             "src/credit_risk/models/pipelines.py": "a" * 64,
             "configs/phase3.toml": "b" * 64, "requirements.lock": sha256_bytes(old_lock.encode())}
    source = {"parent_run_id": "1" * 32, "model": "logistic", "code_file_hashes": files,
              "plan_sha256": "d" * 64, "input_hashes": {"fixture_only": "e" * 64},
              "config_sha256": "b" * 64, "config": {"seed": 42}, "python": "3.12.11",
              "platform": "synthetic-fixture-only", "seed": 42, "threads": 1, "positive_class": 1,
              "dependencies": {"numpy": "2.2.6", "scikit-learn": "1.7.2"}}
    rehash(source)
    target = copy.deepcopy(source)
    target["model"] = "xgboost"
    target["dependencies"]["xgboost-cpu"] = "3.0.5"
    target["code_file_hashes"]["requirements.lock"] = sha256_bytes(new_lock.encode())
    target["code_file_hashes"]["src/credit_risk/phase3.py"] = sha256_bytes(current.read_bytes())
    rehash(target)
    return source, target, tmp_path


def test_reuse_records_original_and_current_provenance_without_new_fits(contexts):
    source, target, root = contexts
    before = copy.deepcopy(source)
    proof = validate_search_reuse(source, target, root)
    assert proof["mode"] == "verified_additive_xgboost_orchestration"
    assert proof["added_dependencies"] == {"xgboost-cpu": "3.0.5"}
    assert proof["additional_search_fits"] == 0
    assert proof["original_dependencies"] != proof["current_dependencies"]
    assert source == before
    assert validate_search_reuse(source, source, root)["mode"] == "identical"


@pytest.mark.parametrize("change", ["upgrade", "remove", "unlisted", "wrong_xgboost"])
def test_reuse_rejects_changed_or_unlisted_dependencies(contexts, change):
    source, target, root = contexts
    if change == "upgrade":
        target["dependencies"]["numpy"] = "9.0"
    elif change == "remove":
        del target["dependencies"]["scikit-learn"]
    elif change == "unlisted":
        target["dependencies"]["unreviewed-package"] = "1.0"
    else:
        target["dependencies"]["xgboost-cpu"] = "9.0"
    with pytest.raises(ValueError, match="dependency"):
        validate_search_reuse(source, target, root)


@pytest.mark.parametrize("field", ["plan_sha256", "input_hashes", "config_sha256", "python"])
def test_reuse_rejects_changed_scientific_contract(contexts, field):
    source, target, root = contexts
    target[field] = "changed"
    with pytest.raises(ValueError, match=field):
        validate_search_reuse(source, target, root)


def test_reuse_rejects_changed_model_source_and_missing_original_snapshot(contexts):
    source, target, root = contexts
    target["code_file_hashes"]["src/credit_risk/models/pipelines.py"] = "0" * 64
    rehash(target)
    with pytest.raises(ValueError, match="numerical or unlisted"):
        validate_search_reuse(source, target, root)
    target["code_file_hashes"]["src/credit_risk/models/pipelines.py"] = "a" * 64
    rehash(target)
    (root / "provenance/original_code/src/credit_risk/phase3.py").unlink()
    with pytest.raises(ValueError, match="snapshot"):
        validate_search_reuse(source, target, root)


@pytest.mark.parametrize("before,after", [
    ("pipeline.fit(X, y)", "pipeline.fit(X[:1], y[:1])"),
    ("candidates = [0]", "candidates = [1]"),
    ("frame = records", "frame = records[:1]"),
    ("X, y = frame, [0, 1]", "X, y = frame[:1], [0]"),
    ('_inputs({}, None, "development")', '_inputs({}, None, "heldout")'),
])
def test_runner_allowance_cannot_change_selection_data_or_final_fit(contexts, before, after):
    source, target, root = contexts
    current = root / "src/credit_risk/phase3.py"
    current.write_text(current.read_text().replace(before, after))
    target["code_file_hashes"]["src/credit_risk/phase3.py"] = sha256_bytes(current.read_bytes())
    rehash(target)
    with pytest.raises(ValueError, match="protected runner|selection or numerical"):
        validate_search_reuse(source, target, root)


def test_reuse_rejects_unaccounted_lock_change_or_invalid_fingerprint(contexts):
    source, target, root = contexts
    del target["dependencies"]["xgboost-cpu"]
    with pytest.raises(ValueError, match="lock change"):
        validate_search_reuse(source, target, root)
    target["code_tree_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprints"):
        validate_search_reuse(source, target, root)


def test_xgboost_addition_requires_current_lock_with_every_installed_pin(contexts):
    source, target, root = contexts
    target["code_file_hashes"]["requirements.lock"] = source["dependency_lock_sha256"]
    rehash(target)
    with pytest.raises(ValueError, match="updated validated lock"):
        validate_search_reuse(source, target, root)
    (root / "requirements.lock").write_text("xgboost-cpu==3.0.5\n")
    target["code_file_hashes"]["requirements.lock"] = sha256_bytes((root / "requirements.lock").read_bytes())
    rehash(target)
    with pytest.raises(ValueError, match="installed dependency pins"):
        validate_search_reuse(source, target, root)
