#!/usr/bin/env python
"""
What each noise condition does to one view.

Every camera view is stored under all the noise conditions of the configuration,
and they share the same geometry, so the conditions of a single camera are a
controlled experiment: the only thing that changes between them is the
perturbation.  This script prints that experiment for one view and checks the
statistics against the model of README Section 5.6.

    python examples/03_noise_conditions.py --data data
    python examples/03_noise_conditions.py --data data --scene-type planar_multi
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.storage import SampleReader, load_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data", help="dataset directory")
    parser.add_argument("--scene-type", default=None, help="restrict to one scene family")
    parser.add_argument("--camera-model", default=None, help="restrict to one camera model")
    args = parser.parse_args()

    manifest = load_manifest(args.data)
    view = manifest
    if args.scene_type:
        view = view[view["scene_type"] == args.scene_type]
    if args.camera_model:
        view = view[view["camera_model"] == args.camera_model]
    if view.empty:
        sys.exit("no view matches the requested scene type / camera model")
    # All conditions of a single camera: same 3D points, same pose, same intrinsics.
    first = view.iloc[0]
    view = view[(view["file"] == first["file"]) & (view["scene_id"] == first["scene_id"])
                & (view["camera_id"] == first["camera_id"])].sort_values("condition_id")

    with SampleReader(args.data) as reader:
        samples = [(row, reader.read(row)) for _, row in view.iterrows()]

    row0, s0 = samples[0]
    print(f"scene    : {row0['scene_type']} #{row0['scene_id']}, {s0.points_3d.shape[0]} 3D points, "
          f"split={row0['split']}")
    print(f"camera   : {row0['camera_model']}, {row0['image_width']}x{row0['image_height']}, "
          f"HFOV {row0['hfov_deg']:.1f} deg, distortion={row0['distortion_level']}")
    print(f"view     : {s0.num_visible} visible correspondences, mean depth {row0['mean_depth']:.2f} m")
    print(f"\n{len(samples)} conditions on this one geometry:\n")
    print(f"{'id':>3s} {'condition':26s} {'outliers':>9s} {'inlier RMS':>11s} {'expected':>9s} "
          f"{'inlier max':>11s} {'outlier med':>12s} {'on grid':>8s}")

    for row, s in samples:
        inl = ~s.outlier_mask
        resid = s.uv[inl] - s.uv_clean[inl]
        rms = float(np.sqrt(np.mean(resid ** 2))) if inl.any() else float("nan")
        sigma = float(row["noise_sigma"])
        quant = bool(row["quantize"])
        # Rounding adds an independent U(-1/2, 1/2), so the variances add.
        expected = math.sqrt(sigma ** 2 + (1.0 / 12.0 if quant else 0.0))
        out_disp = (float(np.median(np.linalg.norm(s.uv[s.outlier_mask] - s.uv_clean[s.outlier_mask], axis=1)))
                    if s.outlier_mask.any() else float("nan"))
        on_grid = bool(np.array_equal(s.uv, np.round(s.uv)))
        print(f"{int(row['condition_id']):3d} {row['condition_name']:26s} "
              f"{int(s.outlier_mask.sum()):4d} ({100 * float(row['outlier_ratio']):3.0f}%) "
              f"{rms:11.4f} {expected:9.4f} {np.abs(resid).max() if inl.any() else float('nan'):11.4f} "
              f"{out_disp:12.1f} {'yes' if on_grid else 'no':>8s}")

    print("\nreading the columns:")
    print("  inlier RMS   per-coordinate RMS of (observation - clean projection) over the inliers")
    print("  expected     sqrt(sigma^2 + 1/12) when quantized, sigma otherwise")
    print("  inlier max   largest single-coordinate deviation; it grows like sqrt(2 ln N) with the")
    print("               number of correspondences, which is why the validator uses a sample-size-")
    print("               aware bound rather than a fixed multiple of sigma")
    print("  outlier med  median pixel distance between an outlier observation and the clean")
    print("               projection of the 3D point it is paired with - hundreds of pixels, i.e.")
    print("               unambiguously separated from the noise")


if __name__ == "__main__":
    main()
