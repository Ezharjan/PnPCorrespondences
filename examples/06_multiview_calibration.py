#!/usr/bin/env python
"""
Recover the intrinsics and the lens distortion of one camera from the views that
share it - the classic multi-view calibration problem - and compare the result
with the exact ground truth the dataset stores.

Views that share an `intrinsics_id` inside a scene were produced by literally the
same camera, so a group of them is a calibration rig.  Two estimators are run on
it: OpenCV's `calibrateCamera` / `fisheye.calibrate`, and the from-scratch sparse
bundle adjustment in `pnpcorr.solvers`.

    python examples/06_multiview_calibration.py --data data
    python examples/06_multiview_calibration.py --data data --camera-model kannala_brandt --num-cameras 3
    python examples/06_multiview_calibration.py --data data --sigmas 0.0,0.5,2.0
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.metrics import intrinsic_errors, pose_metrics  # noqa: E402
from pnpcorr.solvers import HAVE_CV2, calibrate_multiview, calibrate_multiview_ba, dlt_uncalibrated  # noqa: E402
from pnpcorr.storage import SampleReader, load_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data", help="dataset directory")
    parser.add_argument("--camera-model", default=None, choices=["pinhole", "brown_conrady", "kannala_brandt"])
    parser.add_argument("--num-cameras", type=int, default=2, help="distinct cameras to calibrate")
    parser.add_argument("--min-views", type=int, default=3)
    parser.add_argument("--sigmas", default=None,
                        help="comma-separated noise levels to calibrate at (default: 0 and the largest available)")
    args = parser.parse_args()

    manifest = load_manifest(args.data)
    # Outlier-free, non-quantized, non-planar: a single plane per rig leaves the
    # intrinsics under-determined, and mismatches are a different experiment.
    pool = manifest[(manifest["outlier_ratio"] == 0) & (~manifest["quantize"].astype(bool))
                    & (manifest["scene_type"] != "planar_single")]
    if args.camera_model:
        pool = pool[pool["camera_model"] == args.camera_model]
    if pool.empty:
        sys.exit(f"no outlier-free, non-quantized, non-planar view left after filtering"
                 f"{' for camera_model = ' + args.camera_model if args.camera_model else ''}; "
                 f"this dataset has {sorted(manifest['camera_model'].unique())}")
    # Which noise levels to calibrate at.  The default pairs the exact case, where both
    # estimators should be exact, with the noisiest available, where the conditioning of
    # the problem - and the difference between the two - actually shows.
    available = sorted(float(v) for v in pool["noise_sigma"].unique())
    if args.sigmas:
        try:
            sigmas = [float(v) for v in args.sigmas.split(",") if v.strip()]
        except ValueError:
            sys.exit("--sigmas must be a comma-separated list of numbers, e.g. 0.0,0.5,2.0")
        missing = [v for v in sigmas if v not in available]
        if not sigmas or missing:
            sys.exit(f"noise sigma {missing or 'list is empty'}; this dataset has {available}")
    else:
        sigmas = sorted({available[0], available[-1]})
    pool = pool[pool["noise_sigma"].isin(sigmas)]

    rigs = [g for _, g in pool.groupby(["file", "scene_id", "intrinsics_id", "condition_id"], sort=True)
            if len(g) >= args.min_views]
    if not rigs:
        sys.exit(f"no rig with at least {args.min_views} views; increase cameras.num_poses_per_intrinsics")
    # Group the rigs by camera, so each block below is one physical camera seen at every
    # requested noise level rather than a different camera each time.
    by_camera: "dict[tuple, list]" = {}
    for rig in rigs:
        key = (rig.iloc[0]["file"], int(rig.iloc[0]["scene_id"]), int(rig.iloc[0]["intrinsics_id"]))
        by_camera.setdefault(key, []).append(rig)
    cameras = [sorted(v, key=lambda g: float(g.iloc[0]["noise_sigma"])) for v in by_camera.values()]

    print(f"{len(cameras)} distinct cameras with at least {args.min_views} views; "
          f"calibrating {min(args.num_cameras, len(cameras))} of them at sigma = "
          f"{', '.join(str(v) for v in sigmas)} px\n")
    with SampleReader(args.data) as reader:
        for rig in [g for cam_rigs in cameras[:args.num_cameras] for g in cam_rigs]:
            samples = [reader.read(row) for _, row in rig.iterrows()]
            first = samples[0]
            intr = first.intrinsics
            model = "kannala_brandt" if intr.model == "kannala_brandt" else "brown_conrady"
            views = [(s.X, s.uv) for s in samples]

            # Intrinsic guess: the single-view uncalibrated DLT when it is sane,
            # otherwise a generic f = W guess with the principal point at the centre.
            init = dlt_uncalibrated(first.X, first.uv)
            plausible = (init.ok and 0.2 * intr.width < init.K[0, 0] < 20 * intr.width
                         and 0 < init.K[0, 2] < intr.width and 0 < init.K[1, 2] < intr.height)
            if plausible:
                K0 = init.K.copy()
                K0[0, 1] = 0.0
                source = "single-view DLT"
            else:
                K0 = np.array([[intr.width, 0.0, intr.width / 2.0],
                               [0.0, intr.width, intr.height / 2.0], [0.0, 0.0, 1.0]])
                source = "generic (f = W)"

            print(f"rig: {rig.iloc[0]['scene_type']} scene #{int(rig.iloc[0]['scene_id'])}, "
                  f"intrinsics #{int(rig.iloc[0]['intrinsics_id'])}, {len(views)} views, "
                  f"{np.mean([len(X) for X, _ in views]):.0f} points/view, "
                  f"condition {rig.iloc[0]['condition_name']}")
            print(f"  true camera : {intr.model} ({intr.distortion_level}), {intr.width}x{intr.height}, "
                  f"HFOV {intr.hfov_deg:.1f} deg, calibrated as {model}")
            print(f"  fx {intr.fx:10.3f}   fy {intr.fy:10.3f}   cx {intr.cx:9.3f}   cy {intr.cy:9.3f}")
            print(f"  initial guess from {source}: fx {K0[0, 0]:.1f}, cx {K0[0, 2]:.1f}, cy {K0[1, 2]:.1f}")
            print(f"  {'method':12s} {'fx err %':>9s} {'fy err %':>9s} {'cx err px':>10s} {'cy err px':>10s} "
                  f"{'dist RMSE':>10s} {'rot err deg':>12s} {'rms px':>8s}")

            methods = [("ba_scratch", calibrate_multiview_ba)]
            if HAVE_CV2:
                methods.insert(0, ("opencv", calibrate_multiview))
            gt_coeffs = intr.coeffs if intr.model != "pinhole" else np.zeros(5)
            for name, fn in methods:
                est = fn(views, (intr.width, intr.height), K0, model)
                if not est.ok:
                    print(f"  {name:12s} failed: {est.reason}")
                    continue
                err = intrinsic_errors(est.K, intr.K)
                n = 4 if model == "kannala_brandt" else 5
                dist_rmse = float(np.sqrt(np.mean((np.asarray(est.dist)[:n] - np.asarray(gt_coeffs)[:n]) ** 2)))
                rot = float(np.mean([pose_metrics(R, t, s.R, s.t, 1.0)["rot_err_deg"]
                                     for s, (R, t) in zip(samples, est.poses)]))
                print(f"  {name:12s} {err['fx_err_pct']:9.4f} {err['fy_err_pct']:9.4f} "
                      f"{err['cx_err_px']:10.3f} {err['cy_err_px']:10.3f} {dist_rmse:10.2e} "
                      f"{rot:12.4f} {est.rms:8.3f}")
            print()

    print("`dist RMSE` is against the exact coefficients that produced the observations, which is")
    print("only possible because there is no image formation step between them and the data.")
    print("At sigma = 0 the from-scratch bundle adjustment is exact on every rig, which is the check")
    print("that the pipeline and the ground truth agree.  OpenCV lands within a hundredth of a pixel")
    print("on pinhole and Brown-Conrady rigs, but `cv2.fisheye.calibrate` initialises its extrinsics")
    print("assuming a planar target, so it can fail outright on a non-planar Kannala-Brandt rig even")
    print("with no noise at all - the case README Section 9.6 quantifies as 43 % success against 86 %.")
    print("Under noise the conditioning of the problem shows: a narrow field of view makes the")
    print("principal point nearly unobservable, so the cx / cy columns grow by orders of magnitude")
    print("while the reprojection rms stays at the noise level - a small residual is not evidence")
    print("of a well-determined camera.")


if __name__ == "__main__":
    main()
