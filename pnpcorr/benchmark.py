"""
Benchmark runner: stratified sample selection, solver execution and per-solve
metrics for three tasks.

* ``pnp``          calibrated pose estimation (K and distortion known);
                   observations are undistorted to the equivalent pinhole image
                   before solving, so every camera model is handled uniformly.
* ``calibration``  single-view uncalibrated DLT (K, R, t from raw pixels);
                   distortion is *not* modelled - the benchmark quantifies its bias.
* ``multiview``    multi-view calibration with OpenCV (calibrateCamera /
                   fisheye.calibrate) on the views that share one intrinsic set.

Results are plain pandas DataFrames with one row per solve.
"""
from __future__ import annotations

import math
import platform
import time
import zlib
from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

from ._version import __version__
from .cameras import Intrinsics, project_points_all, undistort_to_pinhole_pixels
from .metrics import (inlier_classification, intrinsic_errors, is_success, pose_metrics,
                      reprojection_rmse, reprojection_rmse_pinhole)
from .scenes import is_planar
from .solvers import (CALIBRATION_SOLVERS, HAVE_CV2, CalibrationEstimate, PoseEstimate, SolverSpec,
                      available_solvers, calibrate_multiview, calibrate_multiview_ba, dlt_uncalibrated)
from .storage import Sample, SampleReader

# Metric columns written as NaN when a solver returns nothing, so that a task in
# which every solve fails still produces a frame the summarisers can aggregate.
CALIBRATION_METRICS = ["rot_err_deg", "trans_err", "trans_err_rel", "center_err", "fx_err_pct",
                       "fy_err_pct", "cx_err_pct", "cy_err_pct", "cx_err_px", "cy_err_px",
                       "skew_err_px", "focal_err_pct", "reproj_rmse_px"]
MULTIVIEW_METRICS = ["rms_px", "fx_err_pct", "fy_err_pct", "cx_err_pct", "cy_err_pct", "cx_err_px",
                     "cy_err_px", "skew_err_px", "focal_err_pct", "dist_coeff_rmse", "rot_err_deg",
                     "trans_err_rel", "reproj_rmse_px"]

SAMPLE_FACTORS = [
    "sample_id", "file", "h5_path", "scene_id", "scene_type", "split", "scene_layout", "camera_id", "intrinsics_id",
    "camera_model", "fov_class", "hfov_deg", "distortion_level", "image_width", "image_height", "num_visible",
    "mean_depth", "condition_id", "condition_name", "noise_sigma", "quantize", "outlier_ratio", "outlier_type",
    "num_outliers",
]


# ----------------------------------------------------------------------------
# Sample selection
# ----------------------------------------------------------------------------
def select_samples(manifest: pd.DataFrame, max_samples: int = 2000, split: Optional[str] = None,
                   query: Optional[str] = None, seed: int = 0,
                   strata: Sequence[str] = ("scene_type", "camera_model", "fov_class", "condition_id")
                   ) -> pd.DataFrame:
    """
    Deterministic stratified subset of the manifest: every combination of the
    ``strata`` columns receives (about) the same number of samples, up to
    ``max_samples`` in total.  ``query`` is a pandas query string, e.g.
    ``"outlier_ratio == 0 and scene_type != 'planar_single'"``.
    """
    df = manifest
    if split:
        df = df[df["split"] == split]
    if query:
        df = df.query(query)
    if len(df) == 0:
        raise ValueError("no samples match the requested split/query")
    if max_samples is None or max_samples <= 0 or len(df) <= max_samples:
        return df.sort_values(["file", "h5_path"]).reset_index(drop=True)
    strata = [s for s in strata if s in df.columns]
    groups = df.groupby(strata, sort=True, observed=True)
    per_group = max(1, int(math.ceil(max_samples / groups.ngroups)))
    rng = np.random.default_rng(seed)
    picks = []
    for _, grp in groups:
        n = min(per_group, len(grp))
        picks.append(grp.sample(n=n, random_state=int(rng.integers(2**31 - 1))))
    out = pd.concat(picks)
    if len(out) > max_samples:
        out = out.sample(n=max_samples, random_state=seed)
    return out.sort_values(["file", "h5_path"]).reset_index(drop=True)


def ransac_threshold(policy: str, noise_sigma: float, quantize: bool) -> float:
    """``"auto"`` -> max(2 px, 3 sigma) (+0.5 px when quantized); otherwise a fixed value."""
    if str(policy).lower() == "auto":
        return max(2.0, 3.0 * float(noise_sigma)) + (0.5 if quantize else 0.0)
    return float(policy)


def parse_num_points(settings: Iterable[str]) -> List[Any]:
    out: List[Any] = []
    for s in settings:
        s = str(s).strip().lower()
        out.append("all" if s == "all" else int(s))
    return out


