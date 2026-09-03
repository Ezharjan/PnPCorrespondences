"""
Configuration handling.

A configuration is a plain nested dictionary.  ``DEFAULTS`` documents every key;
YAML files under ``configs/`` only override what they need to.  ``load_config``
deep-merges a YAML file onto the defaults and validates the result.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

SCENE_TYPES = ("planar_single", "planar_multi", "volumetric", "mixed", "depth_stratified")
CAMERA_MODELS = ("pinhole", "brown_conrady", "kannala_brandt")
FOV_CLASSES = ("narrow", "normal", "wide", "fisheye")
OUTLIER_TYPES = ("uniform", "swap", "mixed")
DISTORTION_LEVELS = ("mild", "strong")

# ----------------------------------------------------------------------------
# Default configuration (documented).  Sizes correspond to a quick "small" run.
# ----------------------------------------------------------------------------
DEFAULTS: Dict[str, Any] = {
    "dataset": {
        "name": "PnPCorrespondences",
        "version": "1.0.0",
        "master_seed": 20260902,
        "units": "meters",
        # Fraction of scenes (per scene type) assigned to each split.
        "splits": {"train": 0.8, "val": 0.1, "test": 0.1},
        # Scenes per HDF5 file (files are sharded per scene type).
        "max_scenes_per_file": 50,
        # HDF5 compression for the larger arrays: "gzip" or "none".
        "compression": "gzip",
        "compression_level": 1,
    },
    "scenes": {
        # Number of scenes generated for every scene type.
        "counts": {
            "planar_single": 6,
            "planar_multi": 6,
            "volumetric": 6,
            "mixed": 6,
            "depth_stratified": 6,
        },
        # Number of 3D points per scene, sampled uniformly (integers) in [lo, hi].
        "num_points": [800, 2500],
        # Edge length of the scene's bounding box in meters, sampled in [lo, hi].
        "scene_size": [4.0, 20.0],
        # Planar structures are laid out either as a regular grid (calibration
        # target) or as uniformly random points on the plane.
        "planar_layout_probs": {"grid": 0.5, "random": 0.5},
        # Jitter of grid points, as a fraction of the grid spacing (0 = exact grid).
        "grid_jitter": 0.0,
        # Apply a random rigid transform to every scene so that the world frame is
        # not aligned with the scene structure.
        "randomize_scene_frame": True,
        "depth_stratified": {
            # Depth range (meters) covered by the points, sampled log-uniformly.
            "depth_range": [0.5, 50.0],
            # The points fill two nested cones around the viewing axis.
            "cone_half_angles_deg": [12.0, 45.0],
            # Fraction of points in the narrow cone.
            "narrow_fraction": 0.5,
        },
    },
    "cameras": {
        # Number of distinct intrinsic parameter sets per scene and number of
        # poses (views) generated for every intrinsic set.
        "num_intrinsics_per_scene": 3,
        "num_poses_per_intrinsics": 4,
        # Sensor resolutions (width, height) in pixels, chosen uniformly.
        "resolutions": [[640, 480], [1280, 720], [1920, 1080], [2048, 1536], [3840, 2160]],
        # Probability of each camera / distortion model.
        "model_probs": {"pinhole": 0.30, "brown_conrady": 0.45, "kannala_brandt": 0.25},
        # Nominal horizontal field-of-view ranges (degrees) per FOV class.
        "fov_classes": {
            "narrow": {"hfov_deg": [5.0, 20.0]},
            "normal": {"hfov_deg": [40.0, 75.0]},
            "wide": {"hfov_deg": [80.0, 120.0]},
            "fisheye": {"hfov_deg": [130.0, 175.0]},
        },
        # Which FOV classes each camera model can take, with probabilities.
        "fov_class_probs": {
            "pinhole": {"narrow": 0.25, "normal": 0.50, "wide": 0.25},
            "brown_conrady": {"narrow": 0.25, "normal": 0.50, "wide": 0.25},
            "kannala_brandt": {"wide": 0.40, "fisheye": 0.60},
        },
        # fy = fx * (1 + N(0, aspect_jitter)), clipped to +-10 %.
        "aspect_jitter": 0.01,
        # Principal point offset from the image center, as a fraction of W and H.
        "principal_point_jitter": 0.03,
        # Skew term s of K: zero with probability (1 - probability), otherwise
        # uniform in [-max_pixels, max_pixels].
        "skew": {"probability": 0.10, "max_pixels": 2.0},
        # Distortion coefficients are sampled as *effective* coefficients, i.e. the
        # relative radial displacement they induce at the image corner, then
        # converted to the raw polynomial coefficients (see cameras.py).
        "distortion_levels": {
            "probs": {"mild": 0.5, "strong": 0.5},
            "brown_conrady": {
                "mild": {"k1": 0.08, "k2": 0.02, "k3": 0.005, "p": 0.002},
                "strong": {"k1": 0.35, "k2": 0.15, "k3": 0.05, "p": 0.010},
            },
            "kannala_brandt": {
                "mild": {"k1": 0.03, "k2": 0.010, "k3": 0.005, "k4": 0.002},
                "strong": {"k1": 0.15, "k2": 0.060, "k3": 0.020, "k4": 0.010},
            },
        },
        # The distortion polynomial must stay monotonic (invertible) up to this
        # fraction of the image-corner radius, otherwise coefficients are resampled.
        "min_valid_corner_fraction": 0.8,
        # Views with fewer visible points are rejected and the pose is resampled.
        "min_visible_points": 20,
        # Points with camera depth <= min_depth are culled (0 = keep everything
        # strictly in front of the camera, which is what the method specifies).
        "min_depth": 0.0,
        "max_pose_attempts": 30,
    },
    "poses": {
        # World "up" direction used by the look-at construction.
        "up_vector": [0.0, 1.0, 0.0],
        # Camera elevation above the hemisphere base plane is at least this angle.
        "min_elevation_deg": 10.0,
        # Camera distance = fill_factor * scene_radius / tan(min(hfov, vfov) / 2),
        # so that the scene roughly fills the image whatever the focal length.
        "fill_factor": [0.5, 1.8],
        # Half-FOV used in the distance formula is capped at this value.
        "max_half_fov_for_distance_deg": 60.0,
        # Lower bound on the distance, in units of the scene radius.
        "min_distance_factor": 0.35,
        # Look-at target = scene center + uniform jitter (fraction of the radius).
        "target_jitter": 0.15,
        # Random roll about the optical axis, uniform in [-x, x] degrees.
        "roll_jitter_deg": 15.0,
        # Corridor strategy (depth-stratified scenes): the camera sits near the
        # origin of the scene frame and looks down the +Z corridor.
        "corridor": {
            "center_xy_jitter": 0.30,
            "center_z_range": [-0.25, 0.0],
            "target_depth_range": [5.0, 30.0],
            "target_angle_jitter_deg": 10.0,
        },
    },
    "conditions": {
        # "list": use `items` verbatim.  "factorial": full factorial design of the
        # lists under `factorial`.
        "mode": "list",
        "items": [
            # --- noise sweep (no outliers, no quantization)
            {"noise_sigma": 0.0, "quantize": False, "outlier_ratio": 0.0, "outlier_type": "uniform"},
            {"noise_sigma": 0.1, "quantize": False, "outlier_ratio": 0.0, "outlier_type": "uniform"},
            {"noise_sigma": 0.5, "quantize": False, "outlier_ratio": 0.0, "outlier_type": "uniform"},
            {"noise_sigma": 1.0, "quantize": False, "outlier_ratio": 0.0, "outlier_type": "uniform"},
            {"noise_sigma": 2.0, "quantize": False, "outlier_ratio": 0.0, "outlier_type": "uniform"},
            # --- quantization (pixel grid, no sub-pixel refinement)
            {"noise_sigma": 0.0, "quantize": True, "outlier_ratio": 0.0, "outlier_type": "uniform"},
            {"noise_sigma": 0.5, "quantize": True, "outlier_ratio": 0.0, "outlier_type": "uniform"},
            # --- outlier sweep, uniform replacement (sigma = 0.5 px)
            {"noise_sigma": 0.5, "quantize": False, "outlier_ratio": 0.05, "outlier_type": "uniform"},
            {"noise_sigma": 0.5, "quantize": False, "outlier_ratio": 0.20, "outlier_type": "uniform"},
            {"noise_sigma": 0.5, "quantize": False, "outlier_ratio": 0.50, "outlier_type": "uniform"},
            {"noise_sigma": 0.5, "quantize": False, "outlier_ratio": 0.80, "outlier_type": "uniform"},
            {"noise_sigma": 0.5, "quantize": False, "outlier_ratio": 0.95, "outlier_type": "uniform"},
            # --- outlier sweep, swapped assignments (sigma = 0.5 px)
            {"noise_sigma": 0.5, "quantize": False, "outlier_ratio": 0.20, "outlier_type": "swap"},
            {"noise_sigma": 0.5, "quantize": False, "outlier_ratio": 0.50, "outlier_type": "swap"},
            # --- everything at once
            {"noise_sigma": 1.0, "quantize": True, "outlier_ratio": 0.50, "outlier_type": "mixed"},
        ],
        "factorial": {
            "noise_sigma": [0.0, 0.5, 2.0],
            "quantize": [False, True],
            "outlier_ratio": [0.0, 0.2, 0.5, 0.8],
            "outlier_type": ["uniform", "swap"],
        },
    },
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge ``override`` onto a deep copy of ``base``."""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_config(path: "str | Path | None" = None) -> Dict[str, Any]:
    """Load a YAML configuration (or the defaults when ``path`` is None)."""
    cfg = copy.deepcopy(DEFAULTS)
    if path is not None:
        with open(path, "r", encoding="utf-8") as fh:
            user_cfg = yaml.safe_load(fh) or {}
        # Scene counts and condition lists are replaced, not merged, so a YAML
        # file can restrict the set of scene types / conditions.
        if "scenes" in user_cfg and "counts" in user_cfg["scenes"]:
            cfg["scenes"]["counts"] = {}
        if "conditions" in user_cfg and "items" in user_cfg["conditions"]:
            cfg["conditions"]["items"] = []
        cfg = deep_merge(cfg, user_cfg)
    validate_config(cfg)
    return cfg


