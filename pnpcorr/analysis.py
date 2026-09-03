"""
Aggregation of benchmark results into summary tables (CSV + Markdown).

All tables are produced from the per-solve result frames written by
``scripts/run_benchmark.py``; nothing is recomputed from the HDF5 data.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

PNP_FACTORS = ["noise_sigma", "quantize", "outlier_ratio", "outlier_type", "scene_type", "camera_model",
               "fov_class", "distortion_level", "num_points_setting"]


# ----------------------------------------------------------------------------
# Markdown helpers
# ----------------------------------------------------------------------------
def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(value):
            return "nan"
        if value == 0:
            return "0"
        mag = abs(value)
        if mag >= 1000:
            return f"{value:,.0f}"
        if mag >= 10:
            return f"{value:.1f}"
        if mag >= 0.01:
            return f"{value:.3f}"
        return f"{value:.2e}"
    if isinstance(value, (bool, np.bool_)):
        return "yes" if value else "no"
    return str(value)


def _escape_cell(text: str) -> str:
    """A bare '|' would end the cell, so every table value escapes it."""
    return text.replace("|", "\\|")


def df_to_markdown(df: pd.DataFrame, index: bool = True) -> str:
    """Minimal GitHub-flavoured Markdown table renderer (no extra dependency)."""
    frame = df.reset_index() if index else df
    cols = [_escape_cell(str(c)) for c in frame.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(_escape_cell(_fmt(v)) for v in row.values) + " |")
    return "\n".join(lines) + "\n"


def write_table(df: pd.DataFrame, path_stem: Path, title: str, note: str = "") -> str:
    """Write ``<stem>.csv`` and ``<stem>.md``; return the Markdown section."""
    df.to_csv(str(path_stem) + ".csv")
    md = f"### {title}\n\n"
    if note:
        md += note.strip() + "\n\n"
    md += df_to_markdown(df)
    with open(str(path_stem) + ".md", "w", encoding="utf-8") as fh:
        fh.write(md)
    return md


# ----------------------------------------------------------------------------
# PnP summaries
# ----------------------------------------------------------------------------
def _solver_order(df: pd.DataFrame) -> List[str]:
    from .solvers import SOLVERS
    present = list(df["solver"].unique())
    return [s for s in SOLVERS.keys() if s in present] + [s for s in present if s not in SOLVERS]


def solver_overview(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per solver with the headline numbers.

    Every solver is offered every sample, so `solves` is the same for all of them
    and the columns are directly comparable.  A solver restricted to part of the
    input space - IPPE to coplanar scenes, the DLT away from them - declines the
    rest, which shows up as a lower `returned (%)`; `success when returned (%)`
    then says how often it was right when it did answer.
    """
    g = df.groupby("solver", sort=False)
    returned = g["ok"].sum()
    success = g["success"].sum()
    out = pd.DataFrame({
        "family": g["family"].first(),
        "solves": g.size(),
        "returned (%)": g["ok"].mean() * 100.0,
        "success (%)": g["success"].mean() * 100.0,
        "success when returned (%)": (success / returned.where(returned > 0)) * 100.0,
        "rot err median (deg)": g["rot_err_deg"].median(),
        "rot err mean (deg)": g["rot_err_deg"].mean(),
        "trans err rel median": g["trans_err_rel"].median(),
        "reproj RMSE median (px)": g["reproj_rmse_px"].median(),
        "runtime median (ms)": g["runtime_ms"].median(),
    })
    return out.loc[_solver_order(df)]


def factor_table(df: pd.DataFrame, factor: str, metric: str = "rot_err_deg", agg: str = "median") -> pd.DataFrame:
    """Solver x factor-level pivot of ``metric`` (median by default)."""
    if factor not in df.columns or df[factor].nunique() < 2:
        return pd.DataFrame()
    if metric == "success":
        piv = df.pivot_table(index="solver", columns=factor, values="success", aggfunc="mean") * 100.0
    else:
        piv = df.pivot_table(index="solver", columns=factor, values=metric, aggfunc=agg)
    piv = piv.loc[[s for s in _solver_order(df) if s in piv.index]]
    if factor == "num_points_setting":
        order = sorted(piv.columns, key=lambda c: (c == "all", int(c) if c != "all" else 0))
        piv = piv[order]
    piv.columns = [f"{factor}={c}" for c in piv.columns]
    return piv