def _factor_row(row: pd.Series) -> Dict[str, Any]:
    return {k: row[k] for k in SAMPLE_FACTORS if k in row.index}


def _solver_seed(sample_key: Sequence[int], solver_name: str, setting: Any) -> int:
    """
    Deterministic RANSAC seed for one (sample, solver, subset size).

    It is derived from the sample, the solver's *name* and the subset size, never
    from the solver's position in the list being evaluated, so restricting a run
    with ``--solvers`` reproduces the numbers of a full run exactly.
    """
    name_key = zlib.crc32(f"{solver_name}|{setting}".encode("utf-8"))
    return int(np.random.default_rng(list(sample_key) + [1, int(name_key)]).integers(2 ** 31 - 1))


def environment_info() -> Dict[str, Any]:
    info = {
        "pnpcorr_version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "opencv": None,
    }
    if HAVE_CV2:
        import cv2
        info["opencv"] = cv2.__version__
    return info


# ----------------------------------------------------------------------------
# Task 1: calibrated PnP
# ----------------------------------------------------------------------------
def _prepare(sample: Sample):
    intr = sample.intrinsics
    uv_und, ok = undistort_to_pinhole_pixels(sample.uv, intr)
    uv_und = np.where(ok[:, None], uv_und, sample.uv)  # non-invertible observations keep raw coords
    return intr, uv_und, ok


def run_pnp_benchmark(data_dir, manifest_subset: pd.DataFrame, solver_names: Optional[Sequence[str]] = None,
                      num_points: Sequence[Any] = ("all",), threshold_policy: str = "auto", max_iters: int = 1000,
                      confidence: float = 0.99, seed: int = 0, success_rot_deg: float = 5.0,
                      success_trans_rel: float = 0.05, progress: bool = True) -> pd.DataFrame:
    specs: List[SolverSpec] = available_solvers(solver_names)
    rows: List[Dict[str, Any]] = []
    iterator = manifest_subset.iterrows()
    if progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(list(iterator), desc="pnp benchmark", unit="sample", dynamic_ncols=True)
        except ImportError:  # pragma: no cover
            pass
    with SampleReader(data_dir) as reader:
        for _, row in iterator:
            sample = reader.read(row)
            intr, uv_und, invertible = _prepare(sample)
            thr = ransac_threshold(threshold_policy, float(row["noise_sigma"]), bool(row["quantize"]))
            X_all = sample.X
            m = sample.num_visible
            # Both the point subsets and each solver's random seed must be a function
            # of the sample only, never of how many solvers are being evaluated, or
            # results from a --solvers run would not be comparable with a full run.
            # The subsets come from one stream keyed on the sample; a robust solver's
            # seed is keyed on the sample *and its own name*, so it does not depend on
            # the solver's position in the list.
            key = [seed, int(row["scene_id"]), int(row["camera_id"]), int(row["condition_id"])]
            subset_rng = np.random.default_rng(key + [0])
            for setting in num_points:
                if setting == "all":
                    idx = np.arange(m)
                else:
                    if int(setting) > m:
                        continue
                    idx = np.sort(subset_rng.choice(m, int(setting), replace=False))
                X = X_all[idx]
                uv = uv_und[idx]
                gt_out = sample.outlier_mask[idx]
                n = len(idx)
                planar = is_planar(X)
                gt_inl = ~gt_out
                depth_scale = float(sample.depths[idx][gt_inl].mean()) if gt_inl.any() else float(sample.depths[idx].mean())
                base = _factor_row(row)
                base.update({
                    "num_points_setting": str(setting), "num_points_used": int(n),
                    "num_outliers_used": int(gt_out.sum()),
                    "effective_outlier_ratio": float(gt_out.mean()),
                    "num_noninvertible": int((~invertible[idx]).sum()),
                    "subset_planar": bool(planar), "ransac_threshold": float(thr),
                })
                for spec in specs:
                    if n < spec.min_points or (spec.exact_points and n != spec.min_points):
                        continue
                    # Solvers restricted to (or excluded from) coplanar inputs are not
                    # skipped: they are called and decline, so every solver is scored
                    # over the same set of samples and the `returned (%)` column of one
                    # solver is directly comparable with another's.  The reason is
                    # recorded in `failure_reason` and tabulated by the analysis step.
                    rec = dict(base)
                    rec.update({"solver": spec.name, "family": spec.family, "robust": bool(spec.robust)})
                    reason = ""
                    t0 = time.perf_counter()
                    try:
                        est = spec.fn(X, uv, intr.K, threshold=thr, max_iters=max_iters, confidence=confidence,
                                      seed=_solver_seed(key, spec.name, setting))
                    except Exception as exc:  # solver crashed: record as failure
                        est = None
                        reason = f"exception: {type(exc).__name__}: {exc}"[:160]
                    runtime_ms = (time.perf_counter() - t0) * 1000.0
                    rec["runtime_ms"] = runtime_ms
                    if est is None or not est.ok:
                        rec.update({"ok": False, "failure_reason": (est.reason if est is not None else reason),
                                    "rot_err_deg": np.nan, "trans_err": np.nan, "trans_err_rel": np.nan,
                                    "center_err": np.nan, "reproj_rmse_px": np.nan, "success": False})
                        rec.update(inlier_classification(None, gt_out))
                        rows.append(rec)
                        continue
                    pm = pose_metrics(est.R, est.t, sample.R, sample.t, depth_scale)
                    rec.update({"ok": True, "failure_reason": ""})
                    rec.update(pm)
                    rec["reproj_rmse_px"] = reprojection_rmse(X, sample.uv_clean[idx], intr, est.R, est.t, mask=gt_inl)
                    rec["success"] = is_success(pm["rot_err_deg"], pm["trans_err_rel"], success_rot_deg, success_trans_rel)
                    rec.update(inlier_classification(est.inliers, gt_out))
                    rows.append(rec)
    df = pd.DataFrame(rows)
    return df