def config_to_yaml(cfg: Dict[str, Any]) -> str:
    return yaml.safe_dump(cfg, sort_keys=False, default_flow_style=None)


def config_to_json(cfg: Dict[str, Any]) -> str:
    return json.dumps(cfg, indent=2, sort_keys=False)


def _check_probs(name: str, probs: Dict[str, float], allowed: Iterable[str]) -> None:
    allowed = set(allowed)
    for key, value in probs.items():
        if key not in allowed:
            raise ValueError(f"{name}: unknown key '{key}' (allowed: {sorted(allowed)})")
        if value < 0:
            raise ValueError(f"{name}: negative probability for '{key}'")
    if sum(probs.values()) <= 0:
        raise ValueError(f"{name}: probabilities must not all be zero")


def expand_conditions(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the list of noise conditions described by the configuration."""
    cc = cfg["conditions"]
    mode = cc.get("mode", "list")
    if mode == "list":
        items = [dict(item) for item in cc["items"]]
    elif mode == "factorial":
        fac = cc["factorial"]
        items = []
        for sigma in fac["noise_sigma"]:
            for quant in fac["quantize"]:
                for ratio in fac["outlier_ratio"]:
                    types = fac["outlier_type"] if ratio > 0 else [fac["outlier_type"][0]]
                    for otype in types:
                        items.append(
                            {
                                "noise_sigma": float(sigma),
                                "quantize": bool(quant),
                                "outlier_ratio": float(ratio),
                                "outlier_type": str(otype),
                            }
                        )
    else:
        raise ValueError(f"conditions.mode must be 'list' or 'factorial', got '{mode}'")
    for item in items:
        item.setdefault("noise_sigma", 0.0)
        item.setdefault("quantize", False)
        item.setdefault("outlier_ratio", 0.0)
        item.setdefault("outlier_type", "uniform")
        item["noise_sigma"] = float(item["noise_sigma"])
        item["quantize"] = bool(item["quantize"])
        item["outlier_ratio"] = float(item["outlier_ratio"])
        item["outlier_type"] = str(item["outlier_type"])
        if item["noise_sigma"] < 0:
            raise ValueError("noise_sigma must be >= 0")
        if not 0.0 <= item["outlier_ratio"] < 1.0:
            raise ValueError("outlier_ratio must be in [0, 1)")
        if item["outlier_type"] not in OUTLIER_TYPES:
            raise ValueError(f"outlier_type must be one of {OUTLIER_TYPES}")
    if not items:
        raise ValueError("at least one noise condition is required")
    return items


def validate_config(cfg: Dict[str, Any]) -> None:
    """Raise ``ValueError`` on inconsistent configurations."""
    ds = cfg["dataset"]
    if abs(sum(ds["splits"].values()) - 1.0) > 1e-6:
        raise ValueError("dataset.splits fractions must sum to 1")
    if ds["compression"] not in ("gzip", "none"):
        raise ValueError("dataset.compression must be 'gzip' or 'none'")

    sc = cfg["scenes"]
    for name, count in sc["counts"].items():
        if name not in SCENE_TYPES:
            raise ValueError(f"unknown scene type '{name}' (allowed: {SCENE_TYPES})")
        if int(count) < 0:
            raise ValueError("scene counts must be >= 0")
    if sum(int(c) for c in sc["counts"].values()) == 0:
        raise ValueError("at least one scene must be generated")
    lo, hi = sc["num_points"]
    if lo < 8 or hi < lo:
        raise ValueError("scenes.num_points must satisfy 8 <= lo <= hi")
    _check_probs("scenes.planar_layout_probs", sc["planar_layout_probs"], ("grid", "random"))

    cam = cfg["cameras"]
    _check_probs("cameras.model_probs", cam["model_probs"], CAMERA_MODELS)
    for model, probs in cam["fov_class_probs"].items():
        if model not in CAMERA_MODELS:
            raise ValueError(f"cameras.fov_class_probs: unknown model '{model}'")
        _check_probs(f"cameras.fov_class_probs.{model}", probs, cam["fov_classes"].keys())
    for name, spec in cam["fov_classes"].items():
        lo, hi = spec["hfov_deg"]
        if not (0 < lo <= hi < 180):
            raise ValueError(f"cameras.fov_classes.{name}.hfov_deg must be within (0, 180)")
    _check_probs("cameras.distortion_levels.probs", cam["distortion_levels"]["probs"], DISTORTION_LEVELS)
    if cam["num_intrinsics_per_scene"] < 1 or cam["num_poses_per_intrinsics"] < 1:
        raise ValueError("cameras.num_intrinsics_per_scene and num_poses_per_intrinsics must be >= 1")
    if cam["min_visible_points"] < 4:
        raise ValueError("cameras.min_visible_points must be >= 4")
    for res in cam["resolutions"]:
        if len(res) != 2 or res[0] <= 0 or res[1] <= 0:
            raise ValueError("cameras.resolutions entries must be [width, height] > 0")

    po = cfg["poses"]
    if not (0 <= po["min_elevation_deg"] < 90):
        raise ValueError("poses.min_elevation_deg must be in [0, 90)")
    expand_conditions(cfg)


def scene_specs(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Enumerate every scene to generate as ``{"scene_id", "scene_type", "split",
    "index_in_type"}``.  Splits are assigned per scene type by contiguous index
    ranges so that every split contains every scene type (deterministic).
    """
    specs: List[Dict[str, Any]] = []
    fractions = cfg["dataset"]["splits"]
    split_names = list(fractions.keys())
    scene_id = 0
    for scene_type in SCENE_TYPES:
        count = int(cfg["scenes"]["counts"].get(scene_type, 0))
        if count == 0:
            continue
        allocation = allocate_counts(count, [fractions[name] for name in split_names])
        start = 0
        for name, n_split in zip(split_names, allocation):
            for i in range(start, start + n_split):
                specs.append(
                    {"scene_id": scene_id, "scene_type": scene_type, "split": name, "index_in_type": i}
                )
                scene_id += 1
            start += n_split
    return specs


def allocate_counts(count: int, fractions: List[float]) -> List[int]:
    """
    Split ``count`` items according to ``fractions`` (largest-remainder rounding).
    When ``count`` >= number of non-zero fractions, every such split receives at
    least one item, so small configurations still populate every split.
    """
    raw = [f * count for f in fractions]
    alloc = [int(x) for x in raw]
    remainder = count - sum(alloc)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - alloc[i], reverse=True)
    for i in order[:remainder]:
        alloc[i] += 1
    nonzero = [i for i, f in enumerate(fractions) if f > 0]
    if count >= len(nonzero):
        for i in nonzero:
            if alloc[i] == 0:
                donor = max(range(len(alloc)), key=lambda j: alloc[j])
                alloc[donor] -= 1
                alloc[i] += 1
    return alloc
