"""
Noise modeling and injection (Step 4 of the pipeline, README Section 5.6).

For one clean projection ``uv_clean`` (M, 2) a *condition* produces a noisy
observation ``uv`` (M, 2) and a boolean ``outlier_mask`` (M,):

1. Gaussian pixel noise  N(0, sigma^2) is added independently to u and v.
2. Outliers: ``floor(M * outlier_ratio)`` correspondences are selected at random.
   * ``uniform`` - their 2D coordinates are replaced by uniform random positions
                   inside the image bounds ``[0, W) x [0, H)``.
   * ``swap``    - their 2D observations are permuted among the selected set with
                   a derangement, so every selected 3D point receives the
                   observation of a different 3D point.
   * ``mixed``   - the first half of the selected set is replaced uniformly, the
                   second half is swapped.
   The mask marks every selected correspondence (its 2D observation does not
   belong to its 3D point).
3. Quantization: coordinates are rounded to the nearest integer pixel.  It is
   applied last so that every stored observation - inliers and outliers alike -
   lies on the sensor grid.

Noisy coordinates are deliberately *not* clipped to the image bounds, so the
Gaussian noise statistics are exact even at the image border.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Tuple

import numpy as np


def num_outliers(num_points: int, ratio: float) -> int:
    """
    ``floor(num_points * ratio)``, computed so that the result is the floor of the
    *exact* product rather than of its floating-point approximation.

    ``90 * 0.7`` evaluates to 62.99999999999999 in binary floating point, whose
    floor is 62 where the exact product is 63.  The generator and the validator
    both call this function, so the stored ``num_outliers`` attribute, the manifest
    column and the validator's expectation can never disagree.
    """
    m = int(num_points)
    return int(math.floor(m * float(ratio) + 1e-9))


def condition_name(cond: Dict[str, Any]) -> str:
    """Compact, filesystem-safe description, e.g. ``s0.50_q0_o0.20_uniform``."""
    return "s{:.2f}_q{:d}_o{:.2f}_{}".format(
        float(cond["noise_sigma"]), int(bool(cond["quantize"])), float(cond["outlier_ratio"]), cond["outlier_type"]
    )


def _derangement(rng: np.random.Generator, n: int) -> np.ndarray:
    """Random permutation of range(n) without fixed points (n >= 2)."""
    perm = rng.permutation(n)
    # A random cyclic shift of a random permutation has no fixed points.
    return np.roll(perm, 1)[np.argsort(perm)]


def apply_condition(rng: np.random.Generator, uv_clean: np.ndarray, cond: Dict[str, Any],
                    width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
    """Return ``(uv_noisy, outlier_mask)`` for one noise condition."""
    uv = np.array(uv_clean, dtype=np.float64, copy=True)
    m = uv.shape[0]
    sigma = float(cond["noise_sigma"])
    ratio = float(cond["outlier_ratio"])
    otype = str(cond["outlier_type"])
    quantize = bool(cond["quantize"])

    if sigma > 0.0:
        uv += rng.normal(0.0, sigma, uv.shape)

    outlier_mask = np.zeros(m, dtype=bool)
    n_out = num_outliers(m, ratio)
    if n_out > 0:
        sel = rng.choice(m, n_out, replace=False)
        outlier_mask[sel] = True
        if otype == "uniform":
            uniform_idx, swap_idx = sel, sel[:0]
        elif otype == "swap":
            uniform_idx, swap_idx = sel[:0], sel
        elif otype == "mixed":
            half = n_out // 2
            uniform_idx, swap_idx = sel[:half], sel[half:]
        else:
            raise ValueError(f"unknown outlier type '{otype}'")
        if swap_idx.size == 1:
            # A single correspondence cannot be swapped: replace it instead.
            uniform_idx = np.concatenate([uniform_idx, swap_idx])
            swap_idx = swap_idx[:0]
        if uniform_idx.size:
            uv[uniform_idx, 0] = rng.uniform(0.0, width, uniform_idx.size)
            uv[uniform_idx, 1] = rng.uniform(0.0, height, uniform_idx.size)
        if swap_idx.size >= 2:
            uv[swap_idx] = uv[swap_idx[_derangement(rng, swap_idx.size)]]

    if quantize:
        uv = np.round(uv)
    return uv, outlier_mask


def condition_attrs(cond: Dict[str, Any], outlier_mask: np.ndarray) -> Dict[str, Any]:
    return {
        "noise_sigma": float(cond["noise_sigma"]),
        "quantize": bool(cond["quantize"]),
        "outlier_ratio": float(cond["outlier_ratio"]),
        "outlier_type": str(cond["outlier_type"]),
        "num_outliers": int(outlier_mask.sum()),
        "name": condition_name(cond),
    }
