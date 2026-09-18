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
from scipy.spatial import cKDTree

from .cameras import Intrinsics, project_points
from .config import expand_conditions, load_config, scene_specs
from .generate import generate_scene_record
from .noise import num_outliers
from .scenes import is_planar
from .storage import compute_dataset_stats, load_manifest, load_stats, read_attrs


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
    rep.check("coeffs", np.isfinite(coeffs).all(), f"{label}: non-finite distortion coefficients")
    if model == "pinhole":
        # A pinhole camera must carry zeros: distort_points ignores the coefficients
        # for this model, so a non-zero value would never show up in the projection.
        rep.check("coeffs", not coeffs.any(), f"{label}: pinhole camera has non-zero dist_coeffs")
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

    A fixed multiple of sigma cannot serve as a bound here: the largest of N
    standard normals grows like ``sqrt(2 ln N)``, so any constant threshold is
    exceeded once the dataset is large enough.  The classical tail bound
    ``P(|Z| > z) <= exp(-z^2 / 2)`` gives the (conservative) value
    ``z = sqrt(2 ln(N / alpha))``; it is never allowed below 6.
    """
    n = max(int(num_values), 1)
    return max(6.0, math.sqrt(2.0 * math.log(n / max(alpha, 1e-300))))


def _validate_condition(rep: Report, cond_grp, attrs: Dict[str, Any], uv_clean: np.ndarray,
                        W: int, H: int, label: str) -> None:
    uv = cond_grp["points_2d"][()]
    mask = cond_grp["outlier_mask"][()].astype(bool)
    m = len(uv_clean)
    sigma = float(attrs["noise_sigma"])
    ratio = float(attrs["outlier_ratio"])
    quant = bool(attrs["quantize"])
    otype = str(attrs["outlier_type"])
    rep.check("shapes", uv.shape == (m, 2) and mask.shape == (m,), f"{label}: condition array shapes")
    rep.check("shapes", np.isfinite(uv).all(), f"{label}: non-finite observations")
    expected_outliers = num_outliers(m, ratio)
    rep.check("outliers", int(mask.sum()) == int(attrs["num_outliers"]) == expected_outliers,
              f"{label}: outlier count {int(mask.sum())} / attr {int(attrs['num_outliers'])} / "
              f"expected {expected_outliers}")
    inl = ~mask
    residual = uv[inl] - uv_clean[inl]          # signed noise of the inlier observations
    dev = np.abs(residual)
    n_values = int(residual.size)
    z_max = max_deviation_sigmas(n_values)
    tol = z_max * sigma + (0.5 if quant else 0.0) + 1e-9
    rep.check("noise", bool(dev.max() <= tol) if inl.any() else True,
              f"{label}: inlier deviation {dev.max() if inl.any() else 0:.3f} > {tol:.3f} "
              f"({z_max:.2f} sigma over {n_values} values)")
    if quant:
        rep.check("quantization", np.array_equal(uv, np.round(uv)), f"{label}: quantized coordinates are not integers")

    # -- value checks on the inlier noise ------------------------------------
    # At sigma = 0 the observation is a deterministic function of the clean
    # projection, so it is checked exactly rather than statistically.  Rounding
    # error is not a random sample: the fractional parts of a projected grid are
    # correlated, so its mean and variance depend on the scene geometry.
    if sigma == 0:
        expected = np.round(uv_clean[inl]) if quant else uv_clean[inl]
        rep.check("noise", np.array_equal(uv[inl], expected),
                  f"{label}: sigma = 0 inliers are not {'round(clean)' if quant else 'exactly clean'}")
    elif n_values >= 30:
        # With sigma > 0 the Gaussian term dominates and dithers the rounding, so
        # the residual is a genuine random sample.  Rounding contributes an
        # independent U(-1/2, 1/2), hence a variance of sigma^2 + 1/12.
        expected_rms = math.sqrt(sigma ** 2 + (1.0 / 12.0 if quant else 0.0))
        rms = float(np.sqrt(np.mean(residual ** 2)))
        band = max(0.02, 8.0 / math.sqrt(2.0 * n_values)) + (0.01 if quant else 0.0)
        rep.check("noise", abs(rms / expected_rms - 1.0) <= band,
                  f"{label}: inlier residual RMS {rms:.4f} is {100 * (rms / expected_rms - 1):+.1f} % off the "
                  f"expected {expected_rms:.4f} (band +-{100 * band:.1f} %)")
        # Zero mean: a constant offset shifts the mean by many standard errors
        # even when the RMS still looks plausible.  The standard error is taken
        # from the observed spread so that the test does not depend on the model.
        se = rms / math.sqrt(n_values)
        rep.check("noise", abs(float(residual.mean())) <= 8.0 * se + 1e-9,
                  f"{label}: inlier noise mean {residual.mean():+.4f} exceeds 8 standard errors ({8 * se:.4f})")

    # -- outliers ------------------------------------------------------------
    if mask.any():
        if otype == "uniform" and not quant:
            rep.check("outliers", (uv[mask, 0] >= 0).all() and (uv[mask, 0] < W).all() and (uv[mask, 1] >= 0).all()
                      and (uv[mask, 1] < H).all(), f"{label}: uniform outliers outside the image")
        # An outlier's observation belongs to a different 3D point, so it must sit
        # far from its own clean projection - much further than the noise.  The
        # comparison is against the noise scale rather than an exact equality, so
        # the check is meaningful at every sigma, not only at sigma = 0.
        disp = np.linalg.norm(uv[mask] - uv_clean[mask], axis=1)
        scale = max(sigma, 0.5 if quant else 0.0, 1e-6)
        rep.check("outliers", float(np.median(disp)) > 5.0 * scale,
                  f"{label}: median outlier displacement {np.median(disp):.2f} px is not clearly above the "
                  f"noise scale {scale:.2f} px")
        # `mixed` replaces the first half of the selected set uniformly and swaps
        # the rest, so at least that many observations must still match a selected
        # clean projection.  Which individual index was swapped is not recoverable
        # from the stored mask, so the check is on the count.
        n_sel = int(mask.sum())
        n_swapped = n_sel if otype == "swap" else (n_sel - n_sel // 2 if otype == "mixed" else 0)
        if n_swapped == 1:
            n_swapped = 0          # a lone swap candidate is replaced instead (see noise.py)
        if n_swapped >= 2:
            # Every swapped observation is another selected point's observation, so
            # it must lie within the noise of some selected clean point.  The bound
            # is on a 2-D distance, so it needs the norm of two noisy coordinates,
            # not the per-coordinate bound.
            sel = np.flatnonzero(mask)
            dist, nearest = cKDTree(uv_clean[sel]).query(uv[sel], k=1)
            tol_swap = math.sqrt(2.0) * max_deviation_sigmas(len(sel)) * sigma + (0.7072 if quant else 0.0) + 1e-6
            matched = dist <= tol_swap
            rep.check("outliers", int(matched.sum()) >= n_swapped,
                      f"{label}: only {int(matched.sum())} of {len(sel)} outlier observations match a selected "
                      f"clean point, expected at least {n_swapped} swapped "
                      f"(max distance {dist.max():.3f} px, tolerance {tol_swap:.3f} px)")
            # A derangement leaves no observation on its own 3D point, but two
            # distinct points whose projections are closer together than the noise
            # are genuinely indistinguishable, so a handful of nearest-neighbour
            # ties is expected.  Reverting the swap would make *every* observation
            # its own nearest neighbour, which this still catches decisively.
            self_nearest = int((nearest[matched] == np.flatnonzero(matched)).sum())
            allowed = max(3, int(0.02 * len(sel)))
            rep.check("outliers", self_nearest <= allowed,
                      f"{label}: {self_nearest}/{int(matched.sum())} matched outlier observations sit on their "
                      f"own 3D point (at most {allowed} expected from projection ties)")


def _validate_manifest_row(rep: Report, row, sattrs: Dict[str, Any], cattrs: Dict[str, Any],
                           dattrs: Dict[str, Any], K: np.ndarray, coeffs: np.ndarray,
                           depths: np.ndarray, num_points_3d: int, label: str) -> None:
    """
    Every manifest column is re-derived from the HDF5 groups and compared.

    The columns are the dataset's search index: filtering on `fx`, `noise_sigma`
    or `outlier_type` and getting rows that do not match the arrays would be a
    silent, invisible failure.  Checking three of them is not enough.
    """
    model = str(cattrs["distortion_model"])
    if model == "kannala_brandt":
        k1, k2, k3, k4, p1, p2 = coeffs[0], coeffs[1], coeffs[2], coeffs[3], np.nan, np.nan
    else:
        k1, k2, p1, p2, k3, k4 = coeffs[0], coeffs[1], coeffs[2], coeffs[3], coeffs[4], np.nan
    expected: Dict[str, Any] = {
        "scene_type": sattrs["scene_type"], "split": sattrs["split"],
        "num_points_3d": int(num_points_3d), "scene_layout": sattrs.get("layout", ""),
        "camera_id": int(cattrs["camera_id"]), "intrinsics_id": int(cattrs["intrinsics_id"]),
        "pose_id": int(cattrs["pose_id"]), "camera_model": model, "fov_class": cattrs["fov_class"],
        "hfov_deg": float(cattrs["hfov_deg"]), "vfov_deg": float(cattrs["vfov_deg"]),
        "image_width": int(cattrs["image_width"]), "image_height": int(cattrs["image_height"]),
        "fx": float(K[0, 0]), "fy": float(K[1, 1]), "cx": float(K[0, 2]), "cy": float(K[1, 2]),
        "skew": float(K[0, 1]), "distortion_level": cattrs["distortion_level"],
        "k1": float(k1), "k2": float(k2), "k3": float(k3), "k4": float(k4),
        "p1": float(p1), "p2": float(p2),
        "num_visible": int(cattrs["num_visible"]),
        "mean_depth": float(depths.mean()) if len(depths) else float("nan"),
        "condition_id": int(dattrs["condition_id"]), "condition_name": dattrs["name"],
        "noise_sigma": float(dattrs["noise_sigma"]), "quantize": bool(dattrs["quantize"]),
        "outlier_ratio": float(dattrs["outlier_ratio"]), "outlier_type": dattrs["outlier_type"],
        "num_outliers": int(dattrs["num_outliers"]),
    }
    # One check per row rather than per column: the mismatching columns are all
    # named in the message, and 33 rep.check calls per condition would dominate
    # the runtime of a large tier.
    mismatches = []
    for key, want in expected.items():
        if key not in row:
            mismatches.append(f"{key}: column missing")
            continue
        got = row[key]
        if isinstance(want, bool):
            ok = bool(got) == want
        elif isinstance(want, float):
            ok = (np.isnan(want) and np.isnan(float(got))) or np.isclose(float(got), want, rtol=0, atol=1e-9)
        elif isinstance(want, int):
            ok = int(got) == want
        else:
            ok = str(got) == str(want)
        if not ok:
            mismatches.append(f"{key}={got!r} (HDF5: {want!r})")
    rep.check("manifest", not mismatches, f"{label}: manifest disagrees with the HDF5 on " + ", ".join(mismatches[:6]))


def validate_dataset(data_dir: "str | Path", max_cameras: Optional[int] = None, regenerate: int = 1,
                     seed: int = 0, progress: bool = True, log=print) -> Dict[str, Any]:
    data_dir = Path(data_dir)
    rep = Report()
    manifest = load_manifest(data_dir)
    stats = load_stats(data_dir)
    with open(data_dir / "manifest.csv", "r", encoding="utf-8") as fh:
        csv_rows = sum(1 for _ in fh) - 1
    rep.check("manifest", len(manifest) == csv_rows == stats["num_samples"],
              f"manifest rows {len(manifest)} / csv {csv_rows} / stats {stats['num_samples']} disagree")
    rep.check("manifest", manifest["sample_id"].is_unique, "duplicate sample_id in manifest")
    cams_all = manifest.drop_duplicates(["file", "scene_id", "camera_id"])
    rep.check("stats", int(stats["num_scenes"]) == manifest["scene_id"].nunique(),
              f"stats num_scenes {stats['num_scenes']} != {manifest['scene_id'].nunique()} in the manifest")
    rep.check("stats", int(stats["num_cameras"]) == len(cams_all),
              f"stats num_cameras {stats['num_cameras']} != {len(cams_all)} in the manifest")
    rep.check("stats", int(stats["num_correspondences"]) == int(manifest["num_visible"].sum()),
              f"stats num_correspondences {stats['num_correspondences']} != {int(manifest['num_visible'].sum())}")
    rep.check("stats", int(stats["num_samples"]) == len(manifest), "stats num_samples != manifest rows")
    # Every distribution in dataset_stats.json is recomputed from the manifest, not
    # only the four scalar totals: the composition tables are what the dataset card
    # and the README quote, so a stale one would be published unnoticed.
    recomputed = compute_dataset_stats(manifest)
    stale = sorted(k for k, v in recomputed.items() if k in stats and stats[k] != v)
    rep.check("stats", not stale,
              "dataset_stats.json disagrees with the manifest on " + ", ".join(
                  f"{k}: stored {stats.get(k)!r} vs manifest {recomputed[k]!r}" for k in stale[:4]))
    for f in stats["files"]:
        rep.check("files", (data_dir / "hdf5" / f).exists(), f"missing file hdf5/{f}")
    cfg = load_config(data_dir / "metadata" / "config_used.yaml")
    min_depth = float(cfg["cameras"]["min_depth"])
    n_conditions = len(expand_conditions(cfg))

    # Index the manifest once.  Scanning all rows per camera is quadratic and
    # would dominate validation of a large tier (288 k rows x 19 k cameras).
    indexed = manifest.assign(_cam_path=manifest["h5_path"].str.rsplit("/", n=1).str[0])
    rows_by_camera = {key: grp for key, grp in indexed.groupby(["file", "_cam_path"], sort=False)}
    cameras_per_scene = (manifest.drop_duplicates(["file", "scene_id", "camera_id"])
                         .groupby(["file", "scene_id"], sort=False).size().to_dict())

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
    # One HDF5 file open at a time, reopened every REOPEN_EVERY cameras.  HDF5 keeps
    # a per-file metadata cache for every object touched; over the ~288 000 groups of
    # a large tier that cache reaches several gigabytes and the process is killed.
    # Cameras are iterated in (file, path) order, so closing the previous file costs
    # nothing and bounds the resident set to one shard's worth of cache.
    REOPEN_EVERY = 2000
    current_name: Optional[str] = None
    current: Optional[h5py.File] = None
    since_open = 0
    checked_scenes = set()
    try:
        for _, row in iterator:
            if current is None or row["file"] != current_name or since_open >= REOPEN_EVERY:
                if current is not None:
                    current.close()
                current_name = row["file"]
                current = h5py.File(data_dir / current_name, "r")
                since_open = 0
            since_open += 1
            f = current
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
                    n_planes = int(sattrs["num_planes"])
                    for k in range(n_planes):
                        rep.check("scene", is_planar(pts[labels == k]),
                                  f"{label}: plane {k} of {st} is not planar")
                    # `is_planar` is vacuously true for fewer than four points, so an
                    # empty or missing plane would slip past the check above; requiring
                    # the label set to be exactly the expected one closes that.  A
                    # sparsely populated plane is legitimate - `_gen_planar_multi`
                    # divides the scene's points between two to four planes, so a small
                    # `scenes.num_points` leaves few on each - which is why the check is
                    # on the set of labels rather than on how many points carry each.
                    allowed = set(range(n_planes)) | ({-1} if st == "mixed" else set())
                    rep.check("scene", set(np.unique(labels).tolist()) == allowed,
                              f"{label}: {st} point_labels are {sorted(set(np.unique(labels).tolist()))}, "
                              f"expected {sorted(allowed)}")
                    rep.check("scene", not is_planar(pts), f"{label}: {st} scene is degenerate (planar)")
                else:
                    rep.check("scene", not is_planar(pts) and (labels == -1).all(), f"{label}: {st} labels/planarity")
                rep.check("scene", int(sattrs["num_cameras"]) == cameras_per_scene.get((row["file"], row["scene_id"]), 0),
                          f"{label}: num_cameras attr vs manifest")
            _validate_camera(rep, cam_grp, pts, min_depth, label)
            uv_clean = cam_grp["points_2d_clean"][()]
            cattrs = read_attrs(cam_grp)
            W, H = int(cattrs["image_width"]), int(cattrs["image_height"])
            cond_names = [k for k in cam_grp.keys() if k.startswith("condition_")]
            rep.check("conditions", len(cond_names) == n_conditions == int(cattrs["num_conditions"]),
                      f"{label}: expected {n_conditions} conditions, found {len(cond_names)}")
            cond_attrs = {cname: read_attrs(cam_grp[cname]) for cname in cond_names}
            for cname in cond_names:
                _validate_condition(rep, cam_grp[cname], cond_attrs[cname], uv_clean, W, H, f"{label}/{cname}")
            # Every manifest row of this camera, column by column, against the HDF5.
            # The scene/camera arrays and attributes are read once, not per row.
            depths = cam_grp["depths"][()]
            K_cam, coeffs_cam = cam_grp["K"][()], cam_grp["dist_coeffs"][()]
            scene_attrs_cached = read_attrs(scene_grp)
            cam_rows = rows_by_camera.get((row["file"], cam_grp.name), manifest.iloc[:0])
            rep.check("manifest", len(cam_rows) == len(cond_names),
                      f"{label}: {len(cam_rows)} manifest rows for {len(cond_names)} conditions")
            for mrow in cam_rows.to_dict("records"):
                cname = str(mrow["h5_path"]).rsplit("/", 1)[-1]
                if cname not in cond_attrs:
                    rep.check("manifest", False, f"{label}: manifest points at missing group {mrow['h5_path']}")
                    continue
                rep.check("manifest", str(mrow["sample_id"]) == f"{Path(str(mrow['file'])).stem}{mrow['h5_path']}",
                          f"{label}: sample_id does not match file + h5_path")
                _validate_manifest_row(rep, mrow, scene_attrs_cached, cattrs, cond_attrs[cname],
                                       K_cam, coeffs_cam, depths, len(pts), f"{label}/{cname}")
    finally:
        if current is not None:
            current.close()

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
                # A scene whose every pose failed the visibility test is counted, not
                # written, so its absence is correct exactly when it regenerates empty.
                rep.check("reproducibility", not rec["cameras"],
                          f"scene {spec['scene_id']} is missing from the manifest but regenerates "
                          f"with {len(rec['cameras'])} cameras")
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
