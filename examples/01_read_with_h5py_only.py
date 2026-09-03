#!/usr/bin/env python
"""
Read the dataset with nothing but h5py, pandas and NumPy, and re-derive the ground
truth from first principles.

The point of this example is that the dataset does not need `pnpcorr` at all: the
manifest says where every array lives, and the HDF5 groups carry the exact camera
that produced the observations.  The script re-implements the forward model of
README Section 5.1 in twenty lines and checks that it reproduces the stored clean
projections to floating-point accuracy.

    python examples/01_read_with_h5py_only.py --data data
    python examples/01_read_with_h5py_only.py --data data --num-samples 20
"""
import argparse

import h5py
import numpy as np
import pandas as pd


def project(points_3d, K, coeffs, model, R, t):
    """Forward projection of README Section 5.1, in plain NumPy."""
    pc = points_3d @ R.T + t                      # world -> camera
    xn, yn = pc[:, 0] / pc[:, 2], pc[:, 1] / pc[:, 2]
    if model == "brown_conrady":
        k1, k2, p1, p2, k3 = coeffs
        r2 = xn * xn + yn * yn
        radial = 1.0 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
        xd = xn * radial + 2.0 * p1 * xn * yn + p2 * (r2 + 2.0 * xn ** 2)
        yd = yn * radial + p1 * (r2 + 2.0 * yn ** 2) + 2.0 * p2 * xn * yn
    elif model == "kannala_brandt":
        k1, k2, k3, k4 = coeffs
        r = np.hypot(xn, yn)
        theta = np.arctan(r)
        t2 = theta * theta
        theta_d = theta * (1.0 + t2 * (k1 + t2 * (k2 + t2 * (k3 + t2 * k4))))
        scale = np.where(r > 1e-12, theta_d / np.where(r > 1e-12, r, 1.0), 1.0)
        xd, yd = xn * scale, yn * scale
    else:                                          # pinhole
        xd, yd = xn, yn
    u = K[0, 0] * xd + K[0, 1] * yd + K[0, 2]      # note the skew term on u only
    v = K[1, 1] * yd + K[1, 2]
    return np.column_stack([u, v])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data", help="dataset directory")
    parser.add_argument("--num-samples", type=int, default=8, help="samples to check")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    manifest = pd.read_parquet(f"{args.data}/manifest.parquet")
    rows = manifest.sample(n=min(args.num_samples, len(manifest)), random_state=args.seed)
    print(f"{len(manifest):,} samples in the manifest; checking {len(rows)} of them\n")
    print(f"{'camera model':16s} {'M':>6s} {'sigma':>6s} {'outliers':>9s} "
          f"{'max |proj - stored| [px]':>26s} {'inlier RMS [px]':>16s}")

    worst = 0.0
    for _, row in rows.iterrows():
        with h5py.File(f"{args.data}/{row.file}", "r") as f:
            cond = f[row.h5_path]                  # /scene_XXXXX/camera_XXX/condition_XXX
            cam, scene = cond.parent, cond.parent.parent
            idx = cam["point_indices"][()]
            X = scene["points_3d"][()][idx]
            K = cam["K"][()]
            coeffs = cam["dist_coeffs"][()]
            Rt = cam["pose_Rt"][()]
            model = str(cam.attrs["distortion_model"])
            uv_clean = cam["points_2d_clean"][()]
            uv = cond["points_2d"][()]
            outliers = cond["outlier_mask"][()].astype(bool)

        uv_recomputed = project(X, K, coeffs, model, Rt[:3, :3], Rt[:3, 3])
        err = float(np.abs(uv_recomputed - uv_clean).max())
        worst = max(worst, err)
        inliers = ~outliers
        rms = float(np.sqrt(np.mean(np.sum((uv[inliers] - uv_clean[inliers]) ** 2, axis=1) / 2.0)))
        print(f"{model:16s} {len(idx):6d} {row.noise_sigma:6.2f} {int(outliers.sum()):9d} "
              f"{err:26.2e} {rms:16.4f}")

    print(f"\nlargest deviation from the stored ground truth: {worst:.2e} px")
    print("the per-coordinate inlier RMS is the condition's sigma, plus 1/sqrt(12) when quantized")


if __name__ == "__main__":
    main()
