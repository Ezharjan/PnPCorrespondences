#!/usr/bin/env python
"""
The three camera models, side by side: forward distortion, its inverse, the
injective domain, and agreement with OpenCV.

No dataset is needed - the script samples its own intrinsics from the default
configuration, so it also serves as a check that the projection code behaves as
README Sections 5.1 and 5.4 describe.

    python examples/02_camera_models_and_distortion.py
    python examples/02_camera_models_and_distortion.py --num-cameras 200
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.cameras import (BROWN_CONRADY, KANNALA_BRANDT, PINHOLE, corner_radius,  # noqa: E402
                             distort_points, in_valid_domain, project_points,
                             sample_intrinsics, undistort_points)
from pnpcorr.config import DEFAULTS  # noqa: E402

try:
    import cv2
except ImportError:                                # OpenCV is optional
    cv2 = None


def opencv_reference(points_3d, intr, R, t):
    """The same projection through OpenCV, or None when OpenCV is unavailable."""
    if cv2 is None:
        return None
    rvec, _ = cv2.Rodrigues(R)
    if intr.model == KANNALA_BRANDT:
        uv, _ = cv2.fisheye.projectPoints(points_3d.reshape(1, -1, 3), rvec, t, intr.K, intr.coeffs)
    else:
        uv, _ = cv2.projectPoints(points_3d, rvec, t, intr.K, intr.coeffs)
    return uv.reshape(-1, 2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--num-cameras", type=int, default=60, help="cameras to sample per model")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    cam_cfg = DEFAULTS["cameras"]
    per_model = {PINHOLE: [], BROWN_CONRADY: [], KANNALA_BRANDT: []}
    while min(len(v) for v in per_model.values()) < args.num_cameras:
        intr = sample_intrinsics(rng, cam_cfg)
        if len(per_model[intr.model]) < args.num_cameras:
            per_model[intr.model].append(intr)

    # A cloud in front of the camera, big enough to reach the image corners.
    pts = rng.uniform(-2.5, 2.5, (400, 3))
    pts[:, 2] += 5.0
    R, t = np.eye(3), np.zeros(3)

    print(f"{args.num_cameras} sampled cameras per model, {len(pts)} points each\n")
    print(f"{'model':16s} {'HFOV [deg]':>18s} {'domain / corner':>16s} "
          f"{'undistort err [px]':>19s} {'vs OpenCV [px]':>15s}")
    for model, cameras in per_model.items():
        fovs = [c.hfov_deg for c in cameras]
        domain_ratio, round_trip, cv_gap = [], 0.0, 0.0
        for intr in cameras:
            r_c = corner_radius(intr.K, intr.width, intr.height)
            limit = intr.valid_radius if model != KANNALA_BRANDT else math.tan(min(intr.valid_radius, 1.5))
            domain_ratio.append(min(limit / r_c, 10.0) if np.isfinite(limit) else 10.0)

            # Exactly the points the dataset would store: in front of the camera,
            # inside the invertible domain and on the sensor.
            proj = project_points(pts, intr, R, t)
            if len(proj.indices) < 5:
                continue
            pc = pts[proj.indices]
            # distort -> undistort must return the normalised point it started from
            xn, yn = pc[:, 0] / pc[:, 2], pc[:, 1] / pc[:, 2]
            xd, yd = distort_points(xn, yn, intr.model, intr.coeffs)
            xb, yb, ok = undistort_points(xd, yd, intr.model, intr.coeffs, intr.valid_radius)
            if ok.any():
                round_trip = max(round_trip, float(np.max(np.hypot(xb[ok] - xn[ok], yb[ok] - yn[ok])) * intr.fx))

            ref = opencv_reference(pc, intr, R, t)
            if ref is not None and intr.skew == 0.0:
                # cv2.projectPoints ignores K[0, 1]; only skew-free cameras are comparable.
                cv_gap = max(cv_gap, float(np.abs(proj.uv - ref).max()))
        cv_text = f"{cv_gap:15.2e}" if cv2 is not None else f"{'(not installed)':>15s}"
        print(f"{model:16s} {min(fovs):7.1f} - {max(fovs):6.1f} {np.mean(domain_ratio):16.2f} "
              f"{round_trip:19.2e} {cv_text}")

    print("\n'domain / corner' is the injective radius over the image-corner radius; the "
          "generator\nrequires at least "
          f"{cam_cfg['min_valid_corner_fraction']:.2f} and reports 10.00 for an unbounded (pinhole) domain.")
    print("'vs OpenCV' compares only the points a dataset would store - in front of the camera,\n"
          "inside the invertible domain and on the sensor - which is where the model is defined.")

    # Where the domain actually bites: a strongly distorted Brown-Conrady camera.
    strong = max((c for c in per_model[BROWN_CONRADY]), key=lambda c: -c.valid_radius)
    r_c = corner_radius(strong.K, strong.width, strong.height)
    radii = np.linspace(0.2 * r_c, 2.0 * r_c, 9)
    inside = in_valid_domain(radii, np.zeros_like(radii), strong)
    print(f"\nmost restricted Brown-Conrady camera of the sample: valid_radius = {strong.valid_radius:.4f}, "
          f"corner radius = {r_c:.4f}")
    print("  r / r_corner :", "  ".join(f"{r / r_c:5.2f}" for r in radii))
    print("  invertible   :", "  ".join(f"{'yes' if b else ' no':>5s}" for b in inside))


if __name__ == "__main__":
    main()
