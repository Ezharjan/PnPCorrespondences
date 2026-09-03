"""
Camera models: intrinsics, lens distortion (forward and inverse) and projection.

Conventions (identical to OpenCV and to Section 5.1 of the README):

* A world point ``X_w`` is mapped to the camera frame by ``X_c = R @ X_w + t``.
* Normalized coordinates ``x_n = x_c / z_c``, ``y_n = y_c / z_c``.
* Lens distortion maps ``(x_n, y_n)`` to ``(x_d, y_d)``:

  - ``pinhole``          : identity.
  - ``brown_conrady``    : ``coeffs = (k1, k2, p1, p2, k3)`` (OpenCV ordering),
                           radial ``1 + k1 r^2 + k2 r^4 + k3 r^6`` plus tangential terms.
  - ``kannala_brandt``   : ``coeffs = (k1, k2, k3, k4)``, ``theta = atan(r)``,
                           ``theta_d = theta (1 + k1 theta^2 + k2 theta^4 + k3 theta^6 + k4 theta^8)``,
                           ``(x_d, y_d) = theta_d / r * (x_n, y_n)``.

* Pixel coordinates ``u = fx x_d + s y_d + cx``, ``v = fy y_d + cy`` with

  ``K = [[fx, s, cx], [0, fy, cy], [0, 0, 1]]``.

* A projection is kept when ``z_c > min_depth`` (frustum culling), when the
  normalized radius lies inside the monotonic (invertible) domain of the
  distortion polynomial, and when ``0 <= u < W`` and ``0 <= v < H``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import numpy as np

PINHOLE = "pinhole"
BROWN_CONRADY = "brown_conrady"
KANNALA_BRANDT = "kannala_brandt"
MODELS = (PINHOLE, BROWN_CONRADY, KANNALA_BRANDT)
NUM_COEFFS = {PINHOLE: 5, BROWN_CONRADY: 5, KANNALA_BRANDT: 4}

_EPS = 1e-12
_MAX_RADIUS_SCAN = 50.0  # normalized radius beyond which no image point is ever considered


# ----------------------------------------------------------------------------
# Intrinsics container
# ----------------------------------------------------------------------------
@dataclass
class Intrinsics:
    model: str
    K: np.ndarray
    coeffs: np.ndarray
    width: int
    height: int
    fov_class: str = "normal"
    hfov_deg: float = float("nan")
    vfov_deg: float = float("nan")
    distortion_level: str = "none"
    # Brown-Conrady: largest undistorted normalized radius with a unique image.
    # Kannala-Brandt: largest incidence angle (rad) with a unique image.
    valid_radius: float = float("inf")
    corner_radius: float = float("nan")

    @property
    def fx(self) -> float:
        return float(self.K[0, 0])

    @property
    def fy(self) -> float:
        return float(self.K[1, 1])

    @property
    def cx(self) -> float:
        return float(self.K[0, 2])

    @property
    def cy(self) -> float:
        return float(self.K[1, 2])

    @property
    def skew(self) -> float:
        return float(self.K[0, 1])

    def as_attrs(self) -> Dict[str, Any]:
        return {
            "distortion_model": self.model,
            "image_width": int(self.width),
            "image_height": int(self.height),
            "fov_class": self.fov_class,
            "hfov_deg": float(self.hfov_deg),
            "vfov_deg": float(self.vfov_deg),
            "distortion_level": self.distortion_level,
            "valid_radius": float(self.valid_radius),
            "corner_radius": float(self.corner_radius),
        }

    @classmethod
    def from_arrays(cls, K: np.ndarray, coeffs: np.ndarray, attrs: Dict[str, Any]) -> "Intrinsics":
        model = str(attrs["distortion_model"])
        return cls(
            model=model,
            K=np.asarray(K, dtype=np.float64),
            coeffs=np.asarray(coeffs, dtype=np.float64),
            width=int(attrs["image_width"]),
            height=int(attrs["image_height"]),
            fov_class=str(attrs.get("fov_class", "normal")),
            hfov_deg=float(attrs.get("hfov_deg", float("nan"))),
            vfov_deg=float(attrs.get("vfov_deg", float("nan"))),
            distortion_level=str(attrs.get("distortion_level", "none")),
            valid_radius=float(attrs.get("valid_radius", valid_radius_for(model, coeffs))),
            corner_radius=float(attrs.get("corner_radius", float("nan"))),
        )


# ----------------------------------------------------------------------------
# Forward distortion
# ----------------------------------------------------------------------------
def _brown_radial(r2: np.ndarray, k1: float, k2: float, k3: float) -> np.ndarray:
    return 1.0 + k1 * r2 + k2 * r2 * r2 + k3 * r2 * r2 * r2


def _kb_theta_d(theta: np.ndarray, coeffs: np.ndarray) -> np.ndarray:
    k1, k2, k3, k4 = (float(c) for c in coeffs[:4])
    t2 = theta * theta
    return theta * (1.0 + t2 * (k1 + t2 * (k2 + t2 * (k3 + t2 * k4))))


def distort_points(xn: np.ndarray, yn: np.ndarray, model: str, coeffs: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Apply lens distortion to normalized image coordinates."""
    xn = np.asarray(xn, dtype=np.float64)
    yn = np.asarray(yn, dtype=np.float64)
    if model == PINHOLE:
        return xn.copy(), yn.copy()
    if model == BROWN_CONRADY:
        k1, k2, p1, p2, k3 = (float(c) for c in coeffs[:5])
        r2 = xn * xn + yn * yn
        radial = _brown_radial(r2, k1, k2, k3)
        xd = xn * radial + 2.0 * p1 * xn * yn + p2 * (r2 + 2.0 * xn * xn)
        yd = yn * radial + p1 * (r2 + 2.0 * yn * yn) + 2.0 * p2 * xn * yn
        return xd, yd
    if model == KANNALA_BRANDT:
        r = np.hypot(xn, yn)
        theta = np.arctan(r)
        theta_d = _kb_theta_d(theta, coeffs)
        scale = np.ones_like(r)
        np.divide(theta_d, r, out=scale, where=r > _EPS)
        return xn * scale, yn * scale
    raise ValueError(f"unknown camera model '{model}'")


