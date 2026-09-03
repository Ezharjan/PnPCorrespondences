#!/usr/bin/env python
"""
The breakdown point of a robust estimator, measured directly on the dataset.

The outlier sweep (0 %, 5 %, 20 %, 50 %, 80 %, 95 % at a fixed sigma) is applied to
the same geometry each time, so the curve below isolates contamination from every
other factor.  Both halves of the story are printed: the pose error, and the
quality of the inlier mask the estimator returns, which the ground-truth
`outlier_mask` makes measurable.

    python examples/05_robustness_to_outliers.py --data data
    python examples/05_robustness_to_outliers.py --data data --outlier-type swap --samples-per-ratio 12
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.benchmark import ransac_threshold  # noqa: E402
from pnpcorr.cameras import undistort_to_pinhole_pixels  # noqa: E402
from pnpcorr.metrics import inlier_classification, is_success, pose_metrics  # noqa: E402
from pnpcorr.solvers import SOLVERS, available_solvers  # noqa: E402
from pnpcorr.storage import SampleReader, load_manifest  # noqa: E402

DEFAULT_SOLVERS = "ransac_p3p,ransac_dlt,cv_ransac_epnp,cv_ransac_ap3p,cv_usac_magsac,sqpnp"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data", help="dataset directory")
    parser.add_argument("--solvers", default=DEFAULT_SOLVERS,
                        help="comma-separated solver names (the last one here is deliberately non-robust)")
    parser.add_argument("--noise-sigma", type=float, default=0.5, help="the sigma the outlier sweep uses")
    parser.add_argument("--outlier-type", default="uniform", choices=["uniform", "swap", "mixed"])
    parser.add_argument("--samples-per-ratio", type=int, default=8)
    parser.add_argument("--max-iters", type=int, default=2000, help="RANSAC iteration cap")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    manifest = load_manifest(args.data)
    sweep = manifest[(manifest["noise_sigma"] == args.noise_sigma) & (~manifest["quantize"].astype(bool))
                     & ((manifest["outlier_type"] == args.outlier_type) | (manifest["outlier_ratio"] == 0))]
    ratios = sorted(sweep["outlier_ratio"].unique())
    if len(ratios) < 2:
        sys.exit(f"this dataset has only {len(ratios)} outlier ratio(s) at sigma = {args.noise_sigma} "
                 f"and outlier_type = {args.outlier_type}; the `small` tier or larger is needed")

    names = [n.strip() for n in args.solvers.split(",")]
    specs = available_solvers(names)
    rng = np.random.default_rng(args.seed)
    success = {s.name: [] for s in specs}
    rot = {s.name: [] for s in specs}
    prf = {s.name: [] for s in specs}

    with SampleReader(args.data) as reader:
        for ratio in ratios:
            rows = sweep[sweep["outlier_ratio"] == ratio]
            rows = rows.sample(n=min(args.samples_per_ratio, len(rows)), random_state=args.seed)
            per_solver = {s.name: {"ok": 0, "n": 0, "rot": [], "p": [], "r": []} for s in specs}
            for _, row in rows.iterrows():
                sample = reader.read(row)
                intr = sample.intrinsics
                uv, invertible = undistort_to_pinhole_pixels(sample.uv, intr)
                uv = np.where(invertible[:, None], uv, sample.uv)
                X = sample.X
                gt_inl = ~sample.outlier_mask
                depth_scale = float(sample.depths[gt_inl].mean())
                thr = ransac_threshold("auto", float(row["noise_sigma"]), bool(row["quantize"]))
                for spec in specs:
                    if len(X) < spec.min_points:
                        continue
                    acc = per_solver[spec.name]
                    acc["n"] += 1
                    est = spec.fn(X, uv, intr.K, threshold=thr, max_iters=args.max_iters,
                                  confidence=0.99, seed=int(rng.integers(2 ** 31 - 1)))
                    if not est.ok:
                        continue
                    pm = pose_metrics(est.R, est.t, sample.R, sample.t, depth_scale)
                    acc["rot"].append(pm["rot_err_deg"])
                    acc["ok"] += int(is_success(pm["rot_err_deg"], pm["trans_err_rel"]))
                    if est.inliers is not None:
                        cls = inlier_classification(est.inliers, sample.outlier_mask)
                        acc["p"].append(cls["inlier_precision"])
                        acc["r"].append(cls["inlier_recall"])
            for spec in specs:
                acc = per_solver[spec.name]
                success[spec.name].append(100.0 * acc["ok"] / acc["n"] if acc["n"] else float("nan"))
                rot[spec.name].append(float(np.median(acc["rot"])) if acc["rot"] else float("nan"))
                prf[spec.name].append((float(np.median(acc["p"])) if acc["p"] else float("nan"),
                                       float(np.median(acc["r"])) if acc["r"] else float("nan")))

    header = "  ".join(f"{100 * r:5.0f}%" for r in ratios)
    print(f"sigma = {args.noise_sigma} px, {args.outlier_type} outliers, "
          f"{args.samples_per_ratio} samples per ratio, RANSAC budget {args.max_iters}\n")
    print(f"success rate [%]        {header}")
    for name in success:
        print(f"  {name:20s}" + "  ".join(f"{v:6.0f}" for v in success[name])
              + ("   (not robust)" if not SOLVERS[name].robust else ""))
    print(f"\nmedian rotation error [deg]")
    for name in rot:
        print(f"  {name:20s}" + "  ".join(f"{v:6.2g}" for v in rot[name]))
    if any(np.isfinite(p) for name in prf for p, _ in prf[name]):
        print(f"\ninlier mask, median precision / recall")
        for name in prf:
            if not np.isfinite(prf[name][0][0]):
                continue
            print(f"  {name:20s}" + "  ".join(f" {p:.2f}/{r:.2f}" for p, r in prf[name]))
    print("\nA robust estimator needs one all-inlier minimal sample: with an inlier fraction w and a")
    print("minimal set of m points, that takes about log(1 - 0.99) / log(1 - w^m) iterations, so the")
    print("3-point solvers hold on far longer than the 5-point ones as the contamination grows.")


if __name__ == "__main__":
    main()