def summarize_pnp(df: pd.DataFrame, out_dir: Path, tag: str = "pnp") -> Dict[str, Any]:
    """Write every PnP summary table.  Returns the Markdown sections and key numbers."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sections: List[str] = []
    key: Dict[str, Any] = {}
    all_points = df[df["num_points_setting"] == "all"] if "num_points_setting" in df.columns else df
    sweep_only = len(all_points) == 0
    base = df if sweep_only else all_points
    clean = base[(base["outlier_ratio"] == 0)]
    contaminated = base[(base["outlier_ratio"] > 0)]
    if sweep_only:
        sections.append(write_table(solver_overview(base), out_dir / f"{tag}_overview_all",
                                    "Solver overview - all subset sizes pooled (outlier-free conditions)",
                                    "Success = rotation error <= 5 deg and relative translation error <= 5 %."))
    else:
        sections.append(write_table(solver_overview(base), out_dir / f"{tag}_overview_all", "Solver overview - all conditions",
                                    "Success = rotation error <= 5 deg and relative translation error <= 5 %. "
                                    "Errors are medians over every evaluated sample (all visible correspondences)."))
        if len(clean):
            sections.append(write_table(solver_overview(clean), out_dir / f"{tag}_overview_outlier_free",
                                        "Solver overview - outlier-free conditions (noise / quantization only)"))
        if len(contaminated):
            sections.append(write_table(solver_overview(contaminated), out_dir / f"{tag}_overview_with_outliers",
                                        "Solver overview - conditions with outliers"))
    if not sweep_only:
        # Noise sweep: outlier-free, no quantization.
        noise = base[(base["outlier_ratio"] == 0) & (~base["quantize"].astype(bool))]
        if noise["noise_sigma"].nunique() > 1:
            sections.append(write_table(factor_table(noise, "noise_sigma"), out_dir / f"{tag}_rot_err_vs_noise",
                                        "Median rotation error (deg) vs Gaussian pixel noise sigma (outlier-free)"))
            sections.append(write_table(factor_table(noise, "noise_sigma", "reproj_rmse_px"), out_dir / f"{tag}_reproj_vs_noise",
                                        "Median reprojection RMSE (px) vs noise sigma (outlier-free)"))
        # Quantization.
        quant = base[(base["outlier_ratio"] == 0) & (base["noise_sigma"].isin([0.0, 0.5]))]
        if quant["quantize"].nunique() > 1:
            piv = quant.pivot_table(index="solver", columns=["noise_sigma", "quantize"], values="rot_err_deg", aggfunc="median")
            piv.columns = [f"sigma={s} quantized={'yes' if q else 'no'}" for s, q in piv.columns]
            piv = piv.loc[[s for s in _solver_order(quant) if s in piv.index]]
            sections.append(write_table(piv, out_dir / f"{tag}_rot_err_quantization",
                                        "Median rotation error (deg): effect of pixel quantization"))
        # Outlier sweep (uniform outliers, sigma = 0.5).
        outl = base[(base["outlier_type"] == "uniform") & (base["noise_sigma"] == 0.5) & (~base["quantize"].astype(bool))]
        if outl["outlier_ratio"].nunique() > 1:
            sections.append(write_table(factor_table(outl, "outlier_ratio", "success"), out_dir / f"{tag}_success_vs_outliers",
                                        "Success rate (%) vs outlier ratio (uniform outliers, sigma = 0.5 px)"))
            sections.append(write_table(factor_table(outl, "outlier_ratio"), out_dir / f"{tag}_rot_err_vs_outliers",
                                        "Median rotation error (deg) vs outlier ratio (uniform outliers, sigma = 0.5 px)"))
            rob = outl[outl["robust"].astype(bool)]
            if len(rob):
                sections.append(write_table(factor_table(rob, "outlier_ratio", "inlier_precision"), out_dir / f"{tag}_inlier_precision_vs_outliers",
                                            "Median inlier precision of robust solvers vs outlier ratio"))
                sections.append(write_table(factor_table(rob, "outlier_ratio", "inlier_recall"), out_dir / f"{tag}_inlier_recall_vs_outliers",
                                            "Median inlier recall of robust solvers vs outlier ratio"))
        # Outlier type.
        types = base[(base["outlier_ratio"].isin([0.2, 0.5])) & (base["noise_sigma"] == 0.5)]
        if types["outlier_type"].nunique() > 1:
            piv = types.pivot_table(index="solver", columns=["outlier_ratio", "outlier_type"], values="success", aggfunc="mean") * 100
            piv.columns = [f"ratio={r} type={t}" for r, t in piv.columns]
            piv = piv.loc[[s for s in _solver_order(types) if s in piv.index]]
            sections.append(write_table(piv, out_dir / f"{tag}_success_vs_outlier_type",
                                        "Success rate (%) by outlier type (uniform replacement vs swapped assignments)"))
        # Scene / camera factors on outlier-free data.
        for factor, title in [("scene_type", "scene type"), ("camera_model", "camera model"),
                              ("fov_class", "field-of-view class"), ("distortion_level", "distortion level")]:
            tab = factor_table(clean, factor)
            if len(tab):
                sections.append(write_table(tab, out_dir / f"{tag}_rot_err_by_{factor}",
                                            f"Median rotation error (deg) by {title} (outlier-free conditions)"))
        # Runtime.
        rt = base.pivot_table(index="solver", values="runtime_ms", aggfunc=["median", "mean", "max"])
        rt.columns = ["runtime median (ms)", "runtime mean (ms)", "runtime max (ms)"]
        rt = rt.loc[[s for s in _solver_order(base) if s in rt.index]]
        sections.append(write_table(rt, out_dir / f"{tag}_runtime", "Runtime per solve (all visible correspondences)"))
        # Failure reasons.
        fails = df[~df["ok"].astype(bool)]
        if len(fails):
            fr = fails.groupby(["solver", "failure_reason"]).size().rename("count").to_frame()
            sections.append(write_table(fr, out_dir / f"{tag}_failure_reasons", "Failure reasons (solver returned no estimate)"))
    # Number-of-points sweep (if present).
    sweep = df[df["num_points_setting"] != "all"] if "num_points_setting" in df.columns else pd.DataFrame()
    if len(sweep) and sweep["num_points_setting"].nunique() > 1:
        sw_clean = sweep[(sweep["outlier_ratio"] == 0)]
        if len(sw_clean):
            sections.append(write_table(factor_table(sw_clean, "num_points_setting"), out_dir / f"{tag}_rot_err_vs_num_points",
                                        "Median rotation error (deg) vs number of correspondences (outlier-free)"))
            sections.append(write_table(factor_table(sw_clean, "num_points_setting", "success"), out_dir / f"{tag}_success_vs_num_points",
                                        "Success rate (%) vs number of correspondences (outlier-free)"))
            sections.append(write_table(factor_table(sw_clean, "num_points_setting", "runtime_ms"), out_dir / f"{tag}_runtime_vs_num_points",
                                        "Median runtime (ms) vs number of correspondences (outlier-free)"))
    key["num_solves"] = int(len(df))
    key["num_samples"] = int(df["sample_id"].nunique())
    key["solvers"] = _solver_order(df)
    ov = solver_overview(base)
    key["best_success_all"] = {"solver": str(ov["success (%)"].idxmax()), "success_pct": float(ov["success (%)"].max())}
    if len(clean):
        ovc = solver_overview(clean)
        key["most_accurate_outlier_free"] = {"solver": str(ovc["rot err median (deg)"].idxmin()),
                                             "rot_err_median_deg": float(ovc["rot err median (deg)"].min())}
    return {"markdown": "\n".join(sections), "key": key}


# ----------------------------------------------------------------------------
# Calibration summaries
# ----------------------------------------------------------------------------
def summarize_calibration(df: pd.DataFrame, out_dir: Path, tag: str = "calibration") -> Dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sections: List[str] = []
    if len(df) == 0:
        return {"markdown": "", "key": {}}
    g = df.groupby("solver", sort=False)
    overview = pd.DataFrame({
        "solves": g.size(), "returned (%)": g["ok"].mean() * 100, "success (%)": g["success"].mean() * 100,
        "focal err median (%)": g["focal_err_pct"].median(), "cx err median (px)": g["cx_err_px"].median(),
        "cy err median (px)": g["cy_err_px"].median(), "rot err median (deg)": g["rot_err_deg"].median(),
        "reproj RMSE median (px)": g["reproj_rmse_px"].median(), "runtime median (ms)": g["runtime_ms"].median(),
    })
    sections.append(write_table(overview, out_dir / f"{tag}_overview", "Single-view uncalibrated DLT - overview",
                                "Success = mean focal-length error <= 5 % and rotation error <= 5 deg. Lens distortion is not "
                                "modelled by the DLT, so distorted cameras show a systematic bias."))
    for factor, title in [("camera_model", "camera model"), ("distortion_level", "distortion level"),
                          ("fov_class", "field-of-view class"), ("scene_type", "scene type")]:
        if df[factor].nunique() > 1:
            piv = df.pivot_table(index="solver", columns=factor, values="focal_err_pct", aggfunc="median")
            piv.columns = [f"{factor}={c}" for c in piv.columns]
            sections.append(write_table(piv, out_dir / f"{tag}_focal_err_by_{factor}",
                                        f"Median focal-length error (%) by {title}"))
    if df["noise_sigma"].nunique() > 1:
        sub = df[~df["quantize"].astype(bool)]
        if (sub["camera_model"] == "pinhole").any():
            sub = sub[sub["camera_model"] == "pinhole"]
        piv = sub.pivot_table(index="solver", columns="noise_sigma", values="focal_err_pct", aggfunc="median")
        piv.columns = [f"noise_sigma={c}" for c in piv.columns]
        sections.append(write_table(piv, out_dir / f"{tag}_focal_err_vs_noise",
                                    "Median focal-length error (%) vs noise sigma (pinhole cameras, no quantization)"))
    key = {"num_solves": int(len(df)),
           "median_focal_err_pct": {str(k): float(v) for k, v in g["focal_err_pct"].median().items()}}
    return {"markdown": "\n".join(sections), "key": key}


def summarize_multiview(df: pd.DataFrame, out_dir: Path, tag: str = "multiview") -> Dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sections: List[str] = []
    if len(df) == 0:
        return {"markdown": "", "key": {}}
    g = df.groupby("solver", sort=False)
    overview = pd.DataFrame({
        "rigs": g.size(), "returned (%)": g["ok"].mean() * 100, "success (%)": g["success"].mean() * 100,
        "focal err median (%)": g["focal_err_pct"].median(), "cx err median (px)": g["cx_err_px"].median(),
        "dist coeff RMSE median": g["dist_coeff_rmse"].median(), "rot err median (deg)": g["rot_err_deg"].median(),
        "reproj RMSE median (px)": g["reproj_rmse_px"].median(), "runtime median (ms)": g["runtime_ms"].median(),
    })
    sections.append(write_table(overview, out_dir / f"{tag}_overview", "Multi-view calibration - overview",
                                "Each rig = all views sharing one intrinsic set and one noise condition. "
                                "Success = mean focal error <= 1 % and mean rotation error <= 1 deg. "
                                "`opencv` = calibrateCamera / fisheye.calibrate, `ba_scratch` = from-scratch bundle adjustment."))
    for factor, title in [("camera_model", "camera model"), ("fov_class", "field-of-view class"),
                          ("noise_sigma", "noise sigma"), ("scene_type", "scene type")]:
        if df[factor].nunique() > 1:
            piv = df.pivot_table(index="solver", columns=factor, values="focal_err_pct", aggfunc="median")
            piv.columns = [f"{factor}={c}" for c in piv.columns]
            sections.append(write_table(piv, out_dir / f"{tag}_focal_err_by_{factor}", f"Median focal-length error (%) by {title}"))
            piv2 = df.pivot_table(index="solver", columns=factor, values="success", aggfunc="mean") * 100
            piv2.columns = [f"{factor}={c}" for c in piv2.columns]
            sections.append(write_table(piv2, out_dir / f"{tag}_success_by_{factor}", f"Success rate (%) by {title}"))
    key = {"num_rigs": int(df["sample_id"].nunique()),
           "success_pct": {str(k): float(v) for k, v in (g["success"].mean() * 100).items()}}
    return {"markdown": "\n".join(sections), "key": key}


def write_summary(results_dir: Path, parts: Dict[str, Dict[str, Any]], env: Optional[Dict[str, Any]] = None) -> Path:
    """Combine the Markdown sections of every task into ``results/summary.md``."""
    results_dir = Path(results_dir)
    lines = ["# Benchmark summary", ""]
    if env:
        lines.append("Environment: " + ", ".join(f"{k}={v}" for k, v in env.items() if v is not None))
        lines.append("")
    titles = {"pnp": "## Calibrated PnP", "pnp_sweep": "## Calibrated PnP - number-of-points sweep",
              "calibration": "## Single-view calibration (uncalibrated DLT)", "multiview": "## Multi-view calibration"}
    for name, part in parts.items():
        if not part or not part.get("markdown"):
            continue
        lines.append(titles.get(name, f"## {name}"))
        lines.append("")
        lines.append(part["markdown"])
    path = results_dir / "summary.md"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    with open(results_dir / "summary.json", "w", encoding="utf-8") as fh:
        json.dump({name: part.get("key", {}) for name, part in parts.items()} | {"environment": env or {}}, fh, indent=2)
    return path