# ----------------------------------------------------------------------------
# Validity domain of the distortion polynomials
# ----------------------------------------------------------------------------
def _smallest_positive_root(poly_desc: np.ndarray) -> float:
    """Smallest positive real root of a polynomial given in descending powers."""
    poly_desc = np.trim_zeros(np.asarray(poly_desc, dtype=np.float64), "f")
    if poly_desc.size <= 1:
        return float("inf")
    roots = np.roots(poly_desc)
    real = roots[np.abs(roots.imag) < 1e-9].real
    real = real[real > 0]
    return float(real.min()) if real.size else float("inf")


def brown_valid_radius(coeffs: np.ndarray) -> float:
    """
    Largest undistorted normalized radius ``r`` up to which the radial function
    ``r_d(r) = r (1 + k1 r^2 + k2 r^4 + k3 r^6)`` is strictly increasing, i.e. the
    first positive root of ``1 + 3 k1 r^2 + 5 k2 r^4 + 7 k3 r^6``.
    """
    k1, k2, k3 = float(coeffs[0]), float(coeffs[1]), float(coeffs[4])
    s = _smallest_positive_root([7.0 * k3, 5.0 * k2, 3.0 * k1, 1.0])  # polynomial in s = r^2
    return math.sqrt(s) if math.isfinite(s) else float("inf")


def kb_valid_theta(coeffs: np.ndarray) -> float:
    """
    Largest incidence angle (rad, at most pi/2) up to which
    ``theta_d(theta)`` is strictly increasing.
    """
    k1, k2, k3, k4 = (float(c) for c in coeffs[:4])
    s = _smallest_positive_root([9.0 * k4, 7.0 * k3, 5.0 * k2, 3.0 * k1, 1.0])  # in s = theta^2
    theta = math.sqrt(s) if math.isfinite(s) else float("inf")
    return min(theta, math.pi / 2.0)


def valid_radius_for(model: str, coeffs: np.ndarray) -> float:
    if model == BROWN_CONRADY:
        return brown_valid_radius(coeffs)
    if model == KANNALA_BRANDT:
        return kb_valid_theta(coeffs)
    return float("inf")


def in_valid_domain(xn: np.ndarray, yn: np.ndarray, intr: Intrinsics) -> np.ndarray:
    """Boolean mask of normalized points inside the invertible distortion domain."""
    if intr.model == PINHOLE or not np.isfinite(intr.valid_radius):
        return np.ones(np.shape(xn), dtype=bool)
    r = np.hypot(xn, yn)
    if intr.model == BROWN_CONRADY:
        return r <= intr.valid_radius
    return np.arctan(r) <= intr.valid_radius


# ----------------------------------------------------------------------------
# Inverse distortion
# ----------------------------------------------------------------------------
def _bisect_monotonic(target: np.ndarray, forward, upper: float, iters: int = 80) -> np.ndarray:
    """Solve forward(x) = target for x in [0, upper] where forward is increasing."""
    lo = np.zeros_like(target)
    hi = np.full_like(target, upper)
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        f = forward(mid)
        below = f < target
        lo = np.where(below, mid, lo)
        hi = np.where(below, hi, mid)
    return 0.5 * (lo + hi)


