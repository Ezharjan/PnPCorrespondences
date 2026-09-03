#!/usr/bin/env python
"""
A miniature benchmark: run every available solver over a stratified subset and
print one table.  It is the shape of `scripts/run_benchmark.py` reduced to a
single screen, useful for a quick sanity check or as a template for a new solver.

    python examples/04_compare_solvers.py --data data
    python examples/04_compare_solvers.py --data data --max-samples 60 --query "outlier_ratio == 0"
    python examples/04_compare_solvers.py --data data --solvers sqpnp,epnp_lm,cv_usac_magsac

For the full study - all factors, all tables, the figures - use
`scripts/run_benchmark.py` followed by `scripts/analyze_results.py`.
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.benchmark import ransac_threshold, select_samples  # noqa: E402
from pnpcorr.cameras import undistort_to_pinhole_pixels  # noqa: E402
from pnpcorr.metrics import inlier_classification, is_success, pose_metrics  # noqa: E402
from pnpcorr.solvers import available_solvers  # noqa: E402
from pnpcorr.storage import SampleReader, load_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data", help="dataset directory")
    parser.add_argument("--max-samples", type=int, default=40, help="stratified sample budget")
    parser.add_argument("--query", default=None, help="pandas query applied to the manifest")
    parser.add_argument("--split", default=None, help="restrict to one split")
    parser.add_argument("--solvers", default=None, help="comma-separated solver names (default: all available)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    manifest = load_manifest(args.data)
    subset = select_samples(manifest, args.max_samples, args.split, args.query, args.seed)
    names = [s.strip() for s in args.solvers.split(",")] if args.solvers else None
    specs = available_solvers(names)
    print(f"{len(subset)} samples x {len(specs)} available solvers "
          f"({subset['scene_type'].nunique()} scene types, {subset['camera_model'].nunique()} camera models, "
          f"{subset['condition_id'].nunique()} noise conditions)")
    print("minimal solvers (p3p, ap3p) are evaluated at exactly four correspondences and are therefore\n"
          "absent from a run that uses every visible point; see the sweep task of run_benchmark.py.\n")

    stats = {spec.name: {"spec": spec, "rot": [], "trans": [], "ok": 0, "success": 0, "n": 0,
                         "ms": [], "prec": [], "reasons": {}} for spec in specs}
    with SampleReader(args.data) as reader:
        for _, row in subset.iterrows():
            sample = reader.read(row)
            intr = sample.intrinsics
            uv, invertible = undistort_to_pinhole_pixels(sample.uv, intr)
            uv = np.where(invertible[:, None], uv, sample.uv)
            X = sample.X
            gt_inl = ~sample.outlier_mask
            depth_scale = float(sample.depths[gt_inl].mean())
            thr = ransac_threshold("auto", float(row["noise_sigma"]), bool(row["quantize"]))
            for spec in specs:
                if len(X) < spec.min_points or (spec.exact_points and len(X) != spec.min_points):
                    continue
                acc = stats[spec.name]
                acc["n"] += 1
                t0 = time.perf_counter()
                est = spec.fn(X, uv, intr.K, threshold=thr, max_iters=2000, confidence=0.99, seed=args.seed)
                acc["ms"].append((time.perf_counter() - t0) * 1000.0)
                if not est.ok:
                    acc["reasons"][est.reason] = acc["reasons"].get(est.reason, 0) + 1
                    continue
                acc["ok"] += 1
                pm = pose_metrics(est.R, est.t, sample.R, sample.t, depth_scale)
                acc["rot"].append(pm["rot_err_deg"])
                acc["trans"].append(pm["trans_err_rel"])
                acc["success"] += int(is_success(pm["rot_err_deg"], pm["trans_err_rel"]))
                if est.inliers is not None:
                    acc["prec"].append(inlier_classification(est.inliers, sample.outlier_mask)["inlier_precision"])

    def med(values):
        return float(np.median(values)) if values else float("nan")

    print(f"{'solver':20s} {'family':16s} {'solves':>7s} {'returned':>9s} {'success':>8s} "
          f"{'rot err med':>12s} {'rel trans':>10s} {'inlier P':>9s} {'ms':>8s}")
    for name, acc in stats.items():
        if acc["n"] == 0:
            continue
        prec = f"{med(acc['prec']):9.3f}" if acc["prec"] else f"{'-':>9s}"
        print(f"{name:20s} {acc['spec'].family:16s} {acc['n']:7d} {100 * acc['ok'] / acc['n']:8.1f}% "
              f"{100 * acc['success'] / acc['n']:7.1f}% {med(acc['rot']):12.2e} {med(acc['trans']):10.2e} "
              f"{prec} {med(acc['ms']):8.2f}")

    print("\nsuccess = rotation error <= 5 deg and relative translation error <= 5 %")
    reasons = {(n, r): c for n, acc in stats.items() for r, c in acc["reasons"].items()}
    if reasons:
        print("\nwhy a solver returned nothing:")
        for (name, reason), count in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(f"  {count:4d}  {name:20s} {reason}")


if __name__ == "__main__":
    main()