# ----------------------------------------------------------------------------
# Task 2: single-view uncalibrated DLT
# ----------------------------------------------------------------------------
def run_calibration_benchmark(data_dir, manifest_subset: pd.DataFrame, seed: int = 0,
                              progress: bool = True) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    iterator = manifest_subset.iterrows()
    if progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(list(iterator), desc="single-view calibration", unit="sample", dynamic_ncols=True)
        except ImportError:  # pragma: no cover
            pass
    with SampleReader(data_dir) as reader:
        for _, row in iterator:
            sample = reader.read(row)
            X = sample.X
            uv_raw = sample.uv
            gt_inl = ~sample.outlier_mask
            depth_scale = float(sample.depths[gt_inl].mean()) if gt_inl.any() else float(sample.depths.mean())
            base = _factor_row(row)
            base["num_points_used"] = int(len(X))
            base["subset_planar"] = bool(is_planar(X))
            for name, fn in CALIBRATION_SOLVERS.items():
                rec = dict(base)
                rec["solver"] = name
                t0 = time.perf_counter()
                try:
                    est = fn(X, uv_raw)
                except Exception as exc:  # a solver crash is recorded, never fatal
                    est = PoseEstimate(False, reason=f"exception: {type(exc).__name__}: {exc}"[:160])
                rec["runtime_ms"] = (time.perf_counter() - t0) * 1000.0
                if not est.ok:
                    rec.update({"ok": False, "failure_reason": est.reason, "success": False})
                    rec.update({k: np.nan for k in CALIBRATION_METRICS})
                    rows.append(rec)
                    continue
                rec.update({"ok": True, "failure_reason": ""})
                rec.update(pose_metrics(est.R, est.t, sample.R, sample.t, depth_scale))
                rec.update(intrinsic_errors(est.K, sample.K))
                rec["focal_err_pct"] = 0.5 * (rec["fx_err_pct"] + rec["fy_err_pct"])
                rec["reproj_rmse_px"] = reprojection_rmse_pinhole(X, sample.uv_clean, est.K, est.R, est.t, mask=gt_inl)
                rec["success"] = bool(np.isfinite(rec["focal_err_pct"]) and rec["focal_err_pct"] <= 5.0
                                      and rec["rot_err_deg"] <= 5.0)
                rows.append(rec)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Task 3: multi-view calibration (OpenCV)
# ----------------------------------------------------------------------------
def _distortion_rmse(est: np.ndarray, gt: np.ndarray, model: str) -> float:
    if model == "kannala_brandt":
        return float(np.sqrt(np.mean((np.asarray(est)[:4] - np.asarray(gt)[:4]) ** 2)))
    return float(np.sqrt(np.mean((np.asarray(est)[:5] - np.asarray(gt)[:5]) ** 2)))