def _undistort_brown(xd, yd, coeffs, valid_radius, newton_iters=25):
    k1, k2, p1, p2, k3 = (float(c) for c in coeffs[:5])
    rd = np.hypot(xd, yd)
    upper = min(valid_radius, _MAX_RADIUS_SCAN)
    forward = lambda r: r * _brown_radial(r * r, k1, k2, k3)  # noqa: E731
    r0 = _bisect_monotonic(rd, forward, upper)
    scale = np.ones_like(rd)
    np.divide(r0, rd, out=scale, where=rd > _EPS)
    x = xd * scale
    y = yd * scale
    active = np.ones_like(rd, dtype=bool)
    for _ in range(newton_iters):
        r2 = x * x + y * y
        g = _brown_radial(r2, k1, k2, k3)
        gp = k1 + 2.0 * k2 * r2 + 3.0 * k3 * r2 * r2
        fx = x * g + 2.0 * p1 * x * y + p2 * (r2 + 2.0 * x * x)
        fy = y * g + p1 * (r2 + 2.0 * y * y) + 2.0 * p2 * x * y
        ex = xd - fx
        ey = yd - fy
        a = g + 2.0 * gp * x * x + 2.0 * p1 * y + 6.0 * p2 * x
        b = 2.0 * gp * x * y + 2.0 * p1 * x + 2.0 * p2 * y
        c = b
        d = g + 2.0 * gp * y * y + 6.0 * p1 * y + 2.0 * p2 * x
        det = a * d - b * c
        safe = np.abs(det) > 1e-14
        det_safe = np.where(safe, det, 1.0)
        dx = np.where(safe & active, (d * ex - b * ey) / det_safe, 0.0)
        dy = np.where(safe & active, (-c * ex + a * ey) / det_safe, 0.0)
        x = x + dx
        y = y + dy
        active = active & (np.hypot(dx, dy) > 1e-15)
        if not active.any():
            break
    xn, yn = distort_points(x, y, BROWN_CONRADY, coeffs)
    residual = np.hypot(xn - xd, yn - yd)
    ok = (residual < 1e-9) & (np.hypot(x, y) <= upper * (1.0 + 1e-9))
    return x, y, ok


def _undistort_kb(xd, yd, coeffs, valid_theta):
    thd = np.hypot(xd, yd)
    upper = min(valid_theta, math.pi / 2.0 - 1e-9)
    forward = lambda th: _kb_theta_d(th, coeffs)  # noqa: E731
    theta = _bisect_monotonic(thd, forward, upper)
    r = np.tan(theta)
    scale = np.ones_like(thd)
    np.divide(r, thd, out=scale, where=thd > _EPS)
    residual = np.abs(forward(theta) - thd)
    ok = residual < 1e-9
    return xd * scale, yd * scale, ok


