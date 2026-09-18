#!/usr/bin/env python
"""
Aggregate benchmark results into summary tables (CSV + Markdown) and results/summary.md.

    python scripts/analyze_results.py --results results
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.analysis import summarize_calibration, summarize_multiview, summarize_pnp, write_summary  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", required=True, help="results directory written by run_benchmark.py")
    args = parser.parse_args()
    results = Path(args.results)
    tables = results / "tables"
    parts = {}
    pnp = results / "pnp_results.csv"
    if pnp.exists():
        parts["pnp"] = summarize_pnp(pd.read_csv(pnp), tables, "pnp")
    sweep = results / "pnp_num_points_results.csv"
    if sweep.exists():
        parts["pnp_sweep"] = summarize_pnp(pd.read_csv(sweep), tables, "pnp_sweep")
    calib = results / "calibration_results.csv"
    if calib.exists():
        parts["calibration"] = summarize_calibration(pd.read_csv(calib), tables)
    multi = results / "multiview_results.csv"
    if multi.exists():
        parts["multiview"] = summarize_multiview(pd.read_csv(multi), tables)
    env = None
    meta = results / "benchmark_meta.json"
    if meta.exists():
        with open(meta, "r", encoding="utf-8") as fh:
            env = json.load(fh).get("environment")
    if not parts:
        print("no result files found in", results)
        sys.exit(1)
    path = write_summary(results, parts, env)
    print(f"tables written to {tables}\nsummary written to {path}")


if __name__ == "__main__":
    main()
