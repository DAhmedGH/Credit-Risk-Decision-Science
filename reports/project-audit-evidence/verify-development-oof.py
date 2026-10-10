"""Verify preserved Phase 3 bytes and independently recalculate development OOF metrics.

No estimator is loaded/fitted, and no final-test outcomes are read. Requires the
historically preserved runtime explicitly; output is aggregate audit evidence.
"""

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def metrics(frame):
    labels = frame.default_next_month.to_numpy(dtype=int)
    probabilities = frame.p_default.to_numpy(dtype=float)
    if (
        set(labels) != {0, 1}
        or not np.isfinite(probabilities).all()
        or ((probabilities < 0) | (probabilities > 1)).any()
    ):
        raise ValueError("Saved development outcomes/probabilities violate the contract")
    return {
        "average_precision": float(average_precision_score(labels, probabilities)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "log_loss": float(
            log_loss(labels, np.column_stack((1 - probabilities, probabilities)), labels=[0, 1])
        ),
        "brier_score": float(brier_score_loss(labels, probabilities, pos_label=1)),
    }


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--model-root",
    type=Path,
    required=True,
    help="Read-only historically preserved Phase 3 runtime",
)
parser.add_argument("--output", type=Path, required=True, help="New aggregate JSON file")
args = parser.parse_args()
if args.output.exists():
    raise ValueError("Audit output already exists; choose a new file")
root = Path(__file__).resolve().parents[2]
model_root = args.model_root.resolve()
receipt = json.loads((root / "reports/phase3_acceptance.json").read_text())
inventory = root / receipt["preservation_inventory"]["path"]
if digest(inventory) != receipt["preservation_inventory"]["sha256"]:
    raise ValueError("Historical inventory bytes changed")
rows = list(csv.DictReader(inventory.open(newline="")))
started = time.perf_counter()
errors = []
verified_bytes = 0
for row in rows:
    relative = Path(row["relative_path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Unsafe inventory path")
    path = model_root / relative
    if (
        not path.is_file()
        or path.stat().st_size != int(row["bytes"])
        or digest(path) != row["sha256"]
    ):
        errors.append(str(relative))
    else:
        verified_bytes += int(row["bytes"])
if errors:
    raise ValueError(f"Preserved Phase 3 inventory differs: {errors}")

assignments = pd.read_csv(root / "artifacts/split_manifest.csv", keep_default_na=False)
development = assignments.loc[assignments.partition == "development"].set_index("client_id")
reference_labels = None
family_results = []
maximum = 0.0
search_rows = 0
candidate_count = 0
for run in receipt["search_runs"]:
    if run["purpose"] not in {"logistic", "random_forest", "xgboost"}:
        continue
    run_id = run["run_id"]
    output = model_root / "artifacts/models/phase3" / run_id
    search = json.loads((output / "search.json").read_text())
    folds = pd.read_csv(output / "fold_metrics.csv")
    candidates = {row["candidate_id"]: row for row in search["candidates"]}
    for candidate_id, candidate in candidates.items():
        frame = pd.read_csv(output / "oof" / (candidate_id + ".csv"), float_precision="round_trip")
        if (
            not frame.client_id.is_unique
            or len(frame) != len(development)
            or frame.client_id.tolist() != development.index.tolist()
        ):
            raise ValueError("Saved OOF has missing, duplicated, reordered or held-out IDs")
        expected = development.loc[frame.client_id]
        if (
            frame.fingerprint.tolist() != expected.fingerprint.tolist()
            or frame.fold.astype(int).tolist() != expected.fold.astype(int).tolist()
        ):
            raise ValueError("Saved OOF groups/folds disagree with frozen assignments")
        labels = frame.default_next_month.to_numpy(dtype=int)
        if reference_labels is None:
            reference_labels = labels.copy()
        elif not np.array_equal(reference_labels, labels):
            raise ValueError("Saved candidate outcome alignment disagrees")
        fold_values = []
        for fold in range(5):
            actual = metrics(frame.loc[frame.fold == fold])
            recorded = folds.loc[(folds.candidate_id == candidate_id) & (folds.fold == fold)]
            if len(recorded) != 1:
                raise ValueError("Saved fold metric coverage differs")
            for name, value in actual.items():
                discrepancy = abs(value - float(recorded.iloc[0][name]))
                maximum = max(maximum, discrepancy)
                if discrepancy > 1e-12:
                    raise ValueError("Saved OOF fold metric differs")
            fold_values.append(actual)
        pooled = metrics(frame)
        for name, value in pooled.items():
            for field, actual in (
                (name + "_pooled_oof", value),
                (name + "_mean", float(np.mean([r[name] for r in fold_values]))),
                (name + "_std", float(np.std([r[name] for r in fold_values], ddof=1))),
            ):
                discrepancy = abs(actual - float(candidate[field]))
                maximum = max(maximum, discrepancy)
                if discrepancy > 1e-12:
                    raise ValueError("Saved candidate pooled/fold summary differs")
        candidate_count += 1
        search_rows += len(frame)
    family_results.append(
        {
            "run_id": run_id,
            "model": search["model"],
            "candidates": len(candidates),
            "cv_fits_recorded": search["fit_count"],
        }
    )

result = {
    "inventory_sha256": digest(inventory),
    "inventory_files_verified": len(rows),
    "inventory_bytes_verified": verified_bytes,
    "inventory_extensions": dict(Counter(Path(row["relative_path"]).suffix for row in rows)),
    "search_runs": family_results,
    "search_candidates_verified": candidate_count,
    "saved_development_oof_rows_verified": search_rows,
    "development_rows_per_candidate": len(development),
    "fold_metric_cells_verified": candidate_count * 5 * 4,
    "pooled_metric_cells_verified": candidate_count * 4,
    "candidate_mean_std_cells_verified": candidate_count * 4 * 2,
    "maximum_metric_absolute_difference": maximum,
    "model_loading": False,
    "fits": 0,
    "final_test_outcomes_read": False,
    "label_alignment_scope": "Saved development outcomes agree across all candidates; no raw-label reread",
    "runtime_seconds": time.perf_counter() - started,
}
with args.output.open("x") as stream:
    stream.write(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
