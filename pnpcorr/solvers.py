"""
PnP and camera-calibration solvers behind one common interface.

Every calibrated solver has the signature

    solve(X, uv, K, **kwargs) -> PoseEstimate

with ``X`` (n, 3) world points, ``uv`` (n, 2) *undistorted* pixel observations
(see :func:`pnpcorr.cameras.undistort_to_pinhole_pixels`) and ``K`` the 3x3
intrinsic matrix.  The estimate ``(R, t)`` satisfies ``X_c = R X_w + t``.

Families
--------
* ``classic`` - implemented from scratch with NumPy/SciPy:
    - ``dlt``          calibrated Direct Linear Transform (>= 6 non-coplanar points)
    - ``dlt_lm``       DLT followed by Levenberg-Marquardt reprojection refinement
    - ``ransac_dlt``   RANSAC with 6-point DLT hypotheses + LM (no OpenCV needed)
    - ``ransac_p3p``   RANSAC with 3-point P3P hypotheses (OpenCV P3P) + LM
* ``opencv`` - wrappers around ``cv2.solvePnP`` / ``cv2.solvePnPRansac``:
    - ``epnp``, ``epnp_lm``, ``p3p``, ``ap3p``, ``ippe``, ``iterative``, ``sqpnp``
    - ``cv_ransac_epnp``, ``cv_ransac_ap3p``, ``cv_ransac_epnp_lm``, ``cv_usac_magsac``

Uncalibrated / calibration solvers:
    - ``dlt_uncalibrated``     11-dof DLT -> K, R, t from one view (RQ decomposition)
    - ``dlt_uncalibrated_lm``  + LM refinement of the 11 parameters
    - ``calibrate_multiview``  OpenCV ``calibrateCamera`` / ``fisheye.calibrate``
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.linalg import rq
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

try:  # OpenCV is optional: the classic family works without it.
    import cv2  # type: ignore

    HAVE_CV2 = True
except ImportError:  # pragma: no cover
    cv2 = None
    HAVE_CV2 = False

from .cameras import (BROWN_CONRADY, KANNALA_BRANDT, PINHOLE, distort_points, normalized_from_pixel,
                      pixel_from_normalized, project_pinhole, transform_to_camera)
from .scenes import is_planar


@dataclass
class PoseEstimate:
    ok: bool
    R: Optional[np.ndarray] = None
    t: Optional[np.ndarray] = None
    inliers: Optional[np.ndarray] = None   # boolean mask over the input correspondences (robust solvers)
    K: Optional[np.ndarray] = None         # estimated intrinsics (uncalibrated solvers)
    reason: str = ""
    info: Dict[str, Any] = field(default_factory=dict)


def _fail(reason: str) -> PoseEstimate:
    return PoseEstimate(False, reason=reason)


def _finite_pose(R: np.ndarray, t: np.ndarray) -> bool:
    return bool(np.isfinite(R).all() and np.isfinite(t).all())


# ----------------------------------------------------------------------------
# Normalization helpers (Hartley)
# ----------------------------------------------------------------------------
def _normalize_3d(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    c = X.mean(axis=0)
    d = np.linalg.norm(X - c, axis=1).mean()
    s = math.sqrt(3.0) / max(d, 1e-12)
    T = np.eye(4)
    T[:3, :3] *= s
    T[:3, 3] = -s * c
    return (X - c) * s, T


def _normalize_2d(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    c = x.mean(axis=0)
    d = np.linalg.norm(x - c, axis=1).mean()
    s = math.sqrt(2.0) / max(d, 1e-12)
    T = np.eye(3)
    T[:2, :2] *= s
    T[:2, 2] = -s * c
    return (x - c) * s, T


def _dlt_projection_matrix(X: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Least-squares 3x4 projection matrix P with x ~ P [X; 1] (normalized DLT)."""
    Xn, T3 = _normalize_3d(X)
    xn, T2 = _normalize_2d(x)
    n = len(X)
    Xh = np.hstack([Xn, np.ones((n, 1))])
    A = np.zeros((2 * n, 12))
    A[0::2, 0:4] = Xh
    A[0::2, 8:12] = -xn[:, 0:1] * Xh
    A[1::2, 4:8] = Xh
    A[1::2, 8:12] = -xn[:, 1:2] * Xh
    _, _, Vt = np.linalg.svd(A, full_matrices=False)
    P = Vt[-1].reshape(3, 4)
    return np.linalg.inv(T2) @ P @ T3


