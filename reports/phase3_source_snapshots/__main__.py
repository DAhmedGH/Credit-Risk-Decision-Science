"""Reproduce Phase 1 data contracts or Phase 2 development baselines."""

import argparse
import json
import sys

from credit_risk.config import load_config
from credit_risk import phase1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "ingest", "features", "split", "eda", "reproduce",
                                           "baselines", "baseline-inputs", "phase3-plan",
                                           "phase3-profile", "phase3-search", "phase3-select",
                                           "phase3-verify"])
    parser.add_argument("--config", default=None)
    parser.add_argument("--family", choices=["logistic", "random_forest", "xgboost"])
    parser.add_argument("--search-runs", nargs=3)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    try:
        if args.command.startswith("phase3-"):
            from credit_risk import phase3
            config = args.config or "configs/phase3.toml"
            if args.command == "phase3-search":
                if not args.family:
                    raise ValueError("phase3-search requires --family")
                result = phase3.run_search(args.family, config)
            elif args.command == "phase3-select":
                if not args.search_runs:
                    raise ValueError("phase3-select requires --search-runs with three run IDs")
                result = phase3.select(args.search_runs, config)
            elif args.command == "phase3-verify":
                if not args.run_id:
                    raise ValueError("phase3-verify requires --run-id")
                result = phase3.verify(args.run_id, config)
            elif args.command == "phase3-plan":
                result = phase3.declare_plan(config)
            else:
                result = phase3.profile(config)
        elif args.command in {"baselines", "baseline-inputs"}:
            from credit_risk import phase2
            config = args.config or "configs/phase2.toml"
            result = phase2.run(config) if args.command == "baselines" else phase2.check_inputs(config)
        else:
            result = getattr(phase1, args.command)(load_config(args.config or "configs/base.toml"))
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as error:
        print(f"{args.command} stopped: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        # Driver connection errors may contain sensitive connection information.
        print(f"{args.command} stopped ({type(error).__name__}); check local dependencies and stage inputs.",
              file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result.get("runtime_validation_passed", True) else 1


if __name__ == "__main__":
    sys.exit(main())
