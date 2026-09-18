"""
Camera pose (extrinsics) sampling.

Look-at construction (Step 2 of the pipeline, README Section 5.3):

    Z = (T - C) / ||T - C||          forward (optical axis)
    X = up x Z,  normalised           right
    Y = Z x X                         true orthogonal up
    R = [X; Y; Z]  (rows)             world -> camera rotation
    t = -R C                          so that  X_c = R X_w + t

An optional roll about the optical axis is applied afterwards.  Camera centers
are sampled uniformly on a hemisphere (spherical cap above a minimum elevation)
centered on the structure, at a distance chosen so that the structure roughly
fills the image for the given field of view.  Depth-stratified scenes use the
"corridor" strategy: the camera sits at the corridor entrance looking down it.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Tuple

import numpy as np

from .cameras import Intrinsics
from .scenes import Scene


def look_at_rotation(camera_center: np.ndarray, target: np.ndarray, up: np.ndarray,
                     roll_deg: float = 0.0) -> np.ndarray:
    """World-to-camera rotation matrix R (rows X, Y, Z) for a camera at
    ``camera_center`` looking at ``target``."""
    C = np.asarray(camera_center, dtype=np.float64)
    T = np.asarray(target, dtype=np.float64)
    up = np.asarray(up, dtype=np.float64)
    z = T - C
    norm = np.linalg.norm(z)
    if norm < 1e-12:
        raise ValueError("camera center and target coincide")
    z = z / norm
    x = np.cross(up, z)
    if np.linalg.norm(x) < 1e-6:
        # Viewing direction parallel to the up vector: pick any perpendicular axis.
        alt = np.array([1.0, 0.0, 0.0]) if abs(z[0]) < 0.9 else np.array([0.0, 0.0, 1.0])
        x = np.cross(alt, z)
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.vstack([x, y, z])
    if roll_deg != 0.0:
        c, s = math.cos(math.radians(roll_deg)), math.sin(math.radians(roll_deg))
        R_roll = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        R = R_roll @ R
    return R


def pose_matrix(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    """4x4 homogeneous world-to-camera transform ``[[R, t], [0, 1]]``."""
    Rt = np.eye(4)
    Rt[:3, :3] = R
    Rt[:3, 3] = np.asarray(t).ravel()
    return Rt


def _uniform_cap_direction(rng: np.random.Generator, axis: np.ndarray, min_elevation_deg: float) -> np.ndarray:
    """Uniform (area-wise) random unit vector on the hemisphere around ``axis``
    whose elevation above the base plane is at least ``min_elevation_deg``."""
    min_sin = math.sin(math.radians(min_elevation_deg))
    for _ in range(10000):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        proj = float(d @ axis)
        if proj < 0.0:
            d = d - 2.0 * proj * axis  # reflect onto the hemisphere (keeps uniformity)
            proj = -proj
        if proj >= min_sin:
            return d
    return axis.copy()


def sample_camera_pose(rng: np.random.Generator, scene: Scene, intr: Intrinsics,
                       pose_cfg: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Sample an extrinsic pose for ``scene`` seen through ``intr``.
    Returns ``(R, t, camera_center, info)``.
    """
    up = np.asarray(pose_cfg["up_vector"], dtype=np.float64)
    roll = float(rng.uniform(-pose_cfg["roll_jitter_deg"], pose_cfg["roll_jitter_deg"]))
    if scene.pose_strategy == "corridor":
        cc = pose_cfg["corridor"]
        jit = float(cc["center_xy_jitter"])
        C_s = np.array([rng.uniform(-jit, jit), rng.uniform(-jit, jit), rng.uniform(*cc["center_z_range"])])
        depth = float(rng.uniform(*cc["target_depth_range"]))
        ang = math.radians(float(cc["target_angle_jitter_deg"]))
        T_s = np.array([depth * math.tan(rng.uniform(-ang, ang)), depth * math.tan(rng.uniform(-ang, ang)), depth])
        C = scene.frame_R @ C_s + scene.frame_t
        T = scene.frame_R @ T_s + scene.frame_t
        info = {"strategy": "corridor", "distance": float(np.linalg.norm(T - C)), "elevation_deg": float("nan")}
    else:
        direction = _uniform_cap_direction(rng, scene.front_axis, float(pose_cfg["min_elevation_deg"]))
        half_fov = 0.5 * math.radians(min(intr.hfov_deg, intr.vfov_deg))
        half_fov = min(half_fov, math.radians(float(pose_cfg["max_half_fov_for_distance_deg"])))
        fill = float(rng.uniform(*pose_cfg["fill_factor"]))
        distance = fill * scene.radius / math.tan(half_fov)
        distance = max(distance, float(pose_cfg["min_distance_factor"]) * scene.radius)
        C = scene.center + distance * direction
        jitter = float(pose_cfg["target_jitter"]) * scene.radius
        T = scene.center + rng.uniform(-jitter, jitter, 3)
        info = {
            "strategy": "hemisphere",
            "distance": float(distance),
            "elevation_deg": float(math.degrees(math.asin(np.clip(direction @ scene.front_axis, -1.0, 1.0)))),
        }
    R = look_at_rotation(C, T, up, roll)
    t = -R @ C
    info["roll_deg"] = roll
    info["target"] = T.astype(np.float64)
    return R, t, C.astype(np.float64), info
