"""Synthetic import/tree-SHAP/plot/calibration/save-load compatibility smoke."""
import tempfile
from pathlib import Path

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from xgboost import XGBClassifier

from credit_risk.models.calibration import fit_mappings
from credit_risk.models.pipelines import positive_probability

# Fixture compatibility only; historical Phase 4 commands enforce accepted_integrity.
assert shap.__version__ == '0.48.0' and matplotlib.__version__ == '3.10.6'
rng = np.random.default_rng(42)
X = pd.DataFrame(rng.normal(size=(120, 3)), columns=['a', 'b', 'c'])
y = (X.a + rng.normal(size=120) > 0).astype(int)
base = XGBClassifier(n_estimators=5, max_depth=2, n_jobs=1, random_state=42).fit(X.iloc[:60], y.iloc[:60])
variants = fit_mappings(base, X.iloc[60:100], y.iloc[60:100], partition='calibration',
                        calibration_ids=list(range(60, 100)), development_ids=list(range(60)))
explainer = shap.TreeExplainer(base, data=X.iloc[:20], feature_perturbation='interventional', model_output='raw')
values = explainer.shap_values(X.iloc[100:], check_additivity=True)
assert np.allclose(np.sum(values, axis=1) + explainer.expected_value,
                   base.predict(X.iloc[100:], output_margin=True), atol=1e-5, rtol=1e-5)
with tempfile.TemporaryDirectory(prefix='credit-risk-phase4-smoke-') as directory:
    path = Path(directory)
    joblib.dump(variants, path / 'variants.joblib')
    restored = joblib.load(path / 'variants.joblib')
    for key in variants:
        assert np.array_equal(positive_probability(variants[key], X), positive_probability(restored[key], X))
    shap.summary_plot(values, X.iloc[100:], show=False)
    plt.savefig(path / 'smoke.png')
    assert (path / 'smoke.png').stat().st_size > 0
    plt.close('all')
print('Synthetic calibration/TreeSHAP/plot/save-load smoke passed; no real-data fitting or test exposure.')
