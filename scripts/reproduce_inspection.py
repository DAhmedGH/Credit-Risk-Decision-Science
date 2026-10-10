"""Run the qualified independent diagnostic and log access before any cell decoding."""

import os
import runpy

from credit_risk.config import PROJECT_ROOT, load_config, project_path
from credit_risk.phase1 import log_source_access, provenance_context


def main():
    if not __debug__:
        raise RuntimeError("The bounded BIFF diagnostic requires assertion checks; omit -O")
    os.chdir(PROJECT_ROOT)
    config = load_config()
    _, checksum = provenance_context(config)
    log_source_access("independent BIFF numeric diagnostic requested", checksum,
                      project_path(config["split_manifest"]))
    runpy.run_path(str(PROJECT_ROOT / "scripts/inspect_supplied_workbook.py"), run_name="__main__")
    runpy.run_path(str(PROJECT_ROOT / "scripts/inspection_phase1.py"), run_name="__main__")


if __name__ == "__main__":
    main()
