"""Independently verify accepted Phase 2 artifact bytes and development OOF metrics."""

if not __debug__:
    raise RuntimeError("Run this audit check without Python -O; assertions verify integrity")

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def metrics(frame):
    y = frame.default_next_month.to_numpy(dtype=int)
    p = frame.p_default.to_numpy(dtype=float)
    assert set(y) == {0, 1} and np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
    return {
        "average_precision": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "log_loss": float(log_loss(y, np.column_stack((1 - p, p)), labels=[0, 1])),
        "brier_score": float(brier_score_loss(y, p, pos_label=1)),
    }


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True, help="New aggregate JSON file")
args = parser.parse_args()
if args.output.exists():
    raise ValueError("Audit output already exists; choose a new file")
root = Path(__file__).resolve().parents[2]
run_id = "49c7344ca89440e9a458fa2849d9122d"
manifest = json.loads((root / "reports/phase2_runs" / run_id / "manifest.json").read_text())
for relative, expected_digest in manifest["artifacts"].items():
    assert digest(root / relative) == expected_digest, relative
assignments = pd.read_csv(root / "artifacts/split_manifest.csv", keep_default_na=False)
development = assignments.loc[assignments.partition == "development"].set_index("client_id")
maximum = 0.0
reference = None
results = []
for directory in sorted((root / "artifacts/models/phase2" / run_id).iterdir()):
    if not directory.is_dir():
        continue
    frame = pd.read_csv(directory / "oof_predictions.csv", float_precision="round_trip")
    assert frame.client_id.is_unique and len(frame) == len(development)
    assert frame.client_id.tolist() == development.index.tolist()
    expected = development.loc[frame.client_id]
    assert frame.fingerprint.tolist() == expected.fingerprint.tolist()
    assert frame.fold.tolist() == expected.fold.astype(int).tolist()
    if reference is None:
        reference = frame.default_next_month.to_numpy().copy()
    else:
        assert np.array_equal(reference, frame.default_next_month.to_numpy())
    folded = pd.read_csv(directory / "fold_metrics.csv")
    summary = json.loads((directory / "summary.json").read_text())
    values = []
    for fold in range(5):
        actual = metrics(frame.loc[frame.fold == fold])
        recorded = folded.loc[folded.fold == fold]
        assert len(recorded) == 1
        for name, value in actual.items():
            discrepancy = abs(value - float(recorded.iloc[0][name]))
            maximum = max(maximum, discrepancy)
            assert discrepancy <= 1e-12
        values.append(actual)
    for name, value in metrics(frame).items():
        for field, actual in (
            (name + "_pooled_oof", value),
            (name + "_mean", float(np.mean([r[name] for r in values]))),
            (name + "_std", float(np.std([r[name] for r in values], ddof=1))),
        ):
            discrepancy = abs(actual - float(summary[field]))
            maximum = max(maximum, discrepancy)
            assert discrepancy <= 1e-12
    results.append(directory.name)
assert len(results) == 9
result = {
    "run_id": run_id,
    "artifact_hashes_verified": len(manifest["artifacts"]),
    "variants": results,
    "saved_development_oof_rows_verified": 9 * len(development),
    "fold_metric_cells_verified": 9 * 5 * 4,
    "pooled_metric_cells_verified": 9 * 4,
    "mean_std_metric_cells_verified": 9 * 4 * 2,
    "maximum_metric_absolute_difference": maximum,
    "fits": 0,
    "model_loading": False,
    "final_test_outcomes_read": False,
    "label_alignment_scope": "Saved development outcomes agree across all baseline variants; no raw-label reread",
}
with args.output.open("x") as stream:
    stream.write(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
