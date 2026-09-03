"""
Dataset validation: structural, numerical and statistical consistency checks.

Every check either passes or records a failure message; the report lists the
number of checks performed per category and the failures found.  The
``regenerate`` option re-runs the generator for a few scenes from the stored
configuration and compares the arrays bit-for-bit (reproducibility check).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import h5py
import numpy as np

from .cameras import Intrinsics, project_points
from .config import expand_conditions, load_config, scene_specs
from .generate import generate_scene_record
from .scenes import is_planar
from .storage import load_manifest, load_stats, read_attrs


class Report:
    def __init__(self) -> None:
        self.checks: Dict[str, int] = {}
        self.failures: List[str] = []

    def check(self, category: str, ok: bool, message: str = "") -> bool:
        self.checks[category] = self.checks.get(category, 0) + 1
        if not ok:
            self.failures.append(f"[{category}] {message}")
        return bool(ok)

    def as_dict(self) -> Dict[str, Any]:
        return {"checks": self.checks, "num_checks": int(sum(self.checks.values())),
                "num_failures": len(self.failures), "failures": self.failures[:200], "passed": not self.failures}


def _validate_camera(rep: Report, cam_grp, scene_pts: np.ndarray, min_depth: float, label: str) -> None:
    attrs = read_attrs(cam_grp)
    K = cam_grp["K"][()]
    coeffs = cam_grp["dist_coeffs"][()]
    Rt = cam_grp["pose_Rt"][()]
    C = cam_grp["camera_center"][()]
    uv_clean = cam_grp["points_2d_clean"][()]
    idx = cam_grp["point_indices"][()]
    depths = cam_grp["depths"][()]
    model = attrs["distortion_model"]
    W, H = int(attrs["image_width"]), int(attrs["image_height"])
    rep.check("shapes", K.shape == (3, 3) and Rt.shape == (4, 4) and uv_clean.shape == (len(idx), 2)
              and depths.shape == (len(idx),) and C.shape == (3,), f"{label}: array shapes")
    rep.check("dtypes", uv_clean.dtype == np.float64 and idx.dtype == np.int32 and K.dtype == np.float64,
              f"{label}: dtypes")
    rep.check("coeffs", coeffs.shape[0] == (4 if model == "kannala_brandt" else 5), f"{label}: coefficient count for {model}")
    R, t = Rt[:3, :3], Rt[:3, 3]
    rep.check("rotation", np.allclose(R @ R.T, np.eye(3), atol=1e-10) and abs(np.linalg.det(R) - 1) < 1e-10,
              f"{label}: R not a proper rotation")
    rep.check("rotation", np.allclose(Rt[3], [0, 0, 0, 1]), f"{label}: last row of pose_Rt")
    rep.check("center", np.allclose(C, -R.T @ t, atol=1e-9), f"{label}: camera_center != -R^T t")
    rep.check("intrinsics", K[1, 0] == 0 and K[2, 0] == 0 and K[2, 1] == 0 and K[2, 2] == 1 and K[0, 0] > 0 and K[1, 1] > 0,
              f"{label}: K structure")
    half = math.radians(float(attrs["hfov_deg"])) / 2
    fx_expected = (W / 2) / half if model == "kannala_brandt" else (W / 2) / math.tan(half)
    rep.check("intrinsics", abs(K[0, 0] - fx_expected) <= 1e-9 * fx_expected, f"{label}: fx inconsistent with hfov_deg")
    rep.check("indices", len(np.unique(idx)) == len(idx) and (idx >= 0).all() and (idx < len(scene_pts)).all()
              and (np.diff(idx) > 0).all(), f"{label}: point_indices not sorted/unique/in range")
    rep.check("bounds", (uv_clean[:, 0] >= 0).all() and (uv_clean[:, 0] < W).all() and (uv_clean[:, 1] >= 0).all()
              and (uv_clean[:, 1] < H).all(), f"{label}: clean projections outside the image")
    rep.check("depth", (depths > min_depth).all(), f"{label}: depth <= min_depth")
    intr = Intrinsics.from_arrays(K, coeffs, attrs)
    proj = project_points(scene_pts, intr, R, t, min_depth=min_depth)
    same = (proj.indices.shape == idx.shape and np.array_equal(proj.indices, idx)
            and np.allclose(proj.uv, uv_clean, atol=1e-9) and np.allclose(proj.depth, depths, atol=1e-9))
    rep.check("reprojection", same, f"{label}: stored projections differ from the ground-truth re-projection")
    rep.check("attrs", int(attrs["num_visible"]) == len(idx), f"{label}: num_visible attr")


def max_deviation_sigmas(num_values: int, alpha: float = 1e-9) -> float:
    """
    Upper bound on ``max |Z|`` over ``num_values`` independent standard normals
    that is exceeded with probability at most ``alpha``.

    A fixed multiple of sigma (e.g. 6) is *not* a valid bound: the largest of
    N standard normals grows like ``sqrt(2 ln N)``, so a dataset with 10^8
    correspondences would fail a 6-sigma test by construction.  The classical
    tail bound ``P(|Z| > z) <= exp(-z^2 / 2)`` gives the (conservative) value
    ``z = sqrt(2 ln(N / alpha))``; it is never allowed below 6.
    """
    n = max(int(num_values), 1)
    return max(6.0, math.sqrt(2.0 * math.log(n / max(alpha, 1e-300))))


def _validate_condition(rep: Report, cond_grp, uv_clean: np.ndarray, W: int, H: int, label: str) -> None:
    attrs = read_attrs(cond_grp)
    uv = cond_grp["points_2d"][()]
    mask = cond_grp["outlier_mask"][()].astype(bool)
    m = len(uv_clean)
    sigma = float(attrs["noise_sigma"])
    ratio = float(attrs["outlier_ratio"])
    quant = bool(attrs["quantize"])
    otype = str(attrs["outlier_type"])
    rep.check("shapes", uv.shape == (m, 2) and mask.shape == (m,), f"{label}: condition array shapes")
    rep.check("outliers", int(mask.sum()) == int(attrs["num_outliers"]) == int(m * ratio), f"{label}: outlier count")
    inl = ~mask
    residual = uv[inl] - uv_clean[inl]          # signed noise of the inlier observations
    dev = np.abs(residual)
    n_values = int(residual.size)
    z_max = max_deviation_sigmas(n_values)
    tol = z_max * sigma + (0.5 if quant else 0.0) + 1e-9
    rep.check("noise", bool(dev.max() <= tol) if inl.any() else True,
              f"{label}: inlier deviation {dev.max() if inl.any() else 0:.3f} > {tol:.3f} "
              f"({z_max:.2f} sigma over {n_values} values)")
    # Statistical check of the noise level itself.  The RMS of N zero-mean
    # Gaussian residuals estimates sigma with relative standard error
    # 1 / sqrt(2 N), so an 8-standard-error band is both extremely unlikely to
    # trip and far more sensitive than the maximum-deviation bound above.
    if sigma > 0 and not quant and n_values >= 200:
        rms = float(np.sqrt(np.mean(residual ** 2)))
        rel = rms / sigma - 1.0
        band = max(0.02, 8.0 / math.sqrt(2.0 * n_values))
        rep.check("noise", abs(rel) <= band,
                  f"{label}: inlier noise RMS is {rel * 100:+.1f} % off sigma (band +-{band * 100:.1f} %)")
    if sigma == 0 and not quant:
        rep.check("noise", np.array_equal(uv[inl], uv_clean[inl]), f"{label}: sigma = 0 inliers are not exact")
    if quant:
        rep.check("quantization", np.array_equal(uv, np.round(uv)), f"{label}: quantized coordinates are not integers")
    if mask.any():
        if otype == "uniform" and not quant:
            rep.check("outliers", (uv[mask, 0] >= 0).all() and (uv[mask, 0] < W).all() and (uv[mask, 1] >= 0).all()
                      and (uv[mask, 1] < H).all(), f"{label}: uniform outliers outside the image")
        moved = np.abs(uv[mask] - uv_clean[mask]).sum(axis=1) > 0
        rep.check("outliers", bool(moved.all()) if sigma == 0 else True, f"{label}: an outlier kept its clean coordinates")
        if otype == "swap" and sigma == 0 and not quant:
            # swapped observations are a permutation of the selected clean observations
            rep.check("outliers", np.allclose(np.sort(uv[mask], axis=0), np.sort(uv_clean[mask], axis=0)),
                      f"{label}: swapped observations are not a permutation")


def validate_dataset(data_dir: "str | Path", max_cameras: Optional[int] = None, regenerate: int = 1,
                     seed: int = 0, progress: bool = True, log=print) -> Dict[str, Any]:
    data_dir = Path(data_dir)
    rep = Report()
    manifest = load_manifest(data_dir)
    stats = load_stats(data_dir)
    csv_rows = sum(1 for _ in open(data_dir / "manifest.csv", "r", encoding="utf-8")) - 1
    rep.check("manifest", len(manifest) == csv_rows == stats["num_samples"],
              f"manifest rows {len(manifest)} / csv {csv_rows} / stats {stats['num_samples']} disagree")
    rep.check("manifest", manifest["sample_id"].is_unique, "duplicate sample_id in manifest")
    for f in stats["files"]:
        rep.check("files", (data_dir / "hdf5" / f).exists(), f"missing file hdf5/{f}")
    cfg = load_config(data_dir / "metadata" / "config_used.yaml")
    min_depth = float(cfg["cameras"]["min_depth"])
    n_conditions = len(expand_conditions(cfg))

    cameras = manifest.drop_duplicates(["file", "scene_id", "camera_id"])
    if max_cameras is not None and len(cameras) > max_cameras:
        cameras = cameras.sample(n=max_cameras, random_state=seed)
    cameras = cameras.sort_values(["file", "h5_path"])
    iterator = cameras.iterrows()
    if progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(list(iterator), desc="validating cameras", unit="camera", dynamic_ncols=True)
        except ImportError:  # pragma: no cover
            pass
    open_files: Dict[str, h5py.File] = {}
    checked_scenes = set()
    try:
        for _, row in iterator:
            f = open_files.get(row["file"])
            if f is None:
                f = open_files[row["file"]] = h5py.File(data_dir / row["file"], "r")
            cond_grp = f[row["h5_path"]]
            cam_grp = cond_grp.parent
            scene_grp = cam_grp.parent
            label = f"{row['file']}:{cam_grp.name}"
            pts = scene_grp["points_3d"][()]
            if scene_grp.name not in checked_scenes:
                checked_scenes.add(scene_grp.name)
                sattrs = read_attrs(scene_grp)
                labels = scene_grp["point_labels"][()]
                rep.check("scene", pts.shape == (int(sattrs["num_points"]), 3) and labels.shape == (len(pts),),
                          f"{label}: scene shapes")
                rep.check("scene", np.isfinite(pts).all(), f"{label}: non-finite 3D points")
                st = sattrs["scene_type"]
                if st == "planar_single":
                    rep.check("scene", is_planar(pts) and (labels == 0).all(), f"{label}: planar_single is not planar")
                elif st in ("planar_multi", "mixed"):
                    for k in range(int(sattrs["num_planes"])):
                        rep.check("scene", is_planar(pts[labels == k]), f"{label}: plane {k} of {st} is not planar")
                    rep.check("scene", not is_planar(pts), f"{label}: {st} scene is degenerate (planar)")
                else:
                    rep.check("scene", not is_planar(pts) and (labels == -1).all(), f"{label}: {st} labels/planarity")
                rep.check("scene", int(sattrs["num_cameras"]) == len(
                    manifest[(manifest["file"] == row["file"]) & (manifest["scene_id"] == row["scene_id"])].drop_duplicates("camera_id")),
                    f"{label}: num_cameras attr vs manifest")
            _validate_camera(rep, cam_grp, pts, min_depth, label)
            uv_clean = cam_grp["points_2d_clean"][()]
            cattrs = read_attrs(cam_grp)
            W, H = int(cattrs["image_width"]), int(cattrs["image_height"])
            cond_names = [k for k in cam_grp.keys() if k.startswith("condition_")]
            rep.check("conditions", len(cond_names) == n_conditions == int(cattrs["num_conditions"]),
                      f"{label}: expected {n_conditions} conditions, found {len(cond_names)}")
            for cname in cond_names:
                _validate_condition(rep, cam_grp[cname], uv_clean, W, H, f"{label}/{cname}")
            # manifest consistency for this camera
            rep.check("manifest", row["camera_model"] == cattrs["distortion_model"] and int(row["num_visible"]) == len(uv_clean)
                      and int(row["image_width"]) == W, f"{label}: manifest row disagrees with attrs")
    finally:
        for f in open_files.values():
            f.close()

    # Reproducibility: regenerate a few scenes and compare bit-for-bit.
    if regenerate > 0:
        specs = scene_specs(cfg)
        rng = np.random.default_rng(seed)
        pick = rng.choice(len(specs), min(regenerate, len(specs)), replace=False)
        for i in pick:
            spec = specs[int(i)]
            rec = generate_scene_record(spec, cfg)
            rows = manifest[manifest["scene_id"] == spec["scene_id"]]
            if rows.empty:
                rep.check("reproducibility", False, f"scene {spec['scene_id']} missing from manifest")
                continue
            with h5py.File(data_dir / rows.iloc[0]["file"], "r") as f:
                sg = f[f"scene_{spec['scene_id']:05d}"]
                same = np.array_equal(sg["points_3d"][()], rec["points_3d"])
                for cam in rec["cameras"]:
                    cg = sg[f"camera_{cam['camera_id']:03d}"]
                    same &= np.array_equal(cg["points_2d_clean"][()], cam["points_2d_clean"])
                    same &= np.array_equal(cg["pose_Rt"][()], cam["pose_Rt"])
                    for cond in cam["conditions"]:
                        dg = cg[f"condition_{cond['condition_id']:03d}"]
                        same &= np.array_equal(dg["points_2d"][()], cond["points_2d"])
                        same &= np.array_equal(dg["outlier_mask"][()], cond["outlier_mask"])
                rep.check("reproducibility", bool(same), f"scene {spec['scene_id']} could not be regenerated bit-for-bit")

    report = rep.as_dict()
    report["cameras_validated"] = int(len(cameras))
    report["scenes_validated"] = int(len(checked_scenes))
    if log:
        log(f"validated {report['cameras_validated']} cameras in {report['scenes_validated']} scenes: "
            f"{report['num_checks']} checks, {report['num_failures']} failures")
        for msg in report["failures"][:20]:
            log("  FAIL " + msg)
    return report
