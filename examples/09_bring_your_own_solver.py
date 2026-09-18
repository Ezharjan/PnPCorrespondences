#!/usr/bin/env python
"""
Add a solver of your own and benchmark it against the shipped ones.

A solver is a function `solve(X, uv, K, **kwargs) -> PoseEstimate` plus one entry in
the `SOLVERS` registry; from there the benchmark, the summary tables and the figures
pick it up with no further wiring.  This script defines a real one - a calibrated DLT
followed by iteratively reweighted least squares with a Cauchy loss, which buys some
robustness without the hypothesise-and-verify machinery of RANSAC - registers it, and
runs the actual `run_pnp_benchmark` on a stratified subset so its row appears next to
the others in the real overview table.

    python examples/09_bring_your_own_solver.py --data data
    python examples/09_bring_your_own_solver.py --data data --max-samples 40 --query "outlier_ratio <= 0.2"
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.analysis import solver_overview  # noqa: E402
from pnpcorr.benchmark import run_pnp_benchmark, select_samples  # noqa: E402
from pnpcorr.cameras import project_pinhole  # noqa: E402
from pnpcorr.solvers import (SOLVERS, PoseEstimate, SolverSpec, available_solvers,  # noqa: E402
                             dlt_calibrated, solve_epnp)
from pnpcorr.storage import load_manifest  # noqa: E402


# ---------------------------------------------------------------------------
# The solver.  Signature and return type are the whole contract.
# ---------------------------------------------------------------------------
def solve_dlt_irls(X, uv, K, threshold: float = 3.0, cauchy_scale=None, irls_iters: int = 12,
                   **_) -> PoseEstimate:
    """
    Calibrated DLT (or EPnP on coplanar input) followed by IRLS with a Cauchy loss.

    Least squares gives every residual the same weight, so one gross mismatch can
    dominate the fit.  Re-weighting each correspondence by ``1 / (1 + (r / c)^2)`` after
    every iteration lets large residuals fall out of the estimate on their own.  It is
    a soft alternative to RANSAC - no sampling, no hypothesis set - but it has no breakdown
    guarantee, which is exactly the trade-off the outlier sweep of this dataset measures.

    ``inliers`` marks the correspondences whose final weight is above one half, which is
    exactly ``residual < c``.  The loss scale ``c`` therefore has to be the same number
    the robust solvers use as their inlier threshold, or the reported precision and
    recall would not be measuring the same thing as theirs - hence ``threshold``, which
    the benchmark passes to every solver (``max(2 px, 3 sigma)`` under ``--threshold
    auto``).  ``cauchy_scale`` overrides it when the two should differ.
    """
    X = np.asarray(X, dtype=np.float64)
    uv = np.asarray(uv, dtype=np.float64)
    if len(X) < 6:
        return PoseEstimate(False, reason="dlt_irls needs at least 6 correspondences")

    init = dlt_calibrated(X, uv, K)
    if not init.ok:
        init = solve_epnp(X, uv, K)          # coplanar input: the DLT is degenerate there
    if not init.ok:
        return PoseEstimate(False, reason=f"dlt_irls: initialisation failed ({init.reason})")

    params = np.concatenate([Rotation.from_matrix(init.R).as_rotvec(), init.t])
    weights = np.ones(len(X))
    scale = float(threshold if cauchy_scale is None else cauchy_scale)
    for _ in range(int(irls_iters)):
        def residuals(p, w=weights):
            R = Rotation.from_rotvec(p[:3]).as_matrix()
            proj, _ = project_pinhole(X, K, R, p[3:6])
            return (np.sqrt(w)[:, None] * (proj - uv)).ravel()

        try:
            result = least_squares(residuals, params, method="lm", max_nfev=100,
                                   xtol=1e-12, ftol=1e-12, gtol=1e-12)
        except Exception as exc:                                    # numerical edge cases
            return PoseEstimate(False, reason=f"dlt_irls: {type(exc).__name__}: {exc}"[:160])
        params = result.x
        R = Rotation.from_rotvec(params[:3]).as_matrix()
        proj, _ = project_pinhole(X, K, R, params[3:6])
        err = np.linalg.norm(proj - uv, axis=1)
        new_weights = 1.0 / (1.0 + (err / scale) ** 2)
        if np.max(np.abs(new_weights - weights)) < 1e-6:
            weights = new_weights
            break
        weights = new_weights

    R = Rotation.from_rotvec(params[:3]).as_matrix()
    t = params[3:6]
    if not (np.isfinite(R).all() and np.isfinite(t).all()):
        return PoseEstimate(False, reason="dlt_irls: non-finite result")
    return PoseEstimate(True, R, t, inliers=weights > 0.5, info={"final_weight_sum": float(weights.sum())})


def register() -> None:
    """Put the solver in the registry the benchmark, tables and figures read."""
    SOLVERS["dlt_irls"] = SolverSpec(
        name="dlt_irls",
        fn=solve_dlt_irls,
        family="classic",              # "classic" | "opencv" | "robust-classic" | "robust-opencv"
        min_points=6,                  # never called with fewer
        exact_points=False,            # not a minimal solver
        planar="any",                  # documentation only; the solver declines what it cannot do
        robust=True,                   # it returns an inlier mask, so it is scored on one
        needs_cv2=False,
        description="Calibrated DLT + IRLS with a Cauchy loss (soft robustness, no sampling)",
        reference="Holland & Welsch 1977; Hartley & Zisserman 2004",
    )
    # Figures give one fixed colour and marker per solver; an unregistered name falls
    # back to a positional colour, which would move as the solver list changes.
    # matplotlib is optional, so this half is skipped when it is not installed.
    try:
        from pnpcorr.plots import SOLVER_COLORS, SOLVER_MARKERS
    except ImportError:
        return
    SOLVER_COLORS.setdefault("dlt_irls", "#7a5c2e")
    SOLVER_MARKERS.setdefault("dlt_irls", "h")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data", help="dataset directory")
    parser.add_argument("--max-samples", type=int, default=24, help="stratified sample budget")
    parser.add_argument("--query", default=None, help="pandas query applied to the manifest")
    parser.add_argument("--split", default=None, help="restrict to one split")
    parser.add_argument("--against", default="dlt_lm,sqpnp,ransac_p3p,cv_usac_magsac",
                        help="shipped solvers to compare against")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    register()
    print(f"registered: {SOLVERS['dlt_irls'].name} ({SOLVERS['dlt_irls'].family}, "
          f"min_points={SOLVERS['dlt_irls'].min_points}, robust={SOLVERS['dlt_irls'].robust})")
    print(f"  {SOLVERS['dlt_irls'].description}\n")

    manifest = load_manifest(args.data)
    subset = select_samples(manifest, args.max_samples, args.split, args.query, args.seed)
    names = ["dlt_irls"] + [n.strip() for n in args.against.split(",") if n.strip()]
    runnable = available_solvers(names)          # OpenCV solvers drop out when it is absent
    print(f"{len(subset)} stratified samples, {len(runnable)} of {len(names)} solvers available "
          f"({subset['condition_id'].nunique()} noise conditions)\n")

    # The library's own benchmark, unmodified: the new solver goes through exactly the
    # same undistortion, thresholds, seeding and metrics as the shipped ones.
    df = run_pnp_benchmark(args.data, subset, names, ["all"], seed=args.seed, progress=False)
    overview = solver_overview(df)
    print(overview.to_string(float_format=lambda v: f"{v:.4g}"))

    clean = df[df["outlier_ratio"] == 0]
    dirty = df[df["outlier_ratio"] >= 0.5]
    print("\nwhere a soft loss stands relative to sampling:")
    for label, part in (("outlier-free", clean), ("50 % outliers and above", dirty)):
        if part.empty:
            continue
        row = part.groupby("solver")["success"].mean() * 100.0
        print(f"  {label:24s} " + "  ".join(f"{s.name}={row.get(s.name, float('nan')):5.1f}%"
                                            for s in runnable if s.name in row))
    fails = df[~df["ok"].astype(bool)]
    if len(fails):
        print("\nsolves that returned nothing:")
        for (name, reason), count in fails.groupby(["solver", "failure_reason"]).size().items():
            print(f"  {count:4d}  {name:16s} {reason}")

    print("\nTo keep it, move `solve_dlt_irls` and its `SolverSpec` into `pnpcorr/solvers.py` and give")
    print("it a colour in `pnpcorr.plots.SOLVER_COLORS`; `scripts/run_benchmark.py`, the summary")
    print("tables and every figure then include it with no further changes.")


if __name__ == "__main__":
    main()
