"""
3D scene synthesis.

Five structured scene families are generated in a canonical *scene frame* and
then (optionally) moved by a random rigid transform so the world frame carries no
special structure:

* ``planar_single``    - all points on one plane (calibration target / wall).
                         Exactly planar: the classic DLT degeneracy.
* ``planar_multi``     - 2 to 4 axis-aligned faces of a room, always the back
                         wall plus a random selection of floor, ceiling and side
                         walls (adjacent faces meet at right angles; opposite
                         faces, such as floor and ceiling, are parallel).
* ``volumetric``       - points uniformly distributed inside a box.
* ``mixed``            - half of the points on a back wall, half inside the box in
                         front of it (the layout of the reference implementation).
* ``depth_stratified`` - points filling two nested cones along a corridor, with
                         depths log-uniform between 0.5 m and 50 m (configurable).

Planar structures use either a regular grid or uniformly random in-plane points.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
from scipy.spatial.transform import Rotation

from .config import SCENE_TYPES


@dataclass
class Scene:
    scene_type: str
    points: np.ndarray         # (N, 3) world coordinates, float64
    labels: np.ndarray         # (N,) int16: plane index of the point, -1 for volumetric points
    center: np.ndarray         # (3,) world coordinates of the structure center
    radius: float              # bounding radius around the center (meters)
    front_axis: np.ndarray     # (3,) unit vector (world) - axis of the camera hemisphere
    pose_strategy: str         # "hemisphere" | "corridor"
    frame_R: np.ndarray        # (3, 3) rotation scene-frame -> world
    frame_t: np.ndarray        # (3,) translation scene-frame -> world
    params: Dict[str, Any]

    @property
    def num_points(self) -> int:
        return int(self.points.shape[0])

    def as_attrs(self) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {
            "scene_type": self.scene_type,
            "num_points": self.num_points,
            "center": self.center.astype(np.float64),
            "radius": float(self.radius),
            "front_axis": self.front_axis.astype(np.float64),
            "pose_strategy": self.pose_strategy,
            "frame_R": self.frame_R.astype(np.float64),
            "frame_t": self.frame_t.astype(np.float64),
        }
        for key, value in self.params.items():
            attrs[key] = value
        return attrs


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _grid_points(rng: np.random.Generator, n: int, size_x: float, size_y: float, jitter: float) -> np.ndarray:
    """Regular grid of about ``n`` points on a size_x by size_y rectangle."""
    cols = max(2, int(round(math.sqrt(n * size_x / size_y))))
    rows = max(2, int(round(n / cols)))
    xs = np.linspace(-size_x / 2.0, size_x / 2.0, cols)
    ys = np.linspace(-size_y / 2.0, size_y / 2.0, rows)
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    if jitter > 0:
        spacing = min(xs[1] - xs[0], ys[1] - ys[0])
        pts = pts + rng.uniform(-jitter * spacing, jitter * spacing, pts.shape)
    return pts


def _random_plane_points(rng: np.random.Generator, n: int, size_x: float, size_y: float) -> np.ndarray:
    return rng.uniform([-size_x / 2.0, -size_y / 2.0], [size_x / 2.0, size_y / 2.0], (n, 2))


def _plane_points(rng, n, size_a, size_b, layout, jitter, origin, axis_a, axis_b) -> np.ndarray:
    """Points on the plane ``origin + a * axis_a + b * axis_b``."""
    if layout == "grid":
        ab = _grid_points(rng, n, size_a, size_b, jitter)
    else:
        ab = _random_plane_points(rng, n, size_a, size_b)
    return origin[None, :] + ab[:, :1] * axis_a[None, :] + ab[:, 1:2] * axis_b[None, :]


def _choice(rng: np.random.Generator, probs: Dict[str, float]) -> str:
    """Draw one key of ``probs``; keys are sorted so the draw depends on the
    content of the mapping rather than on the order a YAML file lists it in."""
    keys = sorted(probs.keys())
    p = np.asarray([float(probs[k]) for k in keys])
    return str(keys[int(rng.choice(len(keys), p=p / p.sum()))])


_EX = np.array([1.0, 0.0, 0.0])
_EY = np.array([0.0, 1.0, 0.0])
_EZ = np.array([0.0, 0.0, 1.0])


def _box_half_sizes(rng: np.random.Generator, scene_size: float) -> np.ndarray:
    return 0.5 * scene_size * np.array([1.0, rng.uniform(0.5, 1.0), rng.uniform(0.5, 1.0)])


def _room_planes(h: np.ndarray) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, float, float]]:
    """Room faces as (origin, axis_a, axis_b, size_a, size_b) in the scene frame."""
    hx, hy, hz = (float(v) for v in h)
    return {
        "back": (np.array([0.0, 0.0, hz]), _EX, _EY, 2 * hx, 2 * hy),
        "floor": (np.array([0.0, -hy, 0.0]), _EX, _EZ, 2 * hx, 2 * hz),
        "ceiling": (np.array([0.0, hy, 0.0]), _EX, _EZ, 2 * hx, 2 * hz),
        "left": (np.array([-hx, 0.0, 0.0]), _EZ, _EY, 2 * hz, 2 * hy),
        "right": (np.array([hx, 0.0, 0.0]), _EZ, _EY, 2 * hz, 2 * hy),
    }


# ----------------------------------------------------------------------------
# Generators (scene frame)
# ----------------------------------------------------------------------------
def _gen_planar_single(rng, n, size, sc_cfg):
    layout = _choice(rng, sc_cfg["planar_layout_probs"])
    size_y = size * rng.uniform(0.5, 1.0)
    pts = _plane_points(rng, n, size, size_y, layout, sc_cfg["grid_jitter"], np.zeros(3), _EX, _EY)
    labels = np.zeros(len(pts), dtype=np.int16)
    params = {"layout": layout, "num_planes": 1, "plane_names": "target", "extent_x": size, "extent_y": size_y}
    return pts, labels, np.zeros(3), 0.5 * math.hypot(size, size_y), -_EZ, params


def _gen_planar_multi(rng, n, size, sc_cfg):
    layout = _choice(rng, sc_cfg["planar_layout_probs"])
    h = _box_half_sizes(rng, size)
    planes = _room_planes(h)
    num_planes = int(rng.integers(2, 5))  # 2, 3 or 4 planes
    others = ["floor", "left", "right", "ceiling"]
    chosen = ["back"] + [others[i] for i in sorted(rng.choice(len(others), num_planes - 1, replace=False))]
    per_plane = [n // num_planes + (1 if i < n % num_planes else 0) for i in range(num_planes)]
    pts_list, labels_list = [], []
    for idx, (name, count) in enumerate(zip(chosen, per_plane)):
        origin, axis_a, axis_b, size_a, size_b = planes[name]
        pts_list.append(_plane_points(rng, count, size_a, size_b, layout, sc_cfg["grid_jitter"], origin, axis_a, axis_b))
        labels_list.append(np.full(len(pts_list[-1]), idx, dtype=np.int16))
    pts = np.vstack(pts_list)
    labels = np.concatenate(labels_list)
    params = {"layout": layout, "num_planes": num_planes, "plane_names": ",".join(chosen), "box_half_sizes": h}
    return pts, labels, np.zeros(3), float(np.linalg.norm(h)), -_EZ, params


def _gen_volumetric(rng, n, size, sc_cfg):
    h = _box_half_sizes(rng, size)
    pts = rng.uniform(-h, h, (n, 3))
    labels = np.full(n, -1, dtype=np.int16)
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    params = {"layout": "random", "num_planes": 0, "plane_names": "", "box_half_sizes": h}
    return pts, labels, np.zeros(3), float(np.linalg.norm(h)), axis, params


def _gen_mixed(rng, n, size, sc_cfg):
    layout = _choice(rng, sc_cfg["planar_layout_probs"])
    h = _box_half_sizes(rng, size)
    origin, axis_a, axis_b, size_a, size_b = _room_planes(h)["back"]
    n_wall = n // 2
    wall = _plane_points(rng, n_wall, size_a, size_b, layout, sc_cfg["grid_jitter"], origin, axis_a, axis_b)
    volume = rng.uniform(-h, h, (n - n_wall, 3))
    pts = np.vstack([wall, volume])
    labels = np.concatenate([np.zeros(len(wall), dtype=np.int16), np.full(len(volume), -1, dtype=np.int16)])
    params = {"layout": layout, "num_planes": 1, "plane_names": "back", "box_half_sizes": h}
    return pts, labels, np.zeros(3), float(np.linalg.norm(h)), -_EZ, params


def _gen_depth_stratified(rng, n, size, sc_cfg):
    ds = sc_cfg["depth_stratified"]
    z_min, z_max = (float(v) for v in ds["depth_range"])
    a_narrow, a_wide = (math.radians(float(v)) for v in ds["cone_half_angles_deg"])
    depth = np.exp(rng.uniform(math.log(z_min), math.log(z_max), n))
    narrow = rng.uniform(size=n) < float(ds["narrow_fraction"])
    alpha = np.where(narrow, a_narrow, a_wide)
    cos_phi = rng.uniform(np.cos(alpha), 1.0)
    phi = np.arccos(np.clip(cos_phi, -1.0, 1.0))
    psi = rng.uniform(0.0, 2.0 * math.pi, n)
    lateral = depth * np.tan(phi)
    pts = np.column_stack([lateral * np.cos(psi), lateral * np.sin(psi), depth])
    labels = np.full(n, -1, dtype=np.int16)
    center = np.array([0.0, 0.0, 0.5 * (z_min + z_max)])
    radius = float(np.linalg.norm(pts - center, axis=1).max())
    params = {
        "layout": "random", "num_planes": 0, "plane_names": "",
        "depth_min": z_min, "depth_max": z_max,
        "cone_half_angles_deg": np.array(ds["cone_half_angles_deg"], dtype=np.float64),
    }
    return pts, labels, center, radius, -_EZ, params


_GENERATORS = {
    "planar_single": _gen_planar_single,
    "planar_multi": _gen_planar_multi,
    "volumetric": _gen_volumetric,
    "mixed": _gen_mixed,
    "depth_stratified": _gen_depth_stratified,
}


def generate_scene(rng: np.random.Generator, scene_type: str, cfg: Dict[str, Any]) -> Scene:
    """Generate one scene of the requested type (world coordinates)."""
    if scene_type not in SCENE_TYPES:
        raise ValueError(f"unknown scene type '{scene_type}'")
    sc_cfg = cfg["scenes"]
    lo, hi = sc_cfg["num_points"]
    n = int(rng.integers(int(lo), int(hi) + 1))
    size = float(rng.uniform(*sc_cfg["scene_size"]))
    pts, labels, center, radius, front, params = _GENERATORS[scene_type](rng, n, size, sc_cfg)
    params = dict(params)
    params["scene_size"] = size
    params["requested_num_points"] = n

    if sc_cfg.get("randomize_scene_frame", True):
        frame_R = Rotation.random(random_state=rng).as_matrix()
        frame_t = rng.uniform(-0.5, 0.5, 3) * size
    else:
        frame_R = np.eye(3)
        frame_t = np.zeros(3)
    pts_w = pts @ frame_R.T + frame_t
    center_w = frame_R @ center + frame_t
    front_w = frame_R @ front
    strategy = "corridor" if scene_type == "depth_stratified" else "hemisphere"
    return Scene(
        scene_type=scene_type,
        points=np.ascontiguousarray(pts_w, dtype=np.float64),
        labels=labels.astype(np.int16),
        center=center_w.astype(np.float64),
        radius=float(radius),
        front_axis=(front_w / np.linalg.norm(front_w)).astype(np.float64),
        pose_strategy=strategy,
        frame_R=frame_R.astype(np.float64),
        frame_t=frame_t.astype(np.float64),
        params=params,
    )


def is_planar(points: np.ndarray, rel_tol: float = 1e-8) -> bool:
    """True when the points lie (numerically) on a single plane."""
    pts = np.asarray(points, dtype=np.float64)
    if len(pts) < 4:
        return True
    centered = pts - pts.mean(axis=0)
    s = np.linalg.svd(centered, compute_uv=False)
    return bool(s[-1] <= rel_tol * max(s[0], 1e-300))


def scene_type_list() -> List[str]:
    return list(SCENE_TYPES)
