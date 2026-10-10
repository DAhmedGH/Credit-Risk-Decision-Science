"""Synthetic policy-validation monitoring; no fitting or final-test access.

Callers supply already routed development/policy-validation frames and a trusted,
verified bundle. PSI warnings are configurable demonstration heuristics, not
concept-drift evidence. Customer-level sampling receipts stay in ignored runtime.
"""
from __future__ import annotations

from collections import Counter
from html import escape
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from credit_risk.data.schema import BILL_COLUMNS, RAW_PREDICTORS, STATUS_COLUMNS
from credit_risk.features import PREDICTORS, feature_contract
from credit_risk.inference import validate_batch

EPSILON = 1e-6
PSI_WARNING_THRESHOLD = 0.2
MISSING_WARNING_THRESHOLD = 0.05


def distribution_bins(values):
    """Finite development deciles, retaining min/max for explicit tail bins."""
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    return np.unique(np.quantile(finite, np.linspace(0, 1, 11))) if len(finite) else np.array([])


def distribution_counts(values, edges):
    """Counts: underflow, development intervals, overflow, missing.

    Upper boundary belongs to the final interior bin, including constant data.
    Empty-development support puts all finite observations in overflow.
    """
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if not len(edges):
        return np.array([0, len(finite), len(values) - len(finite)], dtype=int)
    under, over = finite < edges[0], finite > edges[-1]
    interior = finite[~(under | over)]
    n = max(1, len(edges) - 1)
    indexes = np.clip(np.searchsorted(edges, interior, side='right') - 1, 0, n - 1)
    return np.r_[under.sum(), np.bincount(indexes, minlength=n), over.sum(),
                 len(values) - len(finite)].astype(int)


def population_stability_index(reference, current):
    """Add epsilon to every proportion, then renormalize both distributions."""
    reference, current = np.asarray(reference, float), np.asarray(current, float)
    if reference.shape != current.shape or (reference < 0).any() or (current < 0).any():
        raise ValueError('PSI requires matching nonnegative count arrays')
    if reference.sum() == 0 or current.sum() == 0:
        return None
    p = reference / reference.sum() + EPSILON
    q = current / current.sum() + EPSILON
    p, q = p / p.sum(), q / q.sum()
    return float(np.sum((q - p) * np.log(q / p)))


def _features(frame, vocabularies):
    # Resampling repeats customer IDs and can repeat dataframe indexes. Scorer
    # identities refer to input positions, never source customer identities.
    raw = frame.loc[:, [c for c in RAW_PREDICTORS if c in frame.columns]].reset_index(drop=True)
    batch = raw.copy(deep=True)
    batch.insert(0, 'record_id', [f'monitoring-{i}' for i in range(len(batch))])
    accepted, positions, rejected = validate_batch(batch)
    valid = np.zeros(len(frame), dtype=bool)
    valid[positions] = True
    missing = raw.isna() | raw.eq('')
    numeric = raw.mask(missing).apply(pd.to_numeric, errors='coerce')
    nonnumeric = ~missing & numeric.isna()
    nonfinite = numeric.notna() & ~np.isfinite(numeric)
    unknown = {column: int((numeric[column].notna() & np.isfinite(numeric[column])
                           & numeric[column].mod(1).eq(0)
                           & ~numeric[column].isin(vocabularies[column])).sum())
               for column in STATUS_COLUMNS}
    # Raw diagnostics retain rejected financial values; derived features exist
    # only for scorer-valid rows, avoiding a second, divergent feature builder.
    features = pd.DataFrame(np.nan, index=range(len(frame)), columns=PREDICTORS)
    features.loc[:, list(RAW_PREDICTORS)] = numeric.to_numpy()
    features.iloc[positions] = accepted.to_numpy()
    quality = {'rows': len(frame), 'missing_columns': [],
               'missing_counts': {c: int(missing[c].sum()) for c in RAW_PREDICTORS},
               'missing_rates': {c: float(missing[c].mean()) for c in RAW_PREDICTORS},
               'nonnumeric_counts': {c: int(nonnumeric[c].sum()) for c in RAW_PREDICTORS},
               'nonfinite_counts': {c: int(nonfinite[c].sum()) for c in RAW_PREDICTORS},
               'unknown_category_counts': unknown,
               'unknown_category_rate': sum(unknown.values()) / (len(frame) * len(STATUS_COLUMNS)),
               'schema_valid_rows': len(positions), 'quarantined_rows': len(rejected),
               'quarantine_reason_counts': dict(Counter(row['reason'] for row in rejected)),
               'counts_reconcile': len(positions) + len(rejected) == len(frame)}
    return features, valid, quality


