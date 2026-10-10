"""Synthetic XGBoost import/fit/save/load check; never portfolio measurements."""

import json
from pathlib import Path
import tempfile

from credit_risk.phase3 import check_xgboost


def main():
    check_xgboost()
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.base import clone
    from threadpoolctl import threadpool_limits
    from credit_risk.data.schema import RAW_PREDICTORS, STATUS_COLUMNS
    from credit_risk.features import build_features
    from credit_risk.models.pipelines import build_pipeline, positive_probability

    rows = []
    for index in range(40):
        record = dict.fromkeys(RAW_PREDICTORS, 100)
        record["limit_bal"] = 1000 + 100 * index
        record.update({column: index % 4 - 2 for column in STATUS_COLUMNS})
        rows.append(build_features(record))
    X, y = pd.DataFrame(rows), np.array([int(i % 4 == 0) for i in range(40)])
    with tempfile.TemporaryDirectory(prefix="credit-risk-phase3-smoke-") as directory:
        for weighting in ("none", "balanced"):
            pipeline = clone(build_pipeline("xgboost", "engineered", weighting,
                                           model_params={"n_estimators": 3}))
            with threadpool_limits(limits=1):
                pipeline.fit(X, y)
                prediction = positive_probability(pipeline, X)
                path = Path(directory) / f"{weighting}.joblib"
                joblib.dump(pipeline, path)
                np.testing.assert_array_equal(prediction, positive_probability(joblib.load(path), X))
            expected = 3.0 if weighting == "balanced" else 1.0
            assert pipeline.named_steps["model"].scale_pos_weight_ == expected
    print(json.dumps({"scope": "synthetic only", "xgboost_version": "3.0.5", "fits": 2,
                      "import_fit_save_load": "passed", "fold_local_weight": "passed"}))


if __name__ == "__main__":
    main()
