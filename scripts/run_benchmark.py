#!/usr/bin/env python
"""
Run the solver benchmarks on a generated dataset.

Tasks
-----
  pnp          calibrated PnP with every available solver (all visible correspondences)
  sweep        calibrated PnP versus the number of correspondences (random subsets)
  calibration  single-view uncalibrated DLT (K, R, t from raw pixels)
  multiview    multi-view calibration (OpenCV and from-scratch bundle adjustment)
  all          everything above

Examples
--------
    python scripts/run_benchmark.py --data data --out results --task all --max-samples 1500
    python scripts/run_benchmark.py --data data --out results --task pnp --solvers sqpnp,epnp,cv_usac_magsac
    python scripts/run_benchmark.py --data data --out results --task sweep --num-points 4,6,8,12,20,50,100,500
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.benchmark import (environment_info, parse_num_points, run_calibration_benchmark,  # noqa: E402
                               run_multiview_benchmark, run_pnp_benchmark, select_samples)
from pnpcorr.solvers import SOLVERS, available_solvers  # noqa: E402
from pnpcorr.storage import load_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True, help="dataset directory")
    parser.add_argument("--out", required=True, help="results directory")
    parser.add_argument("--task", default="all", choices=["pnp", "sweep", "calibration", "multiview", "all"])
    parser.add_argument("--split", default=None, help="restrict to one split (train/val/test); default: all splits")
    parser.add_argument("--query", default=None, help="pandas query applied to the manifest, e.g. \"camera_model == 'pinhole'\"")
    parser.add_argument("--max-samples", type=int, default=1500, help="stratified sample budget for pnp / calibration")
    parser.add_argument("--sweep-samples", type=int, default=400, help="sample budget for the number-of-points sweep")
    parser.add_argument("--max-rigs", type=int, default=60, help="calibration rigs for the multi-view task")
    parser.add_argument("--solvers", default=None, help="comma-separated solver names (default: all available)")
    parser.add_argument("--num-points", default="4,6,8,12,20,50,100,500", help="subset sizes for the sweep task")
    parser.add_argument("--threshold", default="auto", help="RANSAC inlier threshold in px, or 'auto' = max(2, 3 sigma)")
    parser.add_argument("--max-iters", type=int, default=2000, help="RANSAC iteration cap")
    parser.add_argument("--confidence", type=float, default=0.99)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--list-solvers", action="store_true", help="print the solver registry and exit")
    parser.add_argument("--no-progress", action="store_true")
    args = parser.parse_args()

    if args.list_solvers:
        avail = {s.name for s in available_solvers()}
        for name, spec in SOLVERS.items():
            flag = "" if name in avail else "  (unavailable: needs OpenCV)"
            print(f"{name:20s} {spec.family:15s} min_points={spec.min_points:<3d} planar={spec.planar:6s} "
                  f"robust={'yes' if spec.robust else 'no':3s}  {spec.description}{flag}")
        return

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(args.data)
    solvers = [s.strip() for s in args.solvers.split(",")] if args.solvers else None
    progress = not args.no_progress
    meta = {"environment": environment_info(), "arguments": vars(args), "tasks": {}}
    tasks = ["pnp", "sweep", "calibration", "multiview"] if args.task == "all" else [args.task]

    for task in tasks:
        t0 = time.time()
        if task == "pnp":
            subset = select_samples(manifest, args.max_samples, args.split, args.query, args.seed)
            df = run_pnp_benchmark(args.data, subset, solvers, ["all"], args.threshold, args.max_iters,
                                   args.confidence, args.seed, progress=progress)
            path = out / "pnp_results.csv"
        elif task == "sweep":
            q = "outlier_ratio == 0"
            if args.query:
                q = f"({args.query}) and ({q})"
            subset = select_samples(manifest, args.sweep_samples, args.split, q, args.seed,
                                    strata=("scene_type", "camera_model", "noise_sigma"))
            df = run_pnp_benchmark(args.data, subset, solvers, parse_num_points(args.num_points.split(",")),
                                   args.threshold, args.max_iters, args.confidence, args.seed, progress=progress)
            path = out / "pnp_num_points_results.csv"
        elif task == "calibration":
            q = "outlier_ratio == 0 and scene_type != 'planar_single'"
            if args.query:
                q = f"({args.query}) and ({q})"
            subset = select_samples(manifest, args.max_samples, args.split, q, args.seed,
                                    strata=("scene_type", "camera_model", "fov_class", "condition_id"))
            df = run_calibration_benchmark(args.data, subset, args.seed, progress=progress)
            path = out / "calibration_results.csv"
        else:  # multiview
            q = "outlier_ratio == 0 and quantize == False and scene_type != 'planar_single'"
            if args.query:
                q = f"({args.query}) and ({q})"
            sub = manifest.query(q)
            if args.split:
                sub = sub[sub["split"] == args.split]
            df = run_multiview_benchmark(args.data, sub, max_rigs=args.max_rigs, seed=args.seed, progress=progress)
            path = out / "multiview_results.csv"
        elapsed = time.time() - t0
        if df is None or len(df) == 0:
            print(f"[{task}] no results (task not applicable to this dataset, e.g. fewer than 3 poses per intrinsic set)")
            meta["tasks"][task] = {"rows": 0, "seconds": round(elapsed, 1)}
            continue
        df.to_csv(path, index=False)
        meta["tasks"][task] = {"rows": int(len(df)), "seconds": round(elapsed, 1), "file": path.name}
        print(f"[{task}] {len(df)} result rows in {elapsed:.1f}s -> {path}")
    with open(out / "benchmark_meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, default=str)


if __name__ == "__main__":
    main()
