"""Independent saved-evidence check, no fitting, source outcomes or evaluation."""

import argparse
from pathlib import Path
from collections import defaultdict
import json
import hashlib
import time
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score, log_loss

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, help="Optional new aggregate JSON output file")
args = parser.parse_args()
if args.output is not None and args.output.exists():
    raise ValueError("Audit output already exists; choose a new file")
root = Path(__file__).resolve().parents[2]
model = root / "artifacts/models/phase4/9ca62eca2665438c9c97b4889413acfa"
frame = pd.read_csv(
    root / "artifacts/runtime/phase5/final_evaluation/predictions.csv", float_precision="round_trip"
)
original = json.loads((root / "reports/phase5/results.json").read_text())
policy = json.loads((model / "policy.json").read_text())
y = frame.default_next_month.to_numpy(dtype=int)
models = {name: frame[name].to_numpy(dtype=float) for name in original["model_metrics"]}
metrics = ("average_precision", "roc_auc", "log_loss", "brier_score")


def probability_metrics(labels, p):
    return dict(
        zip(
            metrics,
            [
                average_precision_score(labels, p),
                roc_auc_score(labels, p),
                log_loss(labels, np.c_[1 - p, p], labels=[0, 1]),
                np.mean((labels - p) ** 2),
            ],
        )
    )


cells = [
    dict(
        scenario=dict(scenario_id="base", gain=50, loss=500, cost=0),
        policies=policy["base_policies"],
    ),
    *policy["sensitivity"]["scenarios"],
]
specs = {}
for cell in cells:
    for definition in cell["policies"]:
        s = cell["scenario"]
        kind = definition["kind"]
        cutoff = definition["cutoff"]
        mask = (
            np.ones(len(y), bool)
            if kind == "all"
            else np.zeros(len(y), bool)
            if kind == "none"
            else models["selected_bundle"] < cutoff
        )
        specs[s["scenario_id"] + "/" + definition["policy_id"]] = (s, mask)
samples = defaultdict(list)
indices_hash = hashlib.sha256()
unique = np.unique(frame.fingerprint)
members = [np.flatnonzero(frame.fingerprint.to_numpy() == group) for group in unique]
rng = np.random.default_rng(42)
started = time.perf_counter()
for repetition in range(1000):
    indices = np.concatenate([members[k] for k in rng.integers(0, len(unique), len(unique))])
    indices_hash.update(np.asarray(indices, dtype="<i8").tobytes())
    yy = y[indices]
    current = {name: probability_metrics(yy, p[indices]) for name, p in models.items()}
    for name, row in current.items():
        for metric, value in row.items():
            samples[f"model/{name}/{metric}"].append(value)
            if name != "selected_bundle":
                samples[f"model_difference/selected_bundle-minus-{name}/{metric}"].append(
                    current["selected_bundle"][metric] - value
                )
    utility = {}
    for key, (s, mask) in specs.items():
        accept = mask[indices]
        n = accept.sum()
        bad = yy[accept].sum()
        u = ((n - bad) * s["gain"] - bad * s["loss"] - n * s["cost"]) / len(indices)
        utility[key] = u
        for metric, value in [
            ("benchmark_utility_per_customer", u),
            ("acceptance_rate", n / len(indices)),
            ("accepted_default_rate", bad / n if n else None),
        ]:
            samples[f"policy/{key}/{metric}"].append(value)
    for cell in cells:
        sid = cell["scenario"]["scenario_id"]
        for ref in ("analytic", "accept_all", "abstain_all"):
            samples[f"policy_difference/{sid}/empirical-minus-{ref}"].append(
                utility[sid + "/empirical"] - utility[sid + "/" + ref]
            )
errors = []
maximum = 0
for key, values in samples.items():
    valid = np.asarray([v for v in values if v is not None and np.isfinite(v)])
    expected = original["intervals"][key]
    limits = np.percentile(valid, [2.5, 97.5]) if len(valid) else [None, None]
    for label, actual in zip(("lower", "upper"), limits):
        saved = expected[label]
        if actual is None:
            if saved is not None:
                errors.append(key + "/" + label)
        else:
            maximum = max(maximum, abs(actual - saved))
            if abs(actual - saved) > 1e-12:
                errors.append(key + "/" + label)
    if expected["valid_repetitions"] != len(valid) or expected[
        "undefined_repetitions"
    ] != 1000 - len(valid):
        errors.append(key + "/counts")
result = dict(
    statistics=len(samples),
    interval_max_absolute_difference=maximum,
    errors=errors,
    groups=len(unique),
    seed=42,
    repetitions=1000,
    paired=True,
    resample_indices_sha256=indices_hash.hexdigest(),
    plan_hash_matches=indices_hash.hexdigest() == original["bootstrap"]["resample_indices_sha256"],
    seconds=time.perf_counter() - started,
)
if args.output is not None:
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))

if errors or not result["plan_hash_matches"]:
    raise SystemExit("Saved bootstrap evidence does not match independent reconstruction")