# ----------------------------------------------------------------------------
# Classic solvers (from scratch)
# ----------------------------------------------------------------------------
def dlt_calibrated(X: np.ndarray, uv: np.ndarray, K: np.ndarray, **_) -> PoseEstimate:
    """Calibrated DLT: linear estimate of [R | t] from >= 6 non-coplanar points."""
    X = np.asarray(X, dtype=np.float64)
    uv = np.asarray(uv, dtype=np.float64)
    if len(X) < 6:
        return _fail("dlt needs at least 6 correspondences")
    if is_planar(X):
        return _fail("degenerate: coplanar points")
    xn, yn = normalized_from_pixel(uv[:, 0], uv[:, 1], K)
    P = _dlt_projection_matrix(X, np.column_stack([xn, yn]))
    M = P[:, :3]
    if np.linalg.det(M) < 0:
        P = -P
        M = -M
    U, S, Vt = np.linalg.svd(M)
    R = U @ Vt
    scale = float(S.mean())
    if scale <= 0 or not np.isfinite(scale):
        return _fail("dlt: singular projection matrix")
    t = P[:, 3] / scale
    if not _finite_pose(R, t):
        return _fail("dlt: non-finite result")
    return PoseEstimate(True, R, t, info={"condition": float(S.max() / max(S.min(), 1e-300))})