def _probabilities(bundle, features, valid):
    result = np.full(len(features), np.nan)
    if valid.any():
        probability = np.asarray(bundle.predict_probability(features.loc[valid]), float)
        if (probability.shape != (int(valid.sum()),) or not np.isfinite(probability).all()
                or (probability < 0).any() or (probability > 1).any()):
            raise ValueError('Bundle returned invalid default probabilities')
        result[valid] = probability
    return result


def _metrics(frame, probabilities):
    if 'default_next_month' not in frame:
        return None
    labels = frame.default_next_month
    if labels.isna().any() or not labels.isin([0, 1]).all():
        raise ValueError('Available monitoring labels must be binary and nonmissing')
    valid = np.isfinite(probabilities)
    y, p = labels.to_numpy()[valid], probabilities[valid]
    if not len(y):
        return {'rows': 0, 'AP': None, 'ROC_AUC': None, 'log_loss': None, 'Brier': None}
    both = len(np.unique(y)) == 2
    return {'rows': len(y), 'AP': float(average_precision_score(y, p)) if both else None,
            'ROC_AUC': float(roc_auc_score(y, p)) if both else None,
            'log_loss': float(log_loss(y, p, labels=[0, 1])),
            'Brier': float(brier_score_loss(y, p))}


def monitoring_report(bundle, development: pd.DataFrame, policy_validation: pd.DataFrame,
                      output_dir: Path):
    """Save aggregate JSON/CSV/SVG and ignored customer-level sampling receipts.

    Inputs require unique, disjoint client_id values and normalized raw financial
    fields. Extra derived/audit columns are ignored; development labels are never
    used. The caller remains responsible for partition routing/freeze verification.
    Returns JSON-safe data. No estimator or accepted artifact is mutated.
    """
    output_dir = Path(output_dir)
    project_root = Path(__file__).resolve().parents[2]
    if output_dir.resolve().is_relative_to((project_root / 'artifacts/models').resolve()):
        raise ValueError('Monitoring output must not mutate accepted model artifacts')
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise ValueError('Monitoring output must be new or an empty directory')
    if bundle.feature_schema != feature_contract():
        raise ValueError('Bundle feature contract differs from monitoring formulas')
    for frame in (development, policy_validation):
        if (not frame.columns.is_unique or frame.empty or 'client_id' not in frame
                or frame.client_id.isna().any() or not frame.client_id.is_unique):
            raise ValueError('Monitoring inputs require nonempty frames and unique source IDs')
    if set(development.client_id) & set(policy_validation.client_id):
        raise ValueError('Development and policy-validation IDs overlap')
    if 'default_next_month' in policy_validation:
        labels = policy_validation.default_next_month
        if labels.isna().any() or not labels.isin([0, 1]).all():
            raise ValueError('Available monitoring labels must be binary and nonmissing')
    runtime_root = project_root / 'artifacts/runtime/monitoring'
    identity = hashlib.sha256(pd.util.hash_pandas_object(
        policy_validation, index=True).to_numpy().tobytes()
        + str(output_dir.resolve()).encode()).hexdigest()[:16]
    runtime = runtime_root / identity
    if runtime.exists() or runtime.is_symlink():
        raise ValueError('Monitoring customer receipts already exist; choose a new output directory')
    preprocessor = bundle.base.named_steps['preprocessor']
    encoder = preprocessor.named_transformers_['categorical'].named_steps['encoder']
    vocab = dict(zip(STATUS_COLUMNS, encoder.categories_, strict=True))
    dev, dev_valid, dev_quality = _features(development, vocab)
    pv, pv_valid, _ = _features(policy_validation, vocab)
    if not dev_valid.all() or not pv_valid.all():
        raise ValueError('Source scenarios require schema-valid unchanged financial histories')
    dev_risk = _probabilities(bundle, dev, dev_valid)
    q75 = dev.latest_utilization_proxy.quantile(0.75)
    if not np.isfinite(q75):
        raise ValueError('Development utilization Q75 is undefined')
    scenarios = {'reference': policy_validation.copy(deep=True)}
    receipts = []
    sampling = {}
    for name, subgroup in (
        ('financial_mix_shift', pv.latest_utilization_proxy >= q75),
        ('delinquency_mix_shift', (pv[list(STATUS_COLUMNS)] > 0).any(axis=1)),
    ):
        weights = np.where(subgroup, 3.0, 1.0)
        probabilities = weights / weights.sum()
        positions = np.random.default_rng(42).choice(len(pv), 3000, replace=True, p=probabilities)
        scenarios[name] = policy_validation.iloc[positions].reset_index(drop=True).copy(deep=True)
        counts = np.bincount(positions, minlength=len(pv))
        for i, identifier in enumerate(policy_validation.client_id):
            receipts.append({'scenario': name, 'source_position': i, 'client_id': identifier,
                             'weight': weights[i], 'probability': probabilities[i],
                             'sampled_count': counts[i]})
        sampling[name] = {'rows': 3000, 'source_rows': len(pv),
                          'subgroup_source_rows': int(subgroup.sum()),
                          'subgroup_sampled_rows': int(subgroup.iloc[positions].sum()),
                          'unique_sampled_sources': int((counts > 0).sum())}
        # Draw order is a customer-level receipt, separate from aggregate outputs.
        sampling[name]['positions'] = positions
    altered = {}
    positions = np.random.default_rng(42).choice(len(pv), max(1, len(pv) // 10), replace=False)
    for name, column, value in (
        ('corruption_missing', BILL_COLUMNS[-1], np.nan),
        ('corruption_nonnumeric', BILL_COLUMNS[-1], 'not-a-number'),
        ('corruption_unseen_status', STATUS_COLUMNS[-1],
         max(10, int(max(vocab[STATUS_COLUMNS[-1]], default=9)) + 1)),
    ):
        frame = policy_validation.drop(columns='default_next_month', errors='ignore').copy(deep=True)
        if isinstance(value, str):
            frame[column] = frame[column].astype(object)
        frame.iloc[positions, frame.columns.get_loc(column)] = value
        scenarios[name] = frame
        altered[name] = {'column': column, 'altered_rows': len(positions), 'labels_removed': True}
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise ValueError('Monitoring output must be new or an empty directory')
    # An interrupted run's receipt directory is evidence, even if its aggregate
    # output is empty. Exclusive creation prevents adopting or replacing it.
    runtime.mkdir(parents=True, exist_ok=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(receipts).to_csv(runtime / 'sampling_weights_counts.csv', index=False)
    for name, info in sampling.items():
        draw = info.pop('positions')
        pd.DataFrame({'draw': np.arange(3000), 'source_position': draw,
                      'client_id': policy_validation.client_id.iloc[draw].to_numpy()}).to_csv(
                          runtime / f'{name}_draws.csv', index=False)
    pd.DataFrame({'source_position': positions,
                  'client_id': policy_validation.client_id.iloc[positions].to_numpy()}).to_csv(
                      runtime / 'corruption_source_ids.csv', index=False)
    edges = {c: distribution_bins(dev[c]) for c in PREDICTORS}
    edges['p_default'] = distribution_bins(dev_risk)
    reference = {c: distribution_counts(dev[c] if c != 'p_default' else dev_risk, e)
                 for c, e in edges.items()}
    report = {'synthetic': True, 'seed': 42, 'sample_size': 3000, 'subgroup_multiplier': 3,
              'development_utilization_q75': float(q75), 'epsilon': EPSILON,
              'thresholds': {'PSI': PSI_WARNING_THRESHOLD, 'missing_rate': MISSING_WARNING_THRESHOLD},
              'development_quality': dev_quality, 'sampling': sampling, 'corruption': altered,
              'customer_receipts': str(runtime), 'scenarios': {},
              'limitations': 'Synthetic composition/corruption only; PSI is heuristic, not concept '
              'drift. Corruption has no performance labels. No retraining or policy selection.'}
    rows = []
    for name, frame in scenarios.items():
        features, valid, quality = _features(frame, vocab)
        risk = _probabilities(bundle, features, valid)
        distributions = {}
        warnings = []
        for column, e in edges.items():
            counts = distribution_counts(risk if column == 'p_default' else features[column], e)
            psi = population_stability_index(reference[column], counts)
            distributions[column] = {'edges': e.tolist(), 'bin_order':
                                     'underflow, interior intervals, overflow, missing',
                                     'development_counts': reference[column].tolist(),
                                     'counts': counts.tolist(), 'PSI': psi}
            rows.append({'scenario': name, 'feature': column, 'PSI': psi,
                         'missing_count': int(counts[-1]), 'rows': len(frame)})
            if psi is not None and psi >= PSI_WARNING_THRESHOLD:
                warnings.append(f'Review distribution shift: {column}')
        if quality['quarantined_rows'] or sum(quality['unknown_category_counts'].values()):
            warnings.append('Review schema validity or unknown categories')
        if any(count / len(frame) >= MISSING_WARNING_THRESHOLD
               for count in quality['missing_counts'].values()):
            warnings.append('Review missingness')
        report['scenarios'][name] = {'quality': quality, 'scored_rows': int(np.isfinite(risk).sum()),
                                   'labeled_metrics': _metrics(frame, risk),
                                   'distributions': distributions, 'warnings': warnings}
    (output_dir / 'monitoring.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    pd.DataFrame(rows).to_csv(output_dir / 'monitoring.csv', index=False)
    _risk_distribution_plot(report, output_dir / 'risk_distribution.svg')
    return report


def _risk_distribution_plot(report, path):
    """Plot actual normalized risk-bin counts on the same development bins."""
    reference = report['scenarios']['reference']['distributions']['p_default']
    edges = reference['edges']
    labels = (['underflow'] +
              ([f'[{edges[i]:.3g}, {edges[i + 1]:.3g}'
                + (']' if i == len(edges) - 2 else ')')
                for i in range(len(edges) - 1)] if len(edges) > 1 else
               [f'[{edges[0]:.3g}]'] if edges else []) + ['overflow', 'missing'])
    series = [('development', reference['development_counts'], '#444444')]
    for name, color in [('reference', '#3178a8'), ('financial_mix_shift', '#df861c'),
                        ('delinquency_mix_shift', '#21895d')]:
        series.append((name, report['scenarios'][name]['distributions']['p_default']['counts'], color))
    contents = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="480">',
                '<title>Synthetic predicted-risk distributions</title>',
                '<text x="60" y="25">Synthetic predicted-risk distributions; development-defined bins</text>',
                '<text x="60" y="48">Fraction of all rows; missing includes unscored/quarantined rows</text>']
    left, top, height, width = 60, 100, 260, 1080
    for fraction in (0, 0.25, 0.5, 0.75, 1):
        y = top + height * (1 - fraction)
        contents.append(f'<path d="M{left} {y}H{left + width}" stroke="#dddddd"/>'
                        f'<text x="5" y="{y + 4}">{fraction:.0%}</text>')
    group_width = width / len(labels)
    bar_width = group_width / (len(series) + 1)
    for j, (name, counts, color) in enumerate(series):
        total = sum(counts)
        contents.append(f'<rect x="{60 + j * 270}" y="65" width="12" height="12" fill="{color}"/>'
                        f'<text x="{78 + j * 270}" y="77">{name} (n={total})</text>')
        for i, count in enumerate(counts):
            fraction = count / total if total else 0
            x = left + i * group_width + j * bar_width
            y = top + height * (1 - fraction)
            contents.append(f'<rect data-series="{name}" data-bin="{i}" data-count="{count}" '
                            f'data-fraction="{fraction}" x="{x:.3f}" y="{y:.3f}" '
                            f'width="{bar_width:.3f}" height="{fraction * height:.3f}" '
                            f'fill="{color}"><title>{name}: {escape(labels[i])}, '
                            f'{count}/{total} ({fraction:.2%})</title></rect>')
    for i, label in enumerate(labels):
        x = left + i * group_width + group_width / 2
        contents.append(f'<text transform="translate({x:.3f},380) rotate(25)" '
                        f'font-size="11">{escape(label)}</text>')
    contents.append('</svg>')
    path.write_text(''.join(contents))