def undistort_points(xd: np.ndarray, yd: np.ndarray, model: str, coeffs: np.ndarray,
                     valid_radius: float = float("inf")) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Invert the lens distortion.  Returns ``(x_n, y_n, ok)`` where ``ok`` marks
    points that lie inside the invertible domain and converged to 1e-9.
    Points with ``ok == False`` (e.g. random outliers outside the image circle of a
    strongly distorted lens) are returned clamped to the domain boundary.
    """
    xd = np.asarray(xd, dtype=np.float64)
    yd = np.asarray(yd, dtype=np.float64)
    if model == PINHOLE:
        return xd.copy(), yd.copy(), np.ones(xd.shape, dtype=bool)
    if model == BROWN_CONRADY:
        return _undistort_brown(xd, yd, coeffs, valid_radius)
    if model == KANNALA_BRANDT:
        return _undistort_kb(xd, yd, coeffs, valid_radius)
    raise ValueError(f"unknown camera model '{model}'")


# ----------------------------------------------------------------------------
# Intrinsic matrix helpers
# ----------------------------------------------------------------------------
def pixel_from_normalized(xd: np.ndarray, yd: np.ndarray, K: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    u = K[0, 0] * xd + K[0, 1] * yd + K[0, 2]
    v = K[1, 1] * yd + K[1, 2]
    return u, v


def normalized_from_pixel(u: np.ndarray, v: np.ndarray, K: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    yd = (np.asarray(v, dtype=np.float64) - K[1, 2]) / K[1, 1]
    xd = (np.asarray(u, dtype=np.float64) - K[0, 2] - K[0, 1] * yd) / K[0, 0]
    return xd, yd


def corner_radius(K: np.ndarray, width: int, height: int) -> float:
    """Largest normalized radius reached by the four image corners (pinhole)."""
    corners_u = np.array([0.0, width, 0.0, width])
    corners_v = np.array([0.0, 0.0, height, height])
    xd, yd = normalized_from_pixel(corners_u, corners_v, K)
    return float(np.hypot(xd, yd).max())


def undistort_to_pinhole_pixels(uv: np.ndarray, intr: Intrinsics) -> Tuple[np.ndarray, np.ndarray]:
    """
    Map (possibly distorted) pixel observations to the pixel coordinates of the
    equivalent undistorted pinhole camera with the same ``K``.  Returns
    ``(uv_undistorted, ok)``.
    """
    xd, yd = normalized_from_pixel(uv[:, 0], uv[:, 1], intr.K)
    xn, yn, ok = undistort_points(xd, yd, intr.model, intr.coeffs, intr.valid_radius)
    u, v = pixel_from_normalized(xn, yn, intr.K)
    return np.column_stack([u, v]), ok


# ----------------------------------------------------------------------------
# Projection
# ----------------------------------------------------------------------------
@dataclass
class Projection:
    uv: np.ndarray        # (M, 2) exact pixel coordinates of the visible points
    indices: np.ndarray   # (M,) indices into the scene's 3D point array
    depth: np.ndarray     # (M,) camera-frame depth z_c of the visible points


def transform_to_camera(points_3d: np.ndarray, R: np.ndarray, t: np.ndarray) -> np.ndarray:
    return np.asarray(points_3d, dtype=np.float64) @ np.asarray(R, dtype=np.float64).T + np.asarray(t, dtype=np.float64).reshape(1, 3)


def project_points(points_3d: np.ndarray, intr: Intrinsics, R: np.ndarray, t: np.ndarray,
                   min_depth: float = 0.0) -> Projection:
    """Forward projection with frustum culling, domain check and bounds check."""
    pc = transform_to_camera(points_3d, R, t)
    z = pc[:, 2]
    in_front = z > min_depth
    zs = np.where(in_front, z, 1.0)
    xn = np.where(in_front, pc[:, 0] / zs, 0.0)
    yn = np.where(in_front, pc[:, 1] / zs, 0.0)
    ok = in_front & in_valid_domain(xn, yn, intr)
    xd, yd = distort_points(xn, yn, intr.model, intr.coeffs)
    u, v = pixel_from_normalized(xd, yd, intr.K)
    ok &= (u >= 0.0) & (u < intr.width) & (v >= 0.0) & (v < intr.height)
    idx = np.flatnonzero(ok)
    return Projection(np.column_stack([u[idx], v[idx]]), idx.astype(np.int32), z[idx].copy())


def project_points_all(points_3d: np.ndarray, intr: Intrinsics, R: np.ndarray, t: np.ndarray
                       ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Project every point without culling.  Points behind the camera or outside the
    distortion domain receive NaN coordinates.  Returns ``(uv, depth)``.
    """
    pc = transform_to_camera(points_3d, R, t)
    z = pc[:, 2]
    in_front = z > 0.0
    zs = np.where(in_front, z, 1.0)
    xn = np.where(in_front, pc[:, 0] / zs, 0.0)
    yn = np.where(in_front, pc[:, 1] / zs, 0.0)
    ok = in_front & in_valid_domain(xn, yn, intr)
    xd, yd = distort_points(xn, yn, intr.model, intr.coeffs)
    u, v = pixel_from_normalized(xd, yd, intr.K)
    uv = np.column_stack([u, v])
    uv[~ok] = np.nan
    return uv, z


def project_pinhole(points_3d: np.ndarray, K: np.ndarray, R: np.ndarray, t: np.ndarray
                    ) -> Tuple[np.ndarray, np.ndarray]:
    """Distortion-free projection used by the solvers.  Returns ``(uv, depth)``."""
    pc = transform_to_camera(points_3d, R, t)
    z = pc[:, 2]
    zs = np.where(np.abs(z) > _EPS, z, _EPS)
    xn = pc[:, 0] / zs
    yn = pc[:, 1] / zs
    u, v = pixel_from_normalized(xn, yn, K)
    return np.column_stack([u, v]), z


# ----------------------------------------------------------------------------
# Intrinsics sampling
# ----------------------------------------------------------------------------
def _choice(rng: np.random.Generator, probs: Dict[str, float]) -> str:
    keys = list(probs.keys())
    p = np.asarray([float(probs[k]) for k in keys], dtype=np.float64)
    p = p / p.sum()
    return str(keys[int(rng.choice(len(keys), p=p))])


