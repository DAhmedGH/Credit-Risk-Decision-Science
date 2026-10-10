if not __debug__:
    raise RuntimeError("Run this audit check without Python -O; assertions verify integrity")

from pathlib import Path
from tempfile import TemporaryDirectory
from runpy import run_path

from credit_risk.data.schema import BILL_COLUMNS, validate_records
from credit_risk.features import build_features, PREDICTORS
from credit_risk.artifacts import write_csv
from credit_risk.splits import allocate_records
from credit_risk.models.phase4_inputs import routed_partitions

make_records = run_path(str(Path(__file__).resolve().parents[2] / "tests/fixtures/records.py"))[
    "make_records"
]

for variant in ("missing_financial", "missing_audit"):
    with TemporaryDirectory() as directory:
        root = Path(directory)
        target = root / "data/processed"
        target.mkdir(parents=True)
        records = make_records()
        for record in records:
            record[BILL_COLUMNS[0] if variant == "missing_financial" else "sex"] = None
        accepted = validate_records(records).accepted
        assert len(accepted) == len(records)
        assignments, _ = allocate_records(accepted, "a" * 64)
        write_csv(
            target / "financial_features_v1.csv",
            [{"client_id": r["client_id"], **build_features(r)} for r in accepted],
            ("client_id", *PREDICTORS),
        )
        columns = ("client_id", "default_next_month")
        write_csv(target / "labels.csv", [{k: r[k] for k in columns} for r in accepted], columns)
        columns = (
            "client_id",
            "sex",
            "age",
            "education",
            "marriage",
            "sex_group",
            "education_group",
            "marriage_group",
        )
        audits = [
            {
                **r,
                "sex_group": "unknown",
                "education_group": "university",
                "marriage_group": "married",
            }
            for r in accepted
        ]
        write_csv(
            target / "audit_attributes.csv", [{k: r[k] for k in columns} for r in audits], columns
        )
        try:
            routed_partitions(root, assignments)
        except ValueError as error:
            print(variant, "accepted_rows", len(accepted), "failure", str(error))
        else:
            print(variant, "PASS")
