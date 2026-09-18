#!/usr/bin/env python
"""
Quick start: open one sample, solve PnP with a few solvers and print the errors.

    python examples/quickstart.py --data data
    python examples/quickstart.py --data data --query "camera_model == 'kannala_brandt' and outlier_ratio == 0.5"

The same data can be read without pnpcorr using plain h5py (see the README,
section "Dataset format"); pnpcorr only adds convenience wrappers.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.benchmark import ransac_threshold  # noqa: E402
from pnpcorr.cameras import undistort_to_pinhole_pixels  # noqa: E402
from pnpcorr.metrics import inlier_classification, pose_metrics, reprojection_rmse  # noqa: E402
from pnpcorr.solvers import available_solvers  # noqa: E402
from pnpcorr.storage import SampleReader, load_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data", help="dataset directory")
    parser.add_argument("--query", default="outlier_ratio == 0.2 and noise_sigma == 0.5",
                        help="pandas query selecting the sample (the first match is used)")
    parser.add_argument("--solvers", default="sqpnp,epnp_lm,dlt_lm,ransac_p3p,cv_usac_magsac")
    args = parser.parse_args()

    manifest = load_manifest(args.data)
    rows = manifest.query(args.query)
    if rows.empty:
        sys.exit("no sample matches the query")
    row = rows.iloc[0]
    with SampleReader(args.data) as reader:
        sample = reader.read(row)

    intr = sample.intrinsics
    print(f"sample      : {sample.sample_id}")
    print(f"scene       : {row['scene_type']} ({sample.points_3d.shape[0]} 3D points), split={row['split']}")
    print(f"camera      : {intr.model}, {intr.width}x{intr.height}, HFOV {intr.hfov_deg:.1f} deg, "
          f"distortion={intr.distortion_level}")
    print(f"condition   : {row['condition_name']}  ->  {sample.num_visible} correspondences, "
          f"{int(sample.outlier_mask.sum())} outliers")

    # Calibrated PnP: undistort the observations to the equivalent pinhole image first.
    uv_pinhole, ok = undistort_to_pinhole_pixels(sample.uv, intr)
    uv_pinhole = np.where(ok[:, None], uv_pinhole, sample.uv)
    X = sample.X
    thr = ransac_threshold("auto", float(row["noise_sigma"]), bool(row["quantize"]))
    depth_scale = float(sample.depths[~sample.outlier_mask].mean())

    names = [s.strip() for s in args.solvers.split(",")]
    print(f"\n{'solver':18s} {'ok':3s} {'rot err [deg]':>14s} {'rel. trans err':>15s} {'reproj RMSE [px]':>17s} {'inlier P/R':>12s}")
    for spec in available_solvers(names):
        est = spec.fn(X, uv_pinhole, intr.K, threshold=thr, max_iters=2000, confidence=0.99, seed=0)
        if not est.ok:
            print(f"{spec.name:18s} no  ({est.reason})")
            continue
        pm = pose_metrics(est.R, est.t, sample.R, sample.t, depth_scale)
        rmse = reprojection_rmse(X, sample.uv_clean, intr, est.R, est.t, mask=~sample.outlier_mask)
        cls = inlier_classification(est.inliers, sample.outlier_mask)
        pr = f"{cls['inlier_precision']:.2f}/{cls['inlier_recall']:.2f}" if est.inliers is not None else "-"
        print(f"{spec.name:18s} yes {pm['rot_err_deg']:14.4g} {pm['trans_err_rel']:15.4g} {rmse:17.4g} {pr:>12s}")


if __name__ == "__main__":
    main()
