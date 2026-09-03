#!/usr/bin/env python
"""
Validate a generated dataset: schema, ground-truth re-projection, noise statistics,
outlier bookkeeping, manifest consistency and bit-for-bit reproducibility.

Exit status is 1 when any check fails.

    python scripts/validate_dataset.py --data data
    python scripts/validate_dataset.py --data data --max-cameras 500 --regenerate 3
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.validate import validate_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True, help="dataset directory")
    parser.add_argument("--max-cameras", type=int, default=None, help="validate a random subset of cameras (default: all)")
    parser.add_argument("--regenerate", type=int, default=1, help="scenes to regenerate for the reproducibility check")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--report", default=None, help="write the JSON report to this path (default: <data>/metadata/validation_report.json)")
    parser.add_argument("--no-progress", action="store_true")
    args = parser.parse_args()

    report = validate_dataset(args.data, max_cameras=args.max_cameras, regenerate=args.regenerate, seed=args.seed,
                              progress=not args.no_progress)
    out = Path(args.report) if args.report else Path(args.data) / "metadata" / "validation_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"report written to {out}")
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