def run_multiview_benchmark(data_dir, manifest_subset: pd.DataFrame, min_views: int = 3, max_rigs: int = 100,
                            seed: int = 0, methods: Sequence[str] = ("opencv", "ba_scratch"),
                            progress: bool = True) -> pd.DataFrame:
    """
    Groups views sharing (scene, intrinsics_id, condition) into calibration rigs
    and calibrates each rig with OpenCV (``calibrateCamera`` / ``fisheye.calibrate``)
    and with the from-scratch bundle adjustment.  Planar-target scenes are excluded
    (a single plane per rig leaves the intrinsics under-determined).
    """
    df = manifest_subset[manifest_subset["scene_type"] != "planar_single"]
    groups = [g for _, g in df.groupby(["file", "scene_id", "intrinsics_id", "condition_id"], sort=True) if len(g) >= min_views]
    rng = np.random.default_rng(seed)
    if len(groups) > max_rigs:
        keep = sorted(rng.choice(len(groups), max_rigs, replace=False).tolist())
        groups = [groups[i] for i in keep]
    rows: List[Dict[str, Any]] = []
    iterator = groups
    if progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(groups, desc="multi-view calibration", unit="rig", dynamic_ncols=True)
        except ImportError:  # pragma: no cover
            pass
    with SampleReader(data_dir) as reader:
        for grp in iterator:
            samples = [reader.read(r) for _, r in grp.iterrows()]
            first = samples[0]
            intr = first.intrinsics
            model = intr.model
            calib_model = "kannala_brandt" if model == "kannala_brandt" else "brown_conrady"
            views = [(s.X, s.uv) for s in samples]
            # Initial guess: single-view DLT on the first view, else a generic guess
            # (f = W, principal point at the image center).
            init = dlt_uncalibrated(first.X, first.uv)
            K0 = None
            if init.ok and 0.2 * intr.width < init.K[0, 0] < 20 * intr.width and 0.2 * intr.width < init.K[1, 1] < 20 * intr.width \
                    and 0 < init.K[0, 2] < intr.width and 0 < init.K[1, 2] < intr.height:
                K0 = init.K.copy()
                K0[0, 1] = 0.0
                init_source = "dlt"
            if K0 is None:
                K0 = np.array([[intr.width, 0.0, intr.width / 2.0], [0.0, intr.width, intr.height / 2.0], [0.0, 0.0, 1.0]])
                init_source = "generic"
            base = _factor_row(grp.iloc[0])
            base.update({"num_views": len(samples), "points_per_view": float(np.mean([len(s.X) for s in samples])),
                         "calibration_model": calib_model, "init_source": init_source})
            for method in methods:
                rec = dict(base)
                rec["solver"] = method
                if method not in ("opencv", "ba_scratch"):
                    raise ValueError(f"unknown multi-view method '{method}'")
                if method == "opencv" and not HAVE_CV2:
                    continue
                t0 = time.perf_counter()
                try:
                    # Both methods estimate `calib_model`: OpenCV's calibrateCamera
                    # always fits the 5 Brown-Conrady coefficients, so a pinhole rig is
                    # calibrated as Brown-Conrady by both, and the comparison is fair.
                    if method == "opencv":
                        est = calibrate_multiview(views, (intr.width, intr.height), K0, calib_model)
                    else:
                        est = calibrate_multiview_ba(views, (intr.width, intr.height), K0, calib_model)
                except Exception as exc:  # a solver crash is recorded, never fatal
                    est = CalibrationEstimate(False, reason=f"exception: {type(exc).__name__}: {exc}"[:160])
                rec["runtime_ms"] = (time.perf_counter() - t0) * 1000.0
                if not est.ok:
                    rec.update({"ok": False, "failure_reason": est.reason, "success": False})
                    rec.update({k: np.nan for k in MULTIVIEW_METRICS})
                    rows.append(rec)
                    continue
                rec.update({"ok": True, "failure_reason": "", "rms_px": est.rms})
                rec.update(intrinsic_errors(est.K, intr.K))
                rec["focal_err_pct"] = 0.5 * (rec["fx_err_pct"] + rec["fy_err_pct"])
                gt_coeffs = intr.coeffs if model != "pinhole" else np.zeros(5)
                est_model = calib_model
                est_dist = np.asarray(est.dist)
                rec["dist_coeff_rmse"] = _distortion_rmse(est_dist, gt_coeffs, calib_model)
                rot_errs, trans_errs, reproj = [], [], []
                est_intr = Intrinsics(est_model, est.K, est_dist, intr.width, intr.height)
                for s, (R, t) in zip(samples, est.poses):
                    gt_inl = ~s.outlier_mask
                    depth_scale = float(s.depths[gt_inl].mean())
                    pm = pose_metrics(R, t, s.R, s.t, depth_scale)
                    rot_errs.append(pm["rot_err_deg"])
                    trans_errs.append(pm["trans_err_rel"])
                    uv_est, _ = project_points_all(s.X[gt_inl], est_intr, R, t)
                    if np.isfinite(uv_est).all():
                        reproj.append(np.sqrt(np.mean(np.sum((uv_est - s.uv_clean[gt_inl]) ** 2, axis=1))))
                    else:
                        reproj.append(np.nan)
                rec["rot_err_deg"] = float(np.mean(rot_errs))
                rec["trans_err_rel"] = float(np.mean(trans_errs))
                rec["reproj_rmse_px"] = float(np.nanmean(reproj)) if np.isfinite(reproj).any() else np.nan
                rec["success"] = bool(rec["focal_err_pct"] <= 1.0 and rec["rot_err_deg"] <= 1.0)
                rows.append(rec)
    return pd.DataFrame(rows)
