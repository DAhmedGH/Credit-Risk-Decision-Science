"""Small synthetic import/fit/save/load/local-tracking check before locking."""

import json
from pathlib import Path
import tempfile

from credit_risk.phase2 import check_dependencies


def main():
    check_dependencies()
    import joblib
    import numpy as np
    import pandas as pd
    from mlflow import MlflowClient
    from threadpoolctl import threadpool_limits

    from credit_risk.data.schema import RAW_PREDICTORS, STATUS_COLUMNS
    from credit_risk.features import build_features
    from credit_risk.models.pipelines import build_pipeline, positive_probability

    rows = []
    for index in range(30):
        record = dict.fromkeys(RAW_PREDICTORS, 100)
        record["limit_bal"] = 1000 + 100 * index
        record.update({column: index % 4 - 2 for column in STATUS_COLUMNS})
        rows.append(build_features(record))
    frame, labels = pd.DataFrame(rows), np.array([int(index % 4 == 0) for index in range(30)])
    with tempfile.TemporaryDirectory(prefix="credit-risk-phase2-smoke-") as directory:
        root = Path(directory)
        for model in ("dummy", "logistic", "random_forest"):
            params = {"n_estimators": 2} if model == "random_forest" else {}
            pipeline = build_pipeline(model, "engineered", "none", model_params=params)
            with threadpool_limits(limits=1):
                pipeline.fit(frame, labels)
            predictions = positive_probability(pipeline, frame)
            path = root / f"{model}.joblib"
            joblib.dump(pipeline, path)
            np.testing.assert_allclose(predictions, positive_probability(joblib.load(path), frame),
                                       atol=1e-12, rtol=0)
        client = MlflowClient(tracking_uri=(root / "mlruns").as_uri())
        experiment = client.create_experiment("synthetic-smoke")
        run = client.create_run(experiment)
        client.log_metric(run.info.run_id, "fixture_serialization_agreement", 1.0)
        client.log_artifact(run.info.run_id, str(path))
        client.set_terminated(run.info.run_id)
        assert client.get_run(run.info.run_id).info.status == "FINISHED"
    print(json.dumps({"scope": "synthetic fixture only", "models": 3,
                      "import_fit_save_load": "passed", "local_mlflow": "passed"}))


if __name__ == "__main__":
    main()
