"""
Figures for the dataset and the benchmark results (matplotlib, Agg backend).

Design rules: one categorical palette with a fixed hue per solver (color follows
the entity, never its rank), <= 8 series per axes (solvers are split into the
non-robust and robust families), marker shapes as a secondary encoding, a
single-hue sequential ramp for heat maps, recessive solid hairline grids and a
legend whenever more than one series is drawn.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .cameras import distort_points, normalized_from_pixel, pixel_from_normalized  # noqa: E402
from .storage import SampleReader, load_manifest  # noqa: E402

# ----------------------------------------------------------------------------- palette
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
STATUS_CRITICAL = "#d03b3b"
SEQ_CMAP = LinearSegmentedColormap.from_list("pnp_blue", SEQUENTIAL)

SOLVER_COLORS: Dict[str, str] = {
    # non-robust family
    "sqpnp": CATEGORICAL[0], "epnp": CATEGORICAL[1], "epnp_lm": CATEGORICAL[2], "iterative": CATEGORICAL[3],
    "dlt": CATEGORICAL[4], "dlt_lm": CATEGORICAL[5], "ippe": CATEGORICAL[6], "p3p": CATEGORICAL[7],
    "ap3p": CATEGORICAL[6],  # never drawn together with ippe (planar-only) on one axes
    # robust family
    "ransac_p3p": CATEGORICAL[0], "ransac_dlt": CATEGORICAL[1], "cv_ransac_epnp": CATEGORICAL[2],
    "cv_ransac_epnp_lm": CATEGORICAL[3], "cv_ransac_ap3p": CATEGORICAL[4], "cv_usac_magsac": CATEGORICAL[5],
    # calibration
    "dlt_uncalibrated": CATEGORICAL[0], "dlt_uncalibrated_lm": CATEGORICAL[1],
    "opencv": CATEGORICAL[0], "ba_scratch": CATEGORICAL[1],
}
SOLVER_MARKERS: Dict[str, str] = {
    "sqpnp": "o", "epnp": "s", "epnp_lm": "^", "iterative": "D", "dlt": "v", "dlt_lm": "P", "ippe": "X",
    "p3p": "*", "ap3p": "X", "ransac_p3p": "o", "ransac_dlt": "s", "cv_ransac_epnp": "^",
    "cv_ransac_epnp_lm": "D", "cv_ransac_ap3p": "v", "cv_usac_magsac": "P",
    "dlt_uncalibrated": "o", "dlt_uncalibrated_lm": "s", "opencv": "o", "ba_scratch": "s",
}
NON_ROBUST = ["sqpnp", "epnp", "epnp_lm", "iterative", "dlt", "dlt_lm", "ippe"]
ROBUST = ["ransac_p3p", "ransac_dlt", "cv_ransac_epnp", "cv_ransac_epnp_lm", "cv_ransac_ap3p", "cv_usac_magsac"]
SCENE_TYPES = ["planar_single", "planar_multi", "volumetric", "mixed", "depth_stratified"]
MODELS = ["pinhole", "brown_conrady", "kannala_brandt"]
FOV_CLASSES = ["narrow", "normal", "wide", "fisheye"]


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.8, "grid.linestyle": "-", "axes.axisbelow": True,
        "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": INK_2, "text.color": INK,
        "axes.titlecolor": INK, "axes.titleweight": "medium", "axes.titlesize": 11, "axes.labelsize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 8.5, "legend.frameon": False,
        "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.8, "lines.markersize": 5.5,
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
    })


def _color(name: str, i: int = 0) -> str:
    return SOLVER_COLORS.get(name, CATEGORICAL[i % len(CATEGORICAL)])


def _marker(name: str) -> str:
    return SOLVER_MARKERS.get(name, "o")


def _save(fig, out_dir: Path, name: str) -> Path:
    path = Path(out_dir) / name
    fig.savefig(path)
    plt.close(fig)
    return path


def _present(df: pd.DataFrame, names: Sequence[str]) -> List[str]:
    have = set(df["solver"].unique())
    return [n for n in names if n in have]


def _line_panel(ax, df: pd.DataFrame, x: str, y: str, solvers: Sequence[str], agg: str = "median",
                ylabel: str = "", title: str = "", logy: bool = False, logx: bool = False, pct: bool = False):
    for i, name in enumerate(solvers):
        sub = df[df["solver"] == name]
        if sub.empty:
            continue
        if agg == "mean":
            series = sub.groupby(x)[y].mean()
        else:
            series = sub.groupby(x)[y].median()
        xs = np.asarray(series.index, dtype=float)
        ys = series.values * (100.0 if pct else 1.0)
        ax.plot(xs, ys, marker=_marker(name), color=_color(name, i), label=name, markeredgecolor=SURFACE,
                markeredgewidth=0.8)
    if logy:
        ax.set_yscale("log")
    if logx:
        ax.set_xscale("log")
    ax.set_xlabel(x.replace("_", " "))
    ax.set_ylabel(ylabel or y)
    ax.set_title(title)
    if len(solvers) > 1:
        ax.legend(loc="best", ncol=1 if len(solvers) <= 4 else 2)


def _heatmap(ax, table: pd.DataFrame, title: str, fmt: str = "{:.2g}", vmin=None, vmax=None, cbar_label: str = ""):
    data = table.values.astype(float)
    im = ax.imshow(data, cmap=SEQ_CMAP, aspect="auto", vmin=vmin, vmax=vmax)
    ax.set_xticks(range(table.shape[1]))
    ax.set_xticklabels([str(c) for c in table.columns], rotation=30, ha="right")
    ax.set_yticks(range(table.shape[0]))
    ax.set_yticklabels([str(r) for r in table.index])
    ax.grid(False)
    lo = np.nanmin(data) if vmin is None else vmin
    hi = np.nanmax(data) if vmax is None else vmax
    for r in range(table.shape[0]):
        for c in range(table.shape[1]):
            v = data[r, c]
            if not np.isfinite(v):
                continue
            frac = 0.5 if hi == lo else (v - lo) / (hi - lo)
            ax.text(c, r, fmt.format(v), ha="center", va="center", fontsize=7.5,
                    color=SURFACE if frac > 0.55 else INK)
    ax.set_title(title)
    cb = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.outline.set_visible(False)
    if cbar_label:
        cb.set_label(cbar_label, color=INK_2)


# =============================================================================
# Dataset figures
# =============================================================================
def _pick_camera(manifest: pd.DataFrame, **conds) -> Optional[pd.Series]:
    df = manifest
    for key, value in conds.items():
        df = df[df[key] == value]
    if df.empty:
        return None
    return df.iloc[0]


def fig_scene_gallery(data_dir: Path, out_dir: Path) -> Optional[Path]:
    manifest = load_manifest(data_dir)
    fig = plt.figure(figsize=(16, 3.8))
    with SampleReader(data_dir) as reader:
        for i, st in enumerate(SCENE_TYPES):
            row = _pick_camera(manifest, scene_type=st, condition_id=0)
            if row is None:
                continue
            ax = fig.add_subplot(1, 5, i + 1, projection="3d")
            s = reader.read(row)
            pts = s.points_3d
            ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=2, color=CATEGORICAL[0], alpha=0.55, linewidths=0, label="3D points")
            cams = manifest[(manifest["file"] == row["file"]) & (manifest["scene_id"] == row["scene_id"])].drop_duplicates("camera_id")
            centers = []
            for _, crow in cams.iterrows():
                cs = reader.read(crow)
                centers.append(cs.camera_center)
            centers = np.asarray(centers)
            ax.scatter(centers[:, 0], centers[:, 1], centers[:, 2], s=22, color=CATEGORICAL[1], marker="^",
                       edgecolors=SURFACE, linewidths=0.6, label="camera centers")
            ax.set_title(f"{st}\nN = {len(pts)}, {len(centers)} cameras", fontsize=9.5)
            ax.set_box_aspect((1, 1, 1))
            ax.grid(False)
            for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
                axis.set_pane_color((1, 1, 1, 0))
                axis.set_tick_params(labelsize=6, colors=MUTED)
            ax.set_xlabel("x [m]", fontsize=7, labelpad=-4)
            ax.set_ylabel("y [m]", fontsize=7, labelpad=-4)
            ax.set_zlabel("z [m]", fontsize=7, labelpad=-4)
            if i == 0:
                ax.legend(loc="upper left", fontsize=7.5)
    fig.suptitle("Scene families with their sampled camera centers", fontsize=12, color=INK)
    return _save(fig, out_dir, "dataset_scene_gallery.png")


def fig_projection_examples(data_dir: Path, out_dir: Path) -> Optional[Path]:
    manifest = load_manifest(data_dir)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    with SampleReader(data_dir) as reader:
        for ax, model in zip(axes, MODELS):
            cand = manifest[(manifest["camera_model"] == model) & (manifest["outlier_ratio"] == 0.2)
                            & (manifest["outlier_type"] == "uniform")]
            if cand.empty:
                cand = manifest[manifest["camera_model"] == model]
            if cand.empty:
                ax.set_visible(False)
                continue
            cand = cand.sort_values("num_visible", ascending=False)
            row = cand.iloc[len(cand) // 3]
            s = reader.read(row)
            W, H = s.camera_attrs["image_width"], s.camera_attrs["image_height"]
            inl = ~s.outlier_mask
            ax.scatter(s.uv[inl, 0], s.uv[inl, 1], s=5, color=CATEGORICAL[0], linewidths=0, alpha=0.8,
                       label=f"inliers ({inl.sum()})")
            ax.scatter(s.uv[~inl, 0], s.uv[~inl, 1], s=16, color=STATUS_CRITICAL, marker="x", linewidths=0.9,
                       label=f"outliers ({(~inl).sum()})")
            ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, edgecolor=AXIS, linewidth=1.0))
            ax.set_xlim(-0.03 * W, 1.03 * W)
            ax.set_ylim(1.03 * H, -0.03 * H)
            ax.set_aspect("equal")
            ax.set_title(f"{model}  |  {s.camera_attrs['fov_class']} FOV {s.camera_attrs['hfov_deg']:.0f} deg  |  "
                         f"{W}x{H}\n{row['scene_type']}, sigma = {row['noise_sigma']} px, "
                         f"{int(row['outlier_ratio'] * 100)} % outliers", fontsize=9)
            ax.set_xlabel("u [px]")
            ax.set_ylabel("v [px]")
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, markerscale=1.5)
    fig.suptitle("Stored 2D observations of one view per camera model (image frame drawn in gray)", fontsize=12)
    fig.tight_layout()
    return _save(fig, out_dir, "dataset_projection_examples.png")


def fig_distortion_fields(data_dir: Path, out_dir: Path) -> Optional[Path]:
    manifest = load_manifest(data_dir)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    with SampleReader(data_dir) as reader:
        for ax, model in zip(axes, ["brown_conrady", "kannala_brandt"]):
            cand = manifest[manifest["camera_model"] == model].drop_duplicates(["file", "scene_id", "camera_id"])
            strong = cand[cand["distortion_level"] == "strong"]
            if not strong.empty:
                cand = strong
            if cand.empty:
                ax.set_visible(False)
                continue
            row = cand.iloc[0]
            s = reader.read(row)
            intr = s.intrinsics
            W, H = intr.width, intr.height
            nx, ny = 13, 9
            us = np.linspace(0.06 * W, 0.94 * W, nx)
            vs = np.linspace(0.06 * H, 0.94 * H, ny)
            gu, gv = np.meshgrid(us, vs)
            xd, yd = normalized_from_pixel(gu.ravel(), gv.ravel(), intr.K)  # treat grid as undistorted normalized
            xx, yy = distort_points(xd, yd, intr.model, intr.coeffs)
            du, dv = pixel_from_normalized(xx, yy, intr.K)
            du = du.reshape(ny, nx)
            dv = dv.reshape(ny, nx)
            for r in range(ny):
                ax.plot(gu[r], gv[r], color=AXIS, linewidth=1.0, zorder=1)
                ax.plot(du[r], dv[r], color=CATEGORICAL[0], linewidth=1.4, zorder=2)
            for c in range(nx):
                ax.plot(gu[:, c], gv[:, c], color=AXIS, linewidth=1.0, zorder=1)
                ax.plot(du[:, c], dv[:, c], color=CATEGORICAL[0], linewidth=1.4, zorder=2)
            ax.plot([], [], color=AXIS, linewidth=1.5, label="undistorted (pinhole) grid")
            ax.plot([], [], color=CATEGORICAL[0], linewidth=1.5, label="distorted grid")
            ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, edgecolor=AXIS, linewidth=1.0))
            ax.set_aspect("equal")
            ax.set_xlim(-0.08 * W, 1.08 * W)
            ax.set_ylim(1.08 * H, -0.08 * H)
            coeffs = ", ".join(f"{c:+.3g}" for c in intr.coeffs)
            ax.set_title(f"{model} ({intr.distortion_level}), FOV {intr.hfov_deg:.0f} deg\ncoeffs = [{coeffs}]", fontsize=9)
            ax.set_xlabel("u [px]")
            ax.set_ylabel("v [px]")
            ax.legend(loc="lower right")
    fig.suptitle("Lens distortion fields of two sampled cameras", fontsize=12)
    fig.tight_layout()
    return _save(fig, out_dir, "dataset_distortion_fields.png")


def fig_distributions(data_dir: Path, out_dir: Path) -> Optional[Path]:
    manifest = load_manifest(data_dir)
    cams = manifest.drop_duplicates(["file", "scene_id", "camera_id"])
    scenes = manifest.drop_duplicates(["file", "scene_id"])
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    ax = axes[0, 0]
    ax.hist(cams["num_visible"], bins=30, color=CATEGORICAL[0], edgecolor=SURFACE, linewidth=0.6)
    ax.set_title("Visible correspondences per view")
    ax.set_xlabel("M (points in image)")
    ax.set_ylabel("views")
    ax = axes[0, 1]
    for i, fc in enumerate(FOV_CLASSES):
        sub = cams[cams["fov_class"] == fc]
        if len(sub):
            ax.hist(sub["hfov_deg"], bins=np.linspace(0, 180, 37), color=CATEGORICAL[i], alpha=0.85,
                    edgecolor=SURFACE, linewidth=0.5, label=fc)
    ax.set_title("Horizontal field of view")
    ax.set_xlabel("HFOV [deg]")
    ax.set_ylabel("views")
    ax.legend()
    ax = axes[0, 2]
    depth = cams["mean_depth"]
    ax.hist(np.log10(depth[depth > 0]), bins=30, color=CATEGORICAL[0], edgecolor=SURFACE, linewidth=0.6)
    ax.set_title("Mean depth of the visible points per view")
    ax.set_xlabel("log10(depth [m])")
    ax.set_ylabel("views")
    ax = axes[1, 0]
    counts = scenes["scene_type"].value_counts().reindex(SCENE_TYPES).fillna(0)
    ax.bar(range(len(counts)), counts.values, color=CATEGORICAL[0], width=0.7)
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(counts.index, rotation=25, ha="right")
    ax.set_title("Scenes per type")
    ax.set_ylabel("scenes")
    ax = axes[1, 1]
    tab = cams.groupby(["camera_model", "fov_class"]).size().unstack(fill_value=0).reindex(MODELS).fillna(0)
    bottom = np.zeros(len(tab))
    for i, fc in enumerate(FOV_CLASSES):
        if fc in tab.columns:
            ax.bar(range(len(tab)), tab[fc].values, bottom=bottom, color=CATEGORICAL[i], label=fc, width=0.7,
                   edgecolor=SURFACE, linewidth=0.8)
            bottom += tab[fc].values
    ax.set_xticks(range(len(tab)))
    ax.set_xticklabels(tab.index, rotation=25, ha="right")
    ax.set_title("Cameras per model and FOV class")
    ax.set_ylabel("views")
    ax.legend()
    ax = axes[1, 2]
    cond = manifest.groupby(["condition_id", "condition_name"]).size().reset_index()
    ax.barh(range(len(cond)), cond[0].values, color=CATEGORICAL[0], height=0.7)
    ax.set_yticks(range(len(cond)))
    ax.set_yticklabels(cond["condition_name"], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_title("Samples per noise condition")
    ax.set_xlabel("samples")
    fig.suptitle("Dataset composition", fontsize=12)
    fig.tight_layout()
    return _save(fig, out_dir, "dataset_distributions.png")


def fig_pose_distribution(data_dir: Path, out_dir: Path) -> Optional[Path]:
    manifest = load_manifest(data_dir)
    cams = manifest.drop_duplicates(["file", "scene_id", "camera_id"])
    elev, azim, dist_ratio = [], [], []
    with SampleReader(data_dir) as reader:
        for _, row in cams.iterrows():
            s = reader.read(row)
            if s.camera_attrs.get("pose_strategy") != "hemisphere":
                continue
            front = np.asarray(s.scene_attrs["front_axis"], dtype=float)
            center = np.asarray(s.scene_attrs["center"], dtype=float)
            d = s.camera_center - center
            r = np.linalg.norm(d)
            d = d / r
            e = math.degrees(math.asin(np.clip(d @ front, -1, 1)))
            # azimuth in the plane orthogonal to the front axis
            ref = np.array([1.0, 0.0, 0.0]) if abs(front[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
            u = np.cross(front, ref)
            u /= np.linalg.norm(u)
            v = np.cross(front, u)
            a = math.degrees(math.atan2(d @ v, d @ u))
            elev.append(e)
            azim.append(a)
            dist_ratio.append(r / float(s.scene_attrs["radius"]))
    if not elev:
        return None
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    axes[0].scatter(azim, elev, s=9, color=CATEGORICAL[0], alpha=0.6, linewidths=0)
    axes[0].set_xlabel("azimuth around the front axis [deg]")
    axes[0].set_ylabel("elevation above the base plane [deg]")
    axes[0].set_title(f"Camera directions on the hemisphere ({len(elev)} views)")
    axes[0].set_xlim(-180, 180)
    axes[0].set_ylim(0, 90)
    axes[1].hist(dist_ratio, bins=30, color=CATEGORICAL[0], edgecolor=SURFACE, linewidth=0.6)
    axes[1].set_xlabel("camera distance / scene radius")
    axes[1].set_ylabel("views")
    axes[1].set_title("Distance to the scene center (FOV-dependent framing)")
    fig.tight_layout()
    return _save(fig, out_dir, "dataset_pose_distribution.png")


def make_dataset_figures(data_dir, out_dir) -> List[Path]:
    _style()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for fn in (fig_scene_gallery, fig_projection_examples, fig_distortion_fields, fig_distributions, fig_pose_distribution):
        p = fn(Path(data_dir), out_dir)
        if p is not None:
            paths.append(p)
    return paths


# =============================================================================
# Benchmark figures
# =============================================================================
def fig_error_vs_noise(df: pd.DataFrame, out_dir: Path) -> Optional[Path]:
    sub = df[(df["outlier_ratio"] == 0) & (~df["quantize"].astype(bool)) & (df["num_points_setting"] == "all")]
    if sub["noise_sigma"].nunique() < 2:
        return None
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
    for col, (names, title) in enumerate([(_present(sub, NON_ROBUST), "non-robust solvers"), (_present(sub, ROBUST), "robust solvers")]):
        if not names:
            continue
        _line_panel(axes[0, col], sub, "noise_sigma", "rot_err_deg", names, ylabel="median rotation error [deg]",
                    title=f"Rotation error vs pixel noise ({title})", logy=True)
        _line_panel(axes[1, col], sub, "noise_sigma", "reproj_rmse_px", names, ylabel="median reprojection RMSE [px]",
                    title=f"Reprojection RMSE vs pixel noise ({title})", logy=True)
        for ax in axes[:, col]:
            ax.set_xlabel("Gaussian noise sigma [px]")
    fig.suptitle("Outlier-free conditions, all visible correspondences", fontsize=12)
    fig.tight_layout()
    return _save(fig, out_dir, "pnp_error_vs_noise.png")


def fig_success_vs_outliers(df: pd.DataFrame, out_dir: Path) -> Optional[Path]:
    sub = df[(df["outlier_type"] == "uniform") & (df["noise_sigma"] == 0.5) & (~df["quantize"].astype(bool))
             & (df["num_points_setting"] == "all")]
    if sub["outlier_ratio"].nunique() < 2:
        return None
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    rob = _present(sub, ROBUST)
    nonrob = _present(sub, NON_ROBUST)
    if rob:
        _line_panel(axes[0], sub, "outlier_ratio", "success", rob, agg="mean", ylabel="success rate [%]",
                    title="Robust solvers: success vs outlier ratio", pct=True)
        axes[0].set_ylim(-3, 103)
        _line_panel(axes[1], sub, "outlier_ratio", "rot_err_deg", rob, ylabel="median rotation error [deg]",
                    title="Robust solvers: rotation error vs outlier ratio", logy=True)
    if nonrob:
        _line_panel(axes[2], sub, "outlier_ratio", "success", nonrob, agg="mean", ylabel="success rate [%]",
                    title="Non-robust solvers: success vs outlier ratio", pct=True)
        axes[2].set_ylim(-3, 103)
    for ax in axes:
        ax.set_xlabel("outlier ratio (uniform replacement)")
    fig.suptitle("sigma = 0.5 px, all visible correspondences; success = rot <= 5 deg and rel. trans. <= 5 %", fontsize=11)
    fig.tight_layout()
    return _save(fig, out_dir, "pnp_success_vs_outliers.png")


def fig_inlier_prf(df: pd.DataFrame, out_dir: Path) -> Optional[Path]:
    sub = df[(df["outlier_ratio"] > 0) & (df["outlier_type"] == "uniform") & (df["noise_sigma"] == 0.5)
             & (df["num_points_setting"] == "all") & df["robust"].astype(bool)]
    rob = _present(sub, ROBUST)
    if not rob or sub["outlier_ratio"].nunique() < 2:
        return None
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    _line_panel(axes[0], sub, "outlier_ratio", "inlier_precision", rob, ylabel="median inlier precision", title="Inlier precision")
    _line_panel(axes[1], sub, "outlier_ratio", "inlier_recall", rob, ylabel="median inlier recall", title="Inlier recall")
    for ax in axes:
        ax.set_ylim(-0.03, 1.03)
        ax.set_xlabel("outlier ratio (uniform replacement)")
    fig.suptitle("Inlier classification of the robust solvers (sigma = 0.5 px)", fontsize=12)
    fig.tight_layout()
    return _save(fig, out_dir, "pnp_inlier_precision_recall.png")


def fig_error_vs_num_points(df: pd.DataFrame, out_dir: Path) -> Optional[Path]:
    sub = df[(df["num_points_setting"] != "all") & (df["outlier_ratio"] == 0) & (~df["subset_planar"].astype(bool))]
    if sub.empty or sub["num_points_setting"].nunique() < 2:
        return None
    sub = sub.copy()
    sub["n"] = sub["num_points_setting"].astype(int)
    names = _present(sub, ["sqpnp", "epnp", "epnp_lm", "iterative", "dlt", "dlt_lm", "p3p", "ap3p"])
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    _line_panel(axes[0], sub, "n", "rot_err_deg", names, ylabel="median rotation error [deg]",
                title="Rotation error vs number of correspondences", logx=True, logy=True)
    _line_panel(axes[1], sub, "n", "success", names, agg="mean", ylabel="success rate [%]",
                title="Success rate vs number of correspondences", logx=True, pct=True)
    axes[1].set_ylim(-3, 103)
    _line_panel(axes[2], sub, "n", "runtime_ms", names, ylabel="median runtime [ms]",
                title="Runtime vs number of correspondences", logx=True, logy=True)
    for ax in axes:
        ax.set_xlabel("number of correspondences n")
    fig.suptitle("Outlier-free conditions on non-planar subsets (P3P / AP3P evaluated at n = 4 only)", fontsize=11)
    fig.tight_layout()
    return _save(fig, out_dir, "pnp_error_vs_num_points.png")


def fig_factor_heatmaps(df: pd.DataFrame, out_dir: Path) -> Optional[Path]:
    sub = df[(df["outlier_ratio"] == 0) & (df["num_points_setting"] == "all")]
    if sub.empty:
        return None
    order = [s for s in NON_ROBUST + ROBUST if s in set(sub["solver"])]
    fig, axes = plt.subplots(1, 3, figsize=(17, 0.42 * len(order) + 2.2))
    for ax, (factor, levels, title) in zip(axes, [("scene_type", SCENE_TYPES, "scene type"),
                                                   ("camera_model", MODELS, "camera model"),
                                                   ("fov_class", FOV_CLASSES, "FOV class")]):
        piv = sub.pivot_table(index="solver", columns=factor, values="rot_err_deg", aggfunc="median")
        piv = piv.reindex(index=order, columns=[l for l in levels if l in piv.columns])
        _heatmap(ax, np.log10(piv.clip(lower=1e-8)), f"log10 median rotation error [deg] by {title}", fmt="{:.1f}",
                 cbar_label="log10(deg)")
    fig.suptitle("Outlier-free conditions; lighter = more accurate", fontsize=11)
    fig.tight_layout()
    return _save(fig, out_dir, "pnp_factor_heatmaps.png")


def fig_success_heatmap(df: pd.DataFrame, out_dir: Path) -> Optional[Path]:
    sub = df[df["num_points_setting"] == "all"]
    if sub.empty:
        return None
    order = [s for s in NON_ROBUST + ROBUST if s in set(sub["solver"])]
    conds = sub.drop_duplicates("condition_id").sort_values("condition_id")["condition_name"].tolist()
    piv = sub.pivot_table(index="solver", columns="condition_name", values="success", aggfunc="mean") * 100
    piv = piv.reindex(index=order, columns=conds)
    fig, ax = plt.subplots(figsize=(1.0 * len(conds) + 3, 0.42 * len(order) + 2.4))
    _heatmap(ax, piv, "Success rate [%] per solver and noise condition", fmt="{:.0f}", vmin=0, vmax=100, cbar_label="%")
    ax.set_xlabel("condition  (s = sigma px, q = quantized, o = outlier ratio, type)")
    fig.tight_layout()
    return _save(fig, out_dir, "pnp_success_heatmap.png")


def fig_runtime(df: pd.DataFrame, out_dir: Path) -> Optional[Path]:
    sub = df[df["num_points_setting"] == "all"]
    if sub.empty:
        return None
    med = sub.groupby("solver")["runtime_ms"].median()
    order = [s for s in NON_ROBUST + ROBUST if s in med.index]
    med = med.loc[order]
    fig, ax = plt.subplots(figsize=(9, 0.38 * len(order) + 1.8))
    ax.barh(range(len(med)), med.values, color=CATEGORICAL[0], height=0.65)
    for i, v in enumerate(med.values):
        ax.text(v * 1.08, i, f"{v:.2g} ms", va="center", fontsize=8, color=INK_2)
    ax.set_yticks(range(len(med)))
    ax.set_yticklabels(med.index)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("median runtime per solve [ms] (all visible correspondences)")
    ax.set_title("Solver runtime")
    fig.tight_layout()
    return _save(fig, out_dir, "pnp_runtime.png")


def fig_calibration(df_single: Optional[pd.DataFrame], df_multi: Optional[pd.DataFrame], out_dir: Path) -> Optional[Path]:
    have_single = df_single is not None and len(df_single) > 0
    have_multi = df_multi is not None and len(df_multi) > 0
    if not (have_single or have_multi):
        return None
    ncols = int(have_single) * 2 + int(have_multi) * 2
    fig, axes = plt.subplots(1, ncols, figsize=(4.4 * ncols, 4.4))
    axes = np.atleast_1d(axes)
    k = 0

    def grouped_bars(ax, frame, factor, levels, value, solvers, ylabel, title, logy=False):
        levels = [l for l in levels if l in set(frame[factor])]
        width = 0.8 / max(1, len(solvers))
        for i, name in enumerate(solvers):
            med = frame[frame["solver"] == name].groupby(factor)[value].median().reindex(levels)
            ax.bar(np.arange(len(levels)) + (i - (len(solvers) - 1) / 2) * width, med.values, width=width * 0.94,
                   color=_color(name, i), label=name, edgecolor=SURFACE, linewidth=0.8)
        ax.set_xticks(range(len(levels)))
        ax.set_xticklabels(levels, rotation=20, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=9.5)
        if logy:
            ax.set_yscale("log")
        if len(solvers) > 1:
            ax.legend()

    if have_single:
        solvers = _present(df_single, ["dlt_uncalibrated", "dlt_uncalibrated_lm"])
        grouped_bars(axes[k], df_single, "camera_model", MODELS, "focal_err_pct", solvers, "median focal error [%]",
                     "Single-view DLT: focal error by camera model", logy=True)
        k += 1
        sub = df_single[(df_single["camera_model"] == "pinhole") & (~df_single["quantize"].astype(bool))]
        if sub["noise_sigma"].nunique() > 1:
            _line_panel(axes[k], sub, "noise_sigma", "focal_err_pct", solvers, ylabel="median focal error [%]",
                        title="Single-view DLT (pinhole): focal error vs noise", logy=True)
            axes[k].set_xlabel("Gaussian noise sigma [px]")
        else:
            grouped_bars(axes[k], df_single, "fov_class", FOV_CLASSES, "cx_err_px", solvers, "median cx error [px]",
                         "Single-view DLT: principal point error by FOV class", logy=True)
        k += 1
    if have_multi:
        solvers = _present(df_multi, ["opencv", "ba_scratch"])
        grouped_bars(axes[k], df_multi, "camera_model", MODELS, "focal_err_pct", solvers, "median focal error [%]",
                     "Multi-view calibration: focal error by camera model", logy=True)
        k += 1
        grouped_bars(axes[k], df_multi, "fov_class", FOV_CLASSES, "cx_err_px", solvers, "median cx error [px]",
                     "Multi-view calibration: principal point error by FOV class", logy=True)
        k += 1
    fig.suptitle("Intrinsic calibration benchmarks (outlier-free conditions)", fontsize=12)
    fig.tight_layout()
    return _save(fig, out_dir, "calibration_intrinsic_errors.png")


def make_benchmark_figures(results_dir, out_dir) -> List[Path]:
    _style()
    results_dir = Path(results_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    pnp_path = results_dir / "pnp_results.csv"
    frames = []
    if pnp_path.exists():
        frames.append(pd.read_csv(pnp_path))
    sweep_path = results_dir / "pnp_num_points_results.csv"
    if sweep_path.exists():
        frames.append(pd.read_csv(sweep_path))
    if frames:
        df = pd.concat(frames, ignore_index=True)
        df["num_points_setting"] = df["num_points_setting"].astype(str)
        for fn in (fig_error_vs_noise, fig_success_vs_outliers, fig_inlier_prf, fig_error_vs_num_points,
                   fig_factor_heatmaps, fig_success_heatmap, fig_runtime):
            p = fn(df, out_dir)
            if p is not None:
                paths.append(p)
    single = pd.read_csv(results_dir / "calibration_results.csv") if (results_dir / "calibration_results.csv").exists() else None
    multi = pd.read_csv(results_dir / "multiview_results.csv") if (results_dir / "multiview_results.csv").exists() else None
    p = fig_calibration(single, multi, out_dir)
    if p is not None:
        paths.append(p)
    return paths