def _pose_from_params(p: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    return Rotation.from_rotvec(p[:3]).as_matrix(), p[3:6]


def refine_pose_lm(X: np.ndarray, uv: np.ndarray, K: np.ndarray, R0: np.ndarray, t0: np.ndarray,
                   max_nfev: int = 200) -> PoseEstimate:
    """Levenberg-Marquardt minimisation of the pixel reprojection error over (rotvec, t)."""
    X = np.asarray(X, dtype=np.float64)
    uv = np.asarray(uv, dtype=np.float64)

    def residuals(p):
        R, t = _pose_from_params(p)
        proj, _ = project_pinhole(X, K, R, t)
        return (proj - uv).ravel()

    p0 = np.concatenate([Rotation.from_matrix(R0).as_rotvec(), np.asarray(t0, dtype=np.float64).ravel()])
    method = "lm" if 2 * len(X) >= 6 else "trf"
    try:
        res = least_squares(residuals, p0, method=method, max_nfev=max_nfev, xtol=1e-12, ftol=1e-12, gtol=1e-12)
    except Exception as exc:  # pragma: no cover - numerical edge cases
        return _fail(f"lm: {exc}")
    R, t = _pose_from_params(res.x)
    if not _finite_pose(R, t):
        return _fail("lm: non-finite result")
    return PoseEstimate(True, R, t, info={"nfev": int(res.nfev), "cost": float(res.cost)})


def dlt_lm(X: np.ndarray, uv: np.ndarray, K: np.ndarray, **_) -> PoseEstimate:
    init = dlt_calibrated(X, uv, K)
    if not init.ok:
        return init
    return refine_pose_lm(X, uv, K, init.R, init.t)


# ----------------------------------------------------------------------------
# Uncalibrated DLT (single-view calibration)
# ----------------------------------------------------------------------------
def decompose_projection_matrix(P: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """P = K [R | t] with K upper-triangular (positive diagonal, K[2,2] = 1) and det(R) = +1."""
    M = P[:, :3]
    Kmat, R = rq(M)
    signs = np.sign(np.diag(Kmat))
    signs[signs == 0] = 1.0
    D = np.diag(signs)
    Kmat = Kmat @ D
    R = D @ R
    p4 = P[:, 3].copy()
    if np.linalg.det(R) < 0:
        R = -R
        p4 = -p4
    t = np.linalg.solve(Kmat, p4)
    Kmat = Kmat / Kmat[2, 2]
    return Kmat, R, t


def dlt_uncalibrated(X: np.ndarray, uv: np.ndarray, **_) -> PoseEstimate:
    """11-dof DLT: K, R, t from >= 6 non-coplanar points in a single view."""
    X = np.asarray(X, dtype=np.float64)
    uv = np.asarray(uv, dtype=np.float64)
    if len(X) < 6:
        return _fail("uncalibrated dlt needs at least 6 correspondences")
    if is_planar(X):
        return _fail("degenerate: coplanar points")
    P = _dlt_projection_matrix(X, uv)
    try:
        Kmat, R, t = decompose_projection_matrix(P)
    except np.linalg.LinAlgError:
        return _fail("dlt: singular projection matrix")
    if not (_finite_pose(R, t) and np.isfinite(Kmat).all()):
        return _fail("dlt: non-finite result")
    _, depth = project_pinhole(X, Kmat, R, t)
    if np.median(depth) <= 0:
        return _fail("dlt: cheirality violated")
    return PoseEstimate(True, R, t, K=Kmat)


def _K_from_params(p: np.ndarray) -> np.ndarray:
    return np.array([[p[0], p[2], p[3]], [0.0, p[1], p[4]], [0.0, 0.0, 1.0]])


def refine_full_lm(X: np.ndarray, uv: np.ndarray, K0: np.ndarray, R0: np.ndarray, t0: np.ndarray,
                   max_nfev: int = 300) -> PoseEstimate:
    """LM refinement of (fx, fy, s, cx, cy, rotvec, t) - 11 parameters."""
    X = np.asarray(X, dtype=np.float64)
    uv = np.asarray(uv, dtype=np.float64)

    def residuals(p):
        R, t = _pose_from_params(p[5:11])
        proj, _ = project_pinhole(X, _K_from_params(p[:5]), R, t)
        return (proj - uv).ravel()

    p0 = np.concatenate([[K0[0, 0], K0[1, 1], K0[0, 1], K0[0, 2], K0[1, 2]],
                         Rotation.from_matrix(R0).as_rotvec(), np.asarray(t0).ravel()])
    try:
        res = least_squares(residuals, p0, method="lm", max_nfev=max_nfev, xtol=1e-12, ftol=1e-12, gtol=1e-12)
    except Exception as exc:  # pragma: no cover
        return _fail(f"lm: {exc}")
    R, t = _pose_from_params(res.x[5:11])
    Kmat = _K_from_params(res.x[:5])
    if not (_finite_pose(R, t) and np.isfinite(Kmat).all()):
        return _fail("lm: non-finite result")
    return PoseEstimate(True, R, t, K=Kmat, info={"nfev": int(res.nfev)})


def dlt_uncalibrated_lm(X: np.ndarray, uv: np.ndarray, **_) -> PoseEstimate:
    init = dlt_uncalibrated(X, uv)
    if not init.ok:
        return init
    return refine_full_lm(X, uv, init.K, init.R, init.t)


# ----------------------------------------------------------------------------
# OpenCV wrappers
# ----------------------------------------------------------------------------
def _require_cv2() -> None:
    if not HAVE_CV2:
        raise RuntimeError("OpenCV (opencv-python) is required for this solver")


def _cv_error(exc: Exception) -> str:
    """One-line message for any OpenCV failure (``cv2.error`` or an API change)."""
    text = str(exc).strip().splitlines()
    detail = text[-1] if text else exc.__class__.__name__
    return f"opencv: {exc.__class__.__name__}: {detail}"[:160]


def _fisheye_flag(name: str) -> int:
    """
    Fisheye calibration flag by name.

    OpenCV 4.x exposes them as ``cv2.fisheye.CALIB_*`` and OpenCV 5.x moved them
    to the top-level ``cv2`` namespace; both spellings are accepted here so the
    same code runs on either major version.
    """
    for namespace in (getattr(cv2, "fisheye", None), cv2):
        value = getattr(namespace, name, None) if namespace is not None else None
        if value is not None:
            return int(value)
    raise AttributeError(f"OpenCV {cv2.__version__} exposes neither cv2.fisheye.{name} nor cv2.{name}")


def _cv_pose(rvec, tvec) -> Tuple[np.ndarray, np.ndarray]:
    R, _ = cv2.Rodrigues(np.asarray(rvec, dtype=np.float64).reshape(3, 1))
    return R, np.asarray(tvec, dtype=np.float64).ravel()


def _canonicalize(X: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Express coplanar points in their own plane frame (z = 0 exactly).

    Purpose: make the result independent of the arbitrary orientation of the world
    frame.  A planar target expressed in a rotated world frame is coplanar only up
    to floating-point rounding, and OpenCV's EPnP amplifies that 1e-16 third
    dimension badly once the observations carry noise.  Measured on tilted planes,
    60 points, median rotation error (percentage of solves above 1 deg):

    ======  =========================  ======================  ==========================
    sigma   axis-aligned plane, raw    rotated frame, raw      rotated frame, canonical
    ======  =========================  ======================  ==========================
    0.0 px  1.2e-12 deg (48 %)         1.9e-09 deg (10 %)      1.5e-12 deg (46 %)
    0.1 px  4.5e-02 deg (48 %)         2.5e+01 deg (59 %)      3.1e-02 deg (46 %)
    0.5 px  2.3e-01 deg (48 %)         2.0e+01 deg (65 %)      1.5e-01 deg (46 %)
    2.0 px  8.2e-01 deg (49 %)         1.5e+01 deg (74 %)      6.2e-01 deg (46 %)
    ======  =========================  ======================  ==========================

    The canonical frame reproduces the axis-aligned result at every noise level, so
    the benchmark measures the solver rather than the world frame it was handed.
    EPnP's ~47 % failure rate on planar targets survives the transform and is a
    property of OpenCV's implementation, not of this preprocessing.  The transform
    is applied to every OpenCV solver uniformly, never selectively, and mapping the
    pose back is an exact rigid re-parametrisation.

    Returns ``(X_local, Rp, c)`` with ``X_local = Rp (X - c)``; ``Rp``/``c`` are
    ``None`` for non-planar inputs.
    """
    X = np.asarray(X, dtype=np.float64)
    if len(X) < 4 or not is_planar(X, rel_tol=1e-8):
        return X, None, None
    c = X.mean(axis=0)
    _, _, Vt = np.linalg.svd(X - c, full_matrices=False)
    Rp = Vt.copy()
    if np.linalg.det(Rp) < 0:
        Rp[2] = -Rp[2]
    Xl = (X - c) @ Rp.T
    Xl[:, 2] = 0.0
    return np.ascontiguousarray(Xl), Rp, c


def _pose_from_canonical(R_l: np.ndarray, t_l: np.ndarray, Rp: Optional[np.ndarray], c: Optional[np.ndarray]
                         ) -> Tuple[np.ndarray, np.ndarray]:
    if Rp is None:
        return R_l, t_l
    R = R_l @ Rp
    return R, t_l - R @ c


def _cv_solve(flag: int, X: np.ndarray, uv: np.ndarray, K: np.ndarray) -> PoseEstimate:
    _require_cv2()
    X, Rp, c = _canonicalize(X)
    uv = np.ascontiguousarray(uv, dtype=np.float64)
    try:
        ok, rvec, tvec = cv2.solvePnP(X, uv, np.asarray(K, dtype=np.float64), None, flags=flag)
    except Exception as exc:
        return _fail(_cv_error(exc))
    if not ok:
        return _fail("opencv: solvePnP returned false")
    R, t = _pose_from_canonical(*_cv_pose(rvec, tvec), Rp, c)
    if not _finite_pose(R, t):
        return _fail("opencv: non-finite result")
    return PoseEstimate(True, R, t)


def solve_epnp(X, uv, K, **_):
    return _cv_solve(cv2.SOLVEPNP_EPNP, X, uv, K) if HAVE_CV2 else _fail("opencv missing")


def solve_epnp_lm(X, uv, K, **_):
    init = solve_epnp(X, uv, K)
    if not init.ok:
        return init
    return refine_pose_lm(X, uv, K, init.R, init.t)


def solve_p3p(X, uv, K, **_):
    if len(X) != 4:
        return _fail("p3p is evaluated with exactly 4 correspondences")
    return _cv_solve(cv2.SOLVEPNP_P3P, X, uv, K) if HAVE_CV2 else _fail("opencv missing")


def solve_ap3p(X, uv, K, **_):
    if len(X) != 4:
        return _fail("ap3p is evaluated with exactly 4 correspondences")
    return _cv_solve(cv2.SOLVEPNP_AP3P, X, uv, K) if HAVE_CV2 else _fail("opencv missing")


def solve_iterative(X, uv, K, **_):
    if len(X) < 6 and not is_planar(X):
        return _fail("iterative needs >= 6 non-coplanar points (or >= 4 coplanar)")
    return _cv_solve(cv2.SOLVEPNP_ITERATIVE, X, uv, K) if HAVE_CV2 else _fail("opencv missing")


def solve_sqpnp(X, uv, K, **_):
    return _cv_solve(cv2.SOLVEPNP_SQPNP, X, uv, K) if HAVE_CV2 else _fail("opencv missing")


def solve_ippe(X, uv, K, **_):
    """IPPE on coplanar points (the plane is canonicalised to z = 0 by ``_cv_solve``)."""
    if not HAVE_CV2:
        return _fail("opencv missing")
    X = np.asarray(X, dtype=np.float64)
    if len(X) < 4:
        return _fail("ippe needs at least 4 correspondences")
    if not is_planar(X, rel_tol=1e-6):
        return _fail("ippe requires coplanar points")
    return _cv_solve(cv2.SOLVEPNP_IPPE, X, uv, K)


def _cv_ransac(flag: int, X, uv, K, threshold: float, max_iters: int, confidence: float,
               refine_lm: bool = False) -> PoseEstimate:
    _require_cv2()
    X, Rp, c = _canonicalize(X)
    uv = np.ascontiguousarray(uv, dtype=np.float64)
    try:
        ok, rvec, tvec, inl = cv2.solvePnPRansac(
            X, uv, np.asarray(K, dtype=np.float64), None, iterationsCount=int(max_iters),
            reprojectionError=float(threshold), confidence=float(confidence), flags=flag)
    except Exception as exc:
        return _fail(_cv_error(exc))
    if not ok or inl is None:
        return _fail("opencv: ransac found no consensus")
    mask = np.zeros(len(X), dtype=bool)
    mask[np.asarray(inl).ravel()] = True
    R, t = _pose_from_canonical(*_cv_pose(rvec, tvec), Rp, c)
    X = np.asarray(X) if Rp is None else (X @ Rp) + c  # back to world coordinates for refinement
    if refine_lm and mask.sum() >= 4:
        ref = refine_pose_lm(X[mask], uv[mask], K, R, t)
        if ref.ok:
            R, t = ref.R, ref.t
            proj, z = project_pinhole(X, K, R, t)
            mask = (np.linalg.norm(proj - uv, axis=1) < threshold) & (z > 0)
    if not _finite_pose(R, t):
        return _fail("opencv: non-finite result")
    return PoseEstimate(True, R, t, inliers=mask)


def solve_cv_ransac_epnp(X, uv, K, threshold=3.0, max_iters=1000, confidence=0.99, **_):
    return _cv_ransac(cv2.SOLVEPNP_EPNP, X, uv, K, threshold, max_iters, confidence) if HAVE_CV2 else _fail("opencv missing")


def solve_cv_ransac_epnp_lm(X, uv, K, threshold=3.0, max_iters=1000, confidence=0.99, **_):
    return _cv_ransac(cv2.SOLVEPNP_EPNP, X, uv, K, threshold, max_iters, confidence, refine_lm=True) if HAVE_CV2 else _fail("opencv missing")


def solve_cv_ransac_ap3p(X, uv, K, threshold=3.0, max_iters=1000, confidence=0.99, **_):
    return _cv_ransac(cv2.SOLVEPNP_AP3P, X, uv, K, threshold, max_iters, confidence) if HAVE_CV2 else _fail("opencv missing")


def solve_cv_usac_magsac(X, uv, K, threshold=3.0, max_iters=1000, confidence=0.99, **_):
    """OpenCV USAC framework with the MAGSAC++ scoring function."""
    if not HAVE_CV2 or not hasattr(cv2, "UsacParams"):
        return _fail("opencv usac unavailable")
    X, Rp, c = _canonicalize(X)
    uv = np.ascontiguousarray(uv, dtype=np.float64)
    params = cv2.UsacParams()
    params.score = cv2.SCORE_METHOD_MAGSAC
    params.sampler = cv2.SAMPLING_UNIFORM
    params.loMethod = cv2.LOCAL_OPTIM_SIGMA
    params.threshold = float(threshold)
    params.maxIterations = int(max_iters)
    params.confidence = float(confidence)
    try:
        result = cv2.solvePnPRansac(X, uv, np.asarray(K, dtype=np.float64), None, params=params)
    except Exception as exc:
        return _fail(_cv_error(exc))
    ok, rvec, tvec, inl = result[0], result[-3], result[-2], result[-1]
    if not ok or inl is None:
        return _fail("opencv: usac found no consensus")
    mask = np.zeros(len(X), dtype=bool)
    mask[np.asarray(inl).ravel()] = True
    R, t = _pose_from_canonical(*_cv_pose(rvec, tvec), Rp, c)
    if not _finite_pose(R, t):
        return _fail("opencv: non-finite result")
    return PoseEstimate(True, R, t, inliers=mask)


# ----------------------------------------------------------------------------
# RANSAC from scratch
# ----------------------------------------------------------------------------
def _hypotheses_p3p(X, uv, K) -> List[Tuple[np.ndarray, np.ndarray]]:
    try:
        n, rvecs, tvecs = cv2.solveP3P(np.ascontiguousarray(X), np.ascontiguousarray(uv),
                                       np.asarray(K, dtype=np.float64), None, flags=cv2.SOLVEPNP_P3P)
    except Exception:
        return []
    out = []
    for i in range(int(n)):
        R, t = _cv_pose(rvecs[i], tvecs[i])
        if _finite_pose(R, t):
            out.append((R, t))
    return out


def _hypotheses_dlt(X, uv, K) -> List[Tuple[np.ndarray, np.ndarray]]:
    est = dlt_calibrated(X, uv, K)
    return [(est.R, est.t)] if est.ok else []


def ransac_pnp(X: np.ndarray, uv: np.ndarray, K: np.ndarray, minimal: str = "p3p", threshold: float = 3.0,
               max_iters: int = 1000, confidence: float = 0.99, seed: int = 0, refine: bool = True,
               **_) -> PoseEstimate:
    """
    Classic RANSAC: random minimal samples, inlier counting on the pixel
    reprojection error (and positive depth), adaptive iteration count, and a
    final non-minimal refinement (DLT/EPnP + LM) on the consensus set with one
    re-scoring pass.
    """
    X = np.asarray(X, dtype=np.float64)
    uv = np.asarray(uv, dtype=np.float64)
    n = len(X)
    if minimal == "p3p":
        if not HAVE_CV2:
            return _fail("ransac_p3p needs opencv for the minimal solver")
        m, hypotheses = 3, _hypotheses_p3p
    elif minimal == "dlt":
        if is_planar(X):
            return _fail("degenerate: coplanar points")
        m, hypotheses = 6, _hypotheses_dlt
    else:
        raise ValueError(f"unknown minimal solver '{minimal}'")
    if n < m + 1:
        return _fail(f"ransac needs at least {m + 1} correspondences")
    rng = np.random.default_rng(seed)
    best_count, best_mask, best_pose = 0, None, None
    iters = int(max_iters)
    it = 0
    while it < iters:
        it += 1
        idx = rng.choice(n, m, replace=False)
        for R, t in hypotheses(X[idx], uv[idx], K):
            proj, z = project_pinhole(X, K, R, t)
            err = np.linalg.norm(proj - uv, axis=1)
            inl = (err < threshold) & (z > 0)
            cnt = int(inl.sum())
            if cnt > best_count:
                best_count, best_mask, best_pose = cnt, inl, (R, t)
                w = cnt / n
                if w >= 1.0:
                    iters = it
                else:
                    denom = math.log1p(-(w ** m))  # log(1 - w^m), accurate for tiny w^m
                    if denom >= 0.0:
                        iters = int(max_iters)
                    else:
                        iters = min(int(max_iters), int(math.ceil(math.log(1.0 - confidence) / denom)))
    if best_pose is None or best_count < max(m, 4):
        return _fail("ransac: no consensus")
    R, t = best_pose
    mask = best_mask
    if refine:
        for _ in range(2):  # local optimisation: refine on inliers, re-score, repeat once
            Xi, uvi = X[mask], uv[mask]
            init = dlt_calibrated(Xi, uvi, K) if (len(Xi) >= 6 and not is_planar(Xi)) else None
            R0, t0 = (init.R, init.t) if (init is not None and init.ok) else (R, t)
            ref = refine_pose_lm(Xi, uvi, K, R0, t0)
            if not ref.ok:
                break
            proj, z = project_pinhole(X, K, ref.R, ref.t)
            new_mask = (np.linalg.norm(proj - uv, axis=1) < threshold) & (z > 0)
            if new_mask.sum() >= mask.sum():
                R, t, mask = ref.R, ref.t, new_mask
            else:
                break
    return PoseEstimate(True, R, t, inliers=mask, info={"iterations": it, "consensus": int(mask.sum())})


def solve_ransac_p3p(X, uv, K, threshold=3.0, max_iters=1000, confidence=0.99, seed=0, **_):
    return ransac_pnp(X, uv, K, "p3p", threshold, max_iters, confidence, seed)


def solve_ransac_dlt(X, uv, K, threshold=3.0, max_iters=1000, confidence=0.99, seed=0, **_):
    return ransac_pnp(X, uv, K, "dlt", threshold, max_iters, confidence, seed)


# ----------------------------------------------------------------------------
# Multi-view calibration (OpenCV)
# ----------------------------------------------------------------------------
@dataclass
class CalibrationEstimate:
    ok: bool
    K: Optional[np.ndarray] = None
    dist: Optional[np.ndarray] = None
    poses: Optional[List[Tuple[np.ndarray, np.ndarray]]] = None
    rms: float = float("nan")
    reason: str = ""


def calibrate_multiview(views: Sequence[Tuple[np.ndarray, np.ndarray]], image_size: Tuple[int, int],
                        K_init: np.ndarray, model: str = "brown_conrady") -> CalibrationEstimate:
    """
    Joint intrinsic + distortion + pose estimation from several views sharing
    the same camera, using OpenCV's bundle-adjustment based calibration.
    ``views`` is a sequence of ``(X (n,3), uv_raw (n,2))`` pairs of *distorted*
    observations.  ``K_init`` is used as the intrinsic guess (non-planar rigs
    need one).  ``model`` selects ``calibrateCamera`` (Brown-Conrady, 5
    coefficients) or ``fisheye.calibrate`` (Kannala-Brandt, 4 coefficients).
    """
    if not HAVE_CV2:
        return CalibrationEstimate(False, reason="opencv missing")
    Kg = np.asarray(K_init, dtype=np.float64).copy()
    try:
        if model == "kannala_brandt":
            objs = [np.ascontiguousarray(X, dtype=np.float64).reshape(1, -1, 3) for X, _ in views]
            imgs = [np.ascontiguousarray(uv, dtype=np.float64).reshape(1, -1, 2) for _, uv in views]
            flags = (_fisheye_flag("CALIB_USE_INTRINSIC_GUESS") | _fisheye_flag("CALIB_FIX_SKEW")
                     | _fisheye_flag("CALIB_RECOMPUTE_EXTRINSIC"))
            criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 200, 1e-10)
            rms, K, D, rvecs, tvecs = cv2.fisheye.calibrate(
                objs, imgs, (int(image_size[0]), int(image_size[1])), Kg, np.zeros((4, 1)), flags=flags,
                criteria=criteria)
            dist = np.asarray(D, dtype=np.float64).ravel()[:4]
        else:
            objs = [np.ascontiguousarray(X, dtype=np.float32) for X, _ in views]
            imgs = [np.ascontiguousarray(uv, dtype=np.float32) for _, uv in views]
            flags = cv2.CALIB_USE_INTRINSIC_GUESS
            criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 200, 1e-10)
            rms, K, D, rvecs, tvecs = cv2.calibrateCamera(
                objs, imgs, (int(image_size[0]), int(image_size[1])), Kg, None, flags=flags, criteria=criteria)
            dist = np.asarray(D, dtype=np.float64).ravel()[:5]
    except Exception as exc:
        return CalibrationEstimate(False, reason=_cv_error(exc))
    poses = [_cv_pose(r, t) for r, t in zip(rvecs, tvecs)]
    K = np.asarray(K, dtype=np.float64)
    if not np.isfinite(K).all() or not all(_finite_pose(R, t) for R, t in poses):
        return CalibrationEstimate(False, reason="opencv: non-finite calibration")
    return CalibrationEstimate(True, K, dist, poses, float(rms))


def calibrate_multiview_ba(views: Sequence[Tuple[np.ndarray, np.ndarray]], image_size: Tuple[int, int],
                           K_init: np.ndarray, model: str = "brown_conrady", max_nfev: int = 100
                           ) -> CalibrationEstimate:
    """
    From-scratch multi-view calibration by bundle adjustment: intrinsics
    (fx, fy, cx, cy), the distortion coefficients of ``model`` (5 Brown-Conrady,
    4 Kannala-Brandt or none) and one pose per view are jointly refined with a
    sparse trust-region least-squares solver on the pixel reprojection error.
    Poses are initialised with the calibrated DLT (or EPnP) using ``K_init``.
    """
    n_coeffs = {BROWN_CONRADY: 5, KANNALA_BRANDT: 4, PINHOLE: 0}[model]
    K0 = np.asarray(K_init, dtype=np.float64)
    poses0 = []
    for X, uv in views:
        est = dlt_calibrated(X, uv, K0)
        if not est.ok and HAVE_CV2:
            est = solve_epnp(X, uv, K0)
        if not est.ok:
            return CalibrationEstimate(False, reason="ba: pose initialisation failed (" + est.reason + ")")
        poses0.append(np.concatenate([Rotation.from_matrix(est.R).as_rotvec(), est.t]))
    p0 = np.concatenate([[K0[0, 0], K0[1, 1], K0[0, 2], K0[1, 2]], np.zeros(n_coeffs)] + poses0)
    n_intr = 4 + n_coeffs
    counts = [len(X) for X, _ in views]
    offsets = np.concatenate([[0], np.cumsum(counts)])
    obs = np.vstack([uv for _, uv in views])

    def unpack(p):
        K = np.array([[p[0], 0.0, p[2]], [0.0, p[1], p[3]], [0.0, 0.0, 1.0]])
        coeffs = p[4:4 + n_coeffs] if n_coeffs else np.zeros(5)
        return K, coeffs

    def residuals(p):
        K, coeffs = unpack(p)
        out = np.empty((offsets[-1], 2))
        for i, (X, _) in enumerate(views):
            q = p[n_intr + 6 * i: n_intr + 6 * i + 6]
            R = Rotation.from_rotvec(q[:3]).as_matrix()
            pc = transform_to_camera(X, R, q[3:6])
            z = np.where(np.abs(pc[:, 2]) > 1e-12, pc[:, 2], 1e-12)
            xd, yd = distort_points(pc[:, 0] / z, pc[:, 1] / z, model, coeffs)
            u, v = pixel_from_normalized(xd, yd, K)
            out[offsets[i]:offsets[i + 1], 0] = u
            out[offsets[i]:offsets[i + 1], 1] = v
        return (out - obs).ravel()

    # Jacobian sparsity: every residual depends on the intrinsics and on its own view's pose.
    from scipy.sparse import lil_matrix
    sparsity = lil_matrix((2 * offsets[-1], len(p0)), dtype=int)
    sparsity[:, :n_intr] = 1
    for i in range(len(views)):
        sparsity[2 * offsets[i]:2 * offsets[i + 1], n_intr + 6 * i:n_intr + 6 * i + 6] = 1
    try:
        res = least_squares(residuals, p0, jac_sparsity=sparsity, method="trf", x_scale="jac",
                            max_nfev=max_nfev, xtol=1e-10, ftol=1e-10, gtol=1e-10)
    except Exception as exc:  # pragma: no cover
        return CalibrationEstimate(False, reason=f"ba: {exc}")
    K, coeffs = unpack(res.x)
    poses = []
    for i in range(len(views)):
        q = res.x[n_intr + 6 * i: n_intr + 6 * i + 6]
        poses.append((Rotation.from_rotvec(q[:3]).as_matrix(), q[3:6].copy()))
    if not np.isfinite(res.x).all():
        return CalibrationEstimate(False, reason="ba: non-finite result")
    rms = float(np.sqrt(np.mean(np.sum(residuals(res.x).reshape(-1, 2) ** 2, axis=1))))
    dist = np.asarray(coeffs, dtype=np.float64) if n_coeffs else np.zeros(5)
    return CalibrationEstimate(True, K, dist, poses, rms)


# ----------------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class SolverSpec:
    name: str
    fn: Callable[..., PoseEstimate]
    family: str                 # "classic" | "opencv" | "robust-classic" | "robust-opencv"
    min_points: int
    exact_points: bool = False  # minimal solvers: evaluated only with exactly ``min_points``
    planar: str = "any"         # "any" | "only" | "never"
    robust: bool = False
    needs_cv2: bool = False
    description: str = ""
    reference: str = ""


SOLVERS: Dict[str, SolverSpec] = {
    "dlt": SolverSpec("dlt", dlt_calibrated, "classic", 6, planar="never",
                      description="Calibrated Direct Linear Transform (SVD on the 12-vector, orthonormalised)",
                      reference="Abdel-Aziz & Karara 1971; Hartley & Zisserman 2004"),
    "dlt_lm": SolverSpec("dlt_lm", dlt_lm, "classic", 6, planar="never",
                         description="DLT initialisation + Levenberg-Marquardt reprojection refinement",
                         reference="Hartley & Zisserman 2004"),
    "epnp": SolverSpec("epnp", solve_epnp, "opencv", 4, needs_cv2=True,
                       description="EPnP: O(n) non-iterative solver with 4 control points",
                       reference="Lepetit, Moreno-Noguer & Fua, IJCV 2009"),
    "epnp_lm": SolverSpec("epnp_lm", solve_epnp_lm, "opencv", 4, needs_cv2=True,
                          description="EPnP initialisation + LM refinement",
                          reference="Lepetit et al. 2009 + LM"),
    "p3p": SolverSpec("p3p", solve_p3p, "opencv", 4, exact_points=True, needs_cv2=True,
                      description="Minimal P3P (3 points + 1 for disambiguation)",
                      reference="Gao et al. 2003 / Ding et al. 2023 (OpenCV >= 4.9)"),
    "ap3p": SolverSpec("ap3p", solve_ap3p, "opencv", 4, exact_points=True, needs_cv2=True,
                       description="Algebraic P3P (3 points + 1 for disambiguation)",
                       reference="Ke & Roumeliotis, CVPR 2017"),
    "ippe": SolverSpec("ippe", solve_ippe, "opencv", 4, planar="only", needs_cv2=True,
                       description="Infinitesimal Plane-based Pose Estimation (planar scenes only)",
                       reference="Collins & Bartoli, IJCV 2014"),
    "iterative": SolverSpec("iterative", solve_iterative, "opencv", 6, needs_cv2=True,
                            description="OpenCV SOLVEPNP_ITERATIVE: DLT/homography init + LM",
                            reference="OpenCV calib3d"),
    "sqpnp": SolverSpec("sqpnp", solve_sqpnp, "opencv", 4, needs_cv2=True,
                        description="SQPnP: globally optimal sequential quadratic programming solver",
                        reference="Terzakis & Lourakis, ECCV 2020"),
    "ransac_dlt": SolverSpec("ransac_dlt", solve_ransac_dlt, "robust-classic", 12, planar="never", robust=True,
                             description="From-scratch RANSAC with 6-point DLT hypotheses + LM refinement",
                             reference="Fischler & Bolles 1981"),
    "ransac_p3p": SolverSpec("ransac_p3p", solve_ransac_p3p, "robust-classic", 8, robust=True, needs_cv2=True,
                             description="From-scratch RANSAC with 3-point P3P hypotheses + LM refinement",
                             reference="Fischler & Bolles 1981; Ding et al. 2023"),
    "cv_ransac_epnp": SolverSpec("cv_ransac_epnp", solve_cv_ransac_epnp, "robust-opencv", 8, robust=True, needs_cv2=True,
                                 description="OpenCV solvePnPRansac with EPnP hypotheses",
                                 reference="OpenCV calib3d"),
    "cv_ransac_epnp_lm": SolverSpec("cv_ransac_epnp_lm", solve_cv_ransac_epnp_lm, "robust-opencv", 8, robust=True,
                                    needs_cv2=True, description="OpenCV solvePnPRansac (EPnP) + LM on the inliers",
                                    reference="OpenCV calib3d + LM"),
    "cv_ransac_ap3p": SolverSpec("cv_ransac_ap3p", solve_cv_ransac_ap3p, "robust-opencv", 8, robust=True, needs_cv2=True,
                                 description="OpenCV solvePnPRansac with AP3P hypotheses",
                                 reference="OpenCV calib3d; Ke & Roumeliotis 2017"),
    "cv_usac_magsac": SolverSpec("cv_usac_magsac", solve_cv_usac_magsac, "robust-opencv", 8, robust=True, needs_cv2=True,
                                 description="OpenCV USAC with MAGSAC++ scoring and sigma-consensus local optimisation",
                                 reference="Barath et al., CVPR 2020 (MAGSAC++)"),
}

CALIBRATION_SOLVERS: Dict[str, Callable[..., PoseEstimate]] = {
    "dlt_uncalibrated": dlt_uncalibrated,
    "dlt_uncalibrated_lm": dlt_uncalibrated_lm,
}


def available_solvers(names: Optional[Sequence[str]] = None) -> List[SolverSpec]:
    """Solver specs (optionally filtered by name) that can run in this environment."""
    specs = [SOLVERS[n] for n in (names or SOLVERS.keys())]
    return [s for s in specs if HAVE_CV2 or not s.needs_cv2]
