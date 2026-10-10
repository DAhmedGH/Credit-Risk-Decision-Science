"""Check imports and a deterministic data serialization round trip, without model fitting."""

import importlib.metadata
import json
import sys

import psycopg
import xlrd

from credit_risk.features import feature_contract


def main():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("The project runtime must be Python 3.12")
    contract = feature_contract()
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert psycopg.__version__ == importlib.metadata.version("psycopg")
    assert xlrd.__version__ == importlib.metadata.version("xlrd")
    print(json.dumps({"python": sys.version.split()[0], "xlrd": xlrd.__version__,
                      "psycopg": psycopg.__version__, "feature_round_trip": "passed",
                      "predictive_fit": "not run: outside Phase 1"}, indent=2))


if __name__ == "__main__":
    main()