def _sample_brown_coeffs(rng, ranges, r_c, min_valid, max_tries=200):
    """Sample (k1, k2, p1, p2, k3) whose invertible domain covers the image."""
    scale = 1.0
    for attempt in range(max_tries):
        kappa1 = rng.uniform(-ranges["k1"], ranges["k1"]) * scale
        kappa2 = rng.uniform(-ranges["k2"], ranges["k2"]) * scale
        kappa3 = rng.uniform(-ranges["k3"], ranges["k3"]) * scale
        pi1 = rng.uniform(-ranges["p"], ranges["p"]) * scale
        pi2 = rng.uniform(-ranges["p"], ranges["p"]) * scale
        coeffs = np.array(
            [kappa1 / r_c ** 2, kappa2 / r_c ** 4, pi1 / r_c, pi2 / r_c, kappa3 / r_c ** 6], dtype=np.float64
        )
        valid = brown_valid_radius(coeffs)
        if valid >= min_valid:
            return coeffs, valid
        if attempt % 50 == 49:
            scale *= 0.5
    coeffs = np.zeros(5)
    return coeffs, float("inf")


def _sample_kb_coeffs(rng, ranges, theta_c, min_valid, max_tries=200):
    scale = 1.0
    for attempt in range(max_tries):
        kappas = [rng.uniform(-ranges[k], ranges[k]) * scale for k in ("k1", "k2", "k3", "k4")]
        coeffs = np.array([kappas[i] / theta_c ** (2 * (i + 1)) for i in range(4)], dtype=np.float64)
        valid = kb_valid_theta(coeffs)
        if valid >= min_valid:
            return coeffs, valid
        if attempt % 50 == 49:
            scale *= 0.5
    return np.zeros(4), math.pi / 2.0


def sample_intrinsics(rng: np.random.Generator, cam_cfg: Dict[str, Any]) -> Intrinsics:
    """Sample one intrinsic parameter set (model, K, distortion) from the config."""
    model = _choice(rng, cam_cfg["model_probs"])
    fov_class = _choice(rng, cam_cfg["fov_class_probs"][model])
    lo, hi = cam_cfg["fov_classes"][fov_class]["hfov_deg"]
    hfov = float(rng.uniform(lo, hi))
    width, height = (int(v) for v in cam_cfg["resolutions"][int(rng.integers(len(cam_cfg["resolutions"])))])
    half = math.radians(hfov) / 2.0
    if model == KANNALA_BRANDT:
        fx = (width / 2.0) / half  # equidistant model: r_d = theta
    else:
        fx = (width / 2.0) / math.tan(half)
    aspect = float(np.clip(1.0 + rng.normal(0.0, cam_cfg["aspect_jitter"]), 0.9, 1.1))
    fy = fx * aspect
    jit = cam_cfg["principal_point_jitter"]
    cx = width / 2.0 + rng.uniform(-jit, jit) * width
    cy = height / 2.0 + rng.uniform(-jit, jit) * height
    skew_cfg = cam_cfg["skew"]
    skew = float(rng.uniform(-skew_cfg["max_pixels"], skew_cfg["max_pixels"])) if rng.uniform() < skew_cfg["probability"] else 0.0
    K = np.array([[fx, skew, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
    if model == KANNALA_BRANDT:
        vfov = math.degrees(2.0 * (height / 2.0) / fy)
    else:
        vfov = math.degrees(2.0 * math.atan((height / 2.0) / fy))
    r_c = corner_radius(K, width, height)
    min_valid = cam_cfg["min_valid_corner_fraction"] * r_c

    if model == PINHOLE:
        coeffs, valid, level = np.zeros(5), float("inf"), "none"
    else:
        level = _choice(rng, cam_cfg["distortion_levels"]["probs"])
        if fov_class == "narrow":
            level = "mild"  # telephoto lenses never exhibit strong distortion
        ranges = cam_cfg["distortion_levels"][model][level]
        if model == BROWN_CONRADY:
            coeffs, valid = _sample_brown_coeffs(rng, ranges, r_c, min_valid)
        else:
            coeffs, valid = _sample_kb_coeffs(rng, ranges, r_c, min(min_valid, math.pi / 2.0))
    return Intrinsics(
        model=model, K=K, coeffs=coeffs, width=width, height=height, fov_class=fov_class,
        hfov_deg=hfov, vfov_deg=vfov, distortion_level=level, valid_radius=valid, corner_radius=r_c,
    )
