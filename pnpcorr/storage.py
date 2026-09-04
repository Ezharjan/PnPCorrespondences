"""
HDF5 serialization, manifest and readers.

HDF5 layout (one file per scene type and shard)::

    /                                  attrs: dataset_name, dataset_version, format_version, ...
    /scene_00000/                      attrs: scene_id, scene_type, split, seed, num_points, ...
        points_3d        (N, 3) float64   world coordinates
        point_labels     (N,)   int16     plane index (-1 = volumetric point)
        /camera_000/                   attrs: camera_id, intrinsics_id, pose_id, distortion_model, image_width, ...
            K                (3, 3) float64   ground-truth intrinsics
            dist_coeffs      (5,) | (4,)      ground-truth distortion (OpenCV ordering / Kannala-Brandt)
            pose_Rt          (4, 4) float64   ground-truth extrinsics, world -> camera
            camera_center    (3,)   float64   camera center in world coordinates
            points_2d_clean  (M, 2) float64   exact projections of the visible points
            point_indices    (M,)   int32     index of every visible point into points_3d
            depths           (M,)   float64   camera-frame depth of the visible points
            /condition_000/            attrs: condition_id, noise_sigma, quantize, outlier_ratio, outlier_type, ...
                points_2d    (M, 2) float64   noisy projections (the observations)
                outlier_mask (M,)   bool      True where the observation was replaced / swapped

The manifest (``manifest.parquet`` and ``manifest.csv``) has one row per
condition sample and carries every scalar factor for filtering without opening
the HDF5 files.
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import math
import os
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import h5py
import numpy as np
import pandas as pd

from ._version import FORMAT_VERSION, __version__
from .cameras import Intrinsics
from .config import SPLIT_ORDER, config_to_json, config_to_yaml

MANIFEST_COLUMNS = [
    "sample_id", "file", "h5_path", "scene_id", "scene_type", "split", "num_points_3d", "scene_layout",
    "camera_id", "intrinsics_id", "pose_id", "camera_model", "fov_class", "hfov_deg", "vfov_deg",
    "image_width", "image_height", "fx", "fy", "cx", "cy", "skew", "distortion_level",
    "k1", "k2", "k3", "k4", "p1", "p2", "num_visible", "mean_depth",
    "condition_id", "condition_name", "noise_sigma", "quantize", "outlier_ratio", "outlier_type", "num_outliers",
]

MANIFEST_DTYPES = {
    "scene_id": "int64", "num_points_3d": "int64", "camera_id": "int64", "intrinsics_id": "int64",
    "pose_id": "int64", "image_width": "int64", "image_height": "int64", "num_visible": "int64",
    "condition_id": "int64", "num_outliers": "int64", "quantize": "bool",
    "hfov_deg": "float64", "vfov_deg": "float64", "fx": "float64", "fy": "float64", "cx": "float64",
    "cy": "float64", "skew": "float64", "k1": "float64", "k2": "float64", "k3": "float64", "k4": "float64",
    "p1": "float64", "p2": "float64", "mean_depth": "float64", "noise_sigma": "float64",
    "outlier_ratio": "float64",
}


def json_safe(value: Any) -> Any:
    """
    Recursively convert a value to something ``json.dump(..., allow_nan=False)``
    accepts.  JSON has no ``Infinity`` or ``NaN`` literals (RFC 8259), and the
    Python default of emitting them bare produces files that ``JSON.parse``, jq,
    Go and Rust all reject - so non-finite floats become ``null``.

    They do occur: ``valid_radius`` is infinite for a pinhole camera (no
    distortion limit) and ``elevation_deg`` is NaN for corridor poses.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (np.floating,)):
        v = float(value)
        return v if math.isfinite(v) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def dump_json(obj: Any, path: "str | Path", indent: int = 2) -> None:
    """Write strict, portable JSON (no NaN/Infinity literals)."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(json_safe(obj), fh, indent=indent, allow_nan=False)


def _to_python(value: Any) -> Any:
    """Convert HDF5 attribute values to plain Python / numpy types."""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.ndarray):
        if value.dtype.kind in ("S", "O"):
            return [_to_python(v) for v in value.tolist()]
        return value
    if isinstance(value, np.generic):
        return value.item()
    return value


def read_attrs(obj) -> Dict[str, Any]:
    return {key: _to_python(value) for key, value in obj.attrs.items()}


def write_attrs(obj, attrs: Dict[str, Any]) -> None:
    for key, value in attrs.items():
        if isinstance(value, str):
            obj.attrs[key] = value
        elif isinstance(value, (bool, np.bool_)):
            obj.attrs[key] = np.bool_(value)
        elif isinstance(value, (int, np.integer)):
            obj.attrs[key] = np.int64(value)
        elif isinstance(value, (float, np.floating)):
            obj.attrs[key] = np.float64(value)
        elif isinstance(value, np.ndarray):
            obj.attrs[key] = value
        elif isinstance(value, (list, tuple)):
            obj.attrs[key] = np.asarray(value)
        elif value is None:
            continue
        else:
            obj.attrs[key] = str(value)


# ----------------------------------------------------------------------------
# Writer
# ----------------------------------------------------------------------------
class DatasetWriter:
    """Writes scene records produced by :mod:`pnpcorr.generate` to disk."""

    def __init__(self, out_dir: "str | Path", cfg: Dict[str, Any]):
        self.out_dir = Path(out_dir)
        self.h5_dir = self.out_dir / "hdf5"
        self.meta_dir = self.out_dir / "metadata"
        self.h5_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self.cfg = cfg
        self.max_scenes_per_file = int(cfg["dataset"]["max_scenes_per_file"])
        self.compression = cfg["dataset"]["compression"]
        self.compression_level = int(cfg["dataset"]["compression_level"])
        self._files: Dict[str, h5py.File] = {}
        self._file_scene_counts: Dict[str, int] = {}
        self._part_index: Dict[str, int] = {}
        self._current_file_name: Dict[str, str] = {}
        self._manifest_path = self.out_dir / "manifest.csv"
        self._manifest_fh = open(self._manifest_path, "w", newline="", encoding="utf-8")
        self._manifest_writer = csv.DictWriter(self._manifest_fh, fieldnames=MANIFEST_COLUMNS)
        self._manifest_writer.writeheader()
        self.stats: Dict[str, Any] = {
            "num_scenes": 0, "num_cameras": 0, "num_samples": 0, "num_cameras_skipped": 0,
            "num_scenes_empty": 0, "num_correspondences": 0, "files": [],
        }
        self.created_utc = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()

    # -- file management -----------------------------------------------------
    def _dataset_kwargs(self, shape) -> Dict[str, Any]:
        size = int(np.prod(shape)) if len(shape) else 1
        if self.compression == "gzip" and size >= 64:
            return {"compression": "gzip", "compression_opts": self.compression_level, "shuffle": True}
        return {}

    def _file_for(self, scene_type: str) -> h5py.File:
        count = self._file_scene_counts.get(scene_type, 0)
        if scene_type in self._files and count < self.max_scenes_per_file:
            return self._files[scene_type]
        if scene_type in self._files:
            self._files[scene_type].close()
            del self._files[scene_type]
        part = self._part_index.get(scene_type, 0)
        name = f"{scene_type}_{part:03d}.h5"
        fh = h5py.File(self.h5_dir / name, "w")
        write_attrs(fh, {
            "dataset_name": self.cfg["dataset"]["name"],
            "dataset_version": self.cfg["dataset"]["version"],
            "format_version": FORMAT_VERSION,
            "generator_version": __version__,
            "created_utc": self.created_utc,
            "master_seed": int(self.cfg["dataset"]["master_seed"]),
            "scene_type": scene_type,
            "part": part,
            "units": self.cfg["dataset"]["units"],
            "config_json": config_to_json(self.cfg),
        })
        self._files[scene_type] = fh
        self._file_scene_counts[scene_type] = 0
        self._part_index[scene_type] = part + 1
        self._current_file_name[scene_type] = name
        self.stats["files"].append(name)
        return fh

    # -- writing -------------------------------------------------------------
    def write_scene(self, rec: Dict[str, Any]) -> None:
        self.stats["num_cameras_skipped"] += int(rec.get("num_cameras_skipped", 0))
        if not rec["cameras"]:
            # Every pose of this scene failed the visibility test.  Writing it would
            # put 3D points in the file that no sample refers to and would leave
            # `num_scenes` in dataset_stats.json disagreeing with the manifest, which
            # indexes samples.  The scene is counted instead of stored.
            self.stats["num_scenes_empty"] += 1
            return
        scene_type = rec["scene_type"]
        fh = self._file_for(scene_type)
        file_name = self._current_file_name[scene_type]
        self._file_scene_counts[scene_type] += 1

        sg = fh.create_group(f"scene_{rec['scene_id']:05d}")
        pts = np.ascontiguousarray(rec["points_3d"], dtype=np.float64)
        sg.create_dataset("points_3d", data=pts, **self._dataset_kwargs(pts.shape))
        labels = np.ascontiguousarray(rec["point_labels"], dtype=np.int16)
        sg.create_dataset("point_labels", data=labels, **self._dataset_kwargs(labels.shape))
        scene_attrs = dict(rec["scene_attrs"])
        scene_attrs.update({"scene_id": int(rec["scene_id"]), "split": rec["split"], "seed": int(rec["seed"]),
                            "num_cameras": len(rec["cameras"])})
        write_attrs(sg, scene_attrs)

        for cam in rec["cameras"]:
            cg = sg.create_group(f"camera_{cam['camera_id']:03d}")
            cg.create_dataset("K", data=np.asarray(cam["K"], dtype=np.float64))
            cg.create_dataset("dist_coeffs", data=np.asarray(cam["dist_coeffs"], dtype=np.float64))
            cg.create_dataset("pose_Rt", data=np.asarray(cam["pose_Rt"], dtype=np.float64))
            cg.create_dataset("camera_center", data=np.asarray(cam["camera_center"], dtype=np.float64))
            uv_clean = np.ascontiguousarray(cam["points_2d_clean"], dtype=np.float64)
            cg.create_dataset("points_2d_clean", data=uv_clean, **self._dataset_kwargs(uv_clean.shape))
            idx = np.ascontiguousarray(cam["point_indices"], dtype=np.int32)
            cg.create_dataset("point_indices", data=idx, **self._dataset_kwargs(idx.shape))
            depths = np.ascontiguousarray(cam["depths"], dtype=np.float64)
            cg.create_dataset("depths", data=depths, **self._dataset_kwargs(depths.shape))
            cam_attrs = dict(cam["attrs"])
            cam_attrs.update({"camera_id": int(cam["camera_id"]), "num_visible": int(len(idx)),
                              "num_conditions": len(cam["conditions"])})
            write_attrs(cg, cam_attrs)
            K = np.asarray(cam["K"])
            coeffs = np.asarray(cam["dist_coeffs"], dtype=np.float64)
            model = cam_attrs["distortion_model"]
            if model == "kannala_brandt":
                k1, k2, k3, k4, p1, p2 = coeffs[0], coeffs[1], coeffs[2], coeffs[3], np.nan, np.nan
            else:
                k1, k2, p1, p2, k3, k4 = coeffs[0], coeffs[1], coeffs[2], coeffs[3], coeffs[4], np.nan

            for cond in cam["conditions"]:
                dg = cg.create_group(f"condition_{cond['condition_id']:03d}")
                uv = np.ascontiguousarray(cond["points_2d"], dtype=np.float64)
                dg.create_dataset("points_2d", data=uv, **self._dataset_kwargs(uv.shape))
                mask = np.ascontiguousarray(cond["outlier_mask"], dtype=bool)
                dg.create_dataset("outlier_mask", data=mask, **self._dataset_kwargs(mask.shape))
                cond_attrs = dict(cond["attrs"])
                cond_attrs["condition_id"] = int(cond["condition_id"])
                write_attrs(dg, cond_attrs)
                h5_path = f"/scene_{rec['scene_id']:05d}/camera_{cam['camera_id']:03d}/condition_{cond['condition_id']:03d}"
                row = {
                    "sample_id": f"{Path(file_name).stem}{h5_path}",
                    "file": f"hdf5/{file_name}",
                    "h5_path": h5_path,
                    "scene_id": int(rec["scene_id"]),
                    "scene_type": scene_type,
                    "split": rec["split"],
                    "num_points_3d": int(len(pts)),
                    "scene_layout": scene_attrs.get("layout", ""),
                    "camera_id": int(cam["camera_id"]),
                    "intrinsics_id": int(cam_attrs["intrinsics_id"]),
                    "pose_id": int(cam_attrs["pose_id"]),
                    "camera_model": model,
                    "fov_class": cam_attrs["fov_class"],
                    "hfov_deg": float(cam_attrs["hfov_deg"]),
                    "vfov_deg": float(cam_attrs["vfov_deg"]),
                    "image_width": int(cam_attrs["image_width"]),
                    "image_height": int(cam_attrs["image_height"]),
                    "fx": float(K[0, 0]), "fy": float(K[1, 1]), "cx": float(K[0, 2]), "cy": float(K[1, 2]),
                    "skew": float(K[0, 1]),
                    "distortion_level": cam_attrs["distortion_level"],
                    "k1": float(k1), "k2": float(k2), "k3": float(k3), "k4": float(k4),
                    "p1": float(p1), "p2": float(p2),
                    "num_visible": int(len(idx)),
                    "mean_depth": float(depths.mean()) if len(depths) else float("nan"),
                    "condition_id": int(cond["condition_id"]),
                    "condition_name": cond_attrs["name"],
                    "noise_sigma": float(cond_attrs["noise_sigma"]),
                    "quantize": bool(cond_attrs["quantize"]),
                    "outlier_ratio": float(cond_attrs["outlier_ratio"]),
                    "outlier_type": cond_attrs["outlier_type"],
                    "num_outliers": int(cond_attrs["num_outliers"]),
                }
                self._manifest_writer.writerow(row)
                self.stats["num_samples"] += 1
                self.stats["num_correspondences"] += int(len(idx))
            self.stats["num_cameras"] += 1
        self.stats["num_scenes"] += 1

    # -- finalization --------------------------------------------------------
    def close(self) -> Dict[str, Any]:
        for fh in self._files.values():
            fh.close()
        self._files.clear()
        self._manifest_fh.close()
        # float_precision="round_trip" is required: pandas' default C float parser
        # is not correctly rounded, so without it the Parquet manifest ends up one
        # unit in the last place away from the HDF5 attribute it was written from.
        manifest = pd.read_csv(self._manifest_path, dtype={"scene_layout": str, "condition_name": str},
                               keep_default_na=False, na_values=["nan", "NaN", ""],
                               float_precision="round_trip")
        for col, dtype in MANIFEST_DTYPES.items():
            if col in manifest.columns:
                manifest[col] = manifest[col].astype(dtype)
        manifest.to_parquet(self.out_dir / "manifest.parquet", index=False)
        write_split_manifests(self.out_dir, manifest)
        stats = compute_dataset_stats(manifest)
        stats.update({k: v for k, v in self.stats.items() if k != "files"})
        stats["files"] = sorted(self.stats["files"])
        stats["created_utc"] = self.created_utc
        stats["generator_version"] = __version__
        stats["format_version"] = FORMAT_VERSION
        stats["dataset_name"] = self.cfg["dataset"]["name"]
        stats["dataset_version"] = self.cfg["dataset"]["version"]
        stats["master_seed"] = int(self.cfg["dataset"]["master_seed"])
        total_bytes = 0
        for name in stats["files"]:
            total_bytes += os.path.getsize(self.h5_dir / name)
        stats["hdf5_bytes"] = int(total_bytes)
        dump_json(stats, self.meta_dir / "dataset_stats.json")
        with open(self.meta_dir / "config_used.yaml", "w", encoding="utf-8") as fh:
            fh.write(config_to_yaml(self.cfg))
        return stats


def compute_dataset_stats(manifest: pd.DataFrame) -> Dict[str, Any]:
    """Summary counts used by the dataset card and the README tables."""
    def counts(col):
        return {str(k): int(v) for k, v in manifest[col].value_counts().sort_index().items()}

    cameras = manifest.drop_duplicates(["file", "scene_id", "camera_id"])
    scenes = manifest.drop_duplicates(["file", "scene_id"])
    stats: Dict[str, Any] = {
        "num_scenes": int(len(scenes)),
        "num_cameras": int(len(cameras)),
        "num_samples": int(len(manifest)),
        "num_correspondences": int(manifest["num_visible"].sum()),
        "scenes_per_type": {str(k): int(v) for k, v in scenes["scene_type"].value_counts().sort_index().items()},
        "scenes_per_split": {str(k): int(v) for k, v in scenes["split"].value_counts().sort_index().items()},
        "samples_per_split": counts("split"),
        "samples_per_scene_type": counts("scene_type"),
        "cameras_per_model": {str(k): int(v) for k, v in cameras["camera_model"].value_counts().sort_index().items()},
        "cameras_per_fov_class": {str(k): int(v) for k, v in cameras["fov_class"].value_counts().sort_index().items()},
        "cameras_per_resolution": {f"{int(w)}x{int(h)}": int(v) for (w, h), v in
                                   cameras.groupby(["image_width", "image_height"]).size().items()},
        "samples_per_condition": {str(k): int(v) for k, v in manifest.groupby("condition_name").size().items()},
        "visible_points_per_view": {
            "min": int(cameras["num_visible"].min()), "median": float(cameras["num_visible"].median()),
            "mean": float(cameras["num_visible"].mean()), "max": int(cameras["num_visible"].max()),
        },
        "points_3d_per_scene": {
            "min": int(scenes["num_points_3d"].min()), "mean": float(scenes["num_points_3d"].mean()),
            "max": int(scenes["num_points_3d"].max()),
        },
    }
    return stats


# ----------------------------------------------------------------------------
# Readers
# ----------------------------------------------------------------------------
def load_manifest(data_dir: "str | Path") -> pd.DataFrame:
    data_dir = Path(data_dir)
    parquet = data_dir / "manifest.parquet"
    if parquet.exists():
        return pd.read_parquet(parquet)
    return pd.read_csv(data_dir / "manifest.csv", float_precision="round_trip")


def split_manifest_name(split: str) -> str:
    return f"manifest_{split}.parquet"


def write_split_manifests(data_dir: "str | Path", manifest: Optional[pd.DataFrame] = None,
                          overwrite: bool = True) -> List[Path]:
    """
    Partition the manifest on ``split`` and write one Parquet file per split.

    ``manifest.parquet`` remains the complete table; these files hold exactly its
    rows, grouped, so a reader can pull one split without downloading the rest and
    a catalogue that indexes Parquet files sees the splits the dataset declares.
    Returns the paths written, in split order.
    """
    data_dir = Path(data_dir)
    if manifest is None:
        manifest = load_manifest(data_dir)
    names = [s for s in SPLIT_ORDER if s in set(manifest["split"])]
    names += sorted(set(manifest["split"]) - set(SPLIT_ORDER))
    paths: List[Path] = []
    for split in names:
        path = data_dir / split_manifest_name(str(split))
        if overwrite or not path.exists():
            manifest[manifest["split"] == split].reset_index(drop=True).to_parquet(path, index=False)
        paths.append(path)
    return paths


def load_stats(data_dir: "str | Path") -> Dict[str, Any]:
    with open(Path(data_dir) / "metadata" / "dataset_stats.json", "r", encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class Sample:
    """One (scene, camera, condition) sample with everything needed to solve/evaluate."""
    sample_id: str
    file: str
    h5_path: str
    points_3d: np.ndarray        # (N, 3)
    point_labels: np.ndarray     # (N,)
    K: np.ndarray                # (3, 3)
    dist_coeffs: np.ndarray
    pose_Rt: np.ndarray          # (4, 4)
    camera_center: np.ndarray    # (3,)
    uv_clean: np.ndarray         # (M, 2)
    indices: np.ndarray          # (M,)
    depths: np.ndarray           # (M,)
    uv: np.ndarray               # (M, 2) noisy observations
    outlier_mask: np.ndarray     # (M,)
    scene_attrs: Dict[str, Any] = field(default_factory=dict)
    camera_attrs: Dict[str, Any] = field(default_factory=dict)
    condition_attrs: Dict[str, Any] = field(default_factory=dict)

    @property
    def R(self) -> np.ndarray:
        return self.pose_Rt[:3, :3]

    @property
    def t(self) -> np.ndarray:
        return self.pose_Rt[:3, 3]

    @property
    def X(self) -> np.ndarray:
        """(M, 3) 3D points matching the M observations."""
        return self.points_3d[self.indices]

    @property
    def intrinsics(self) -> Intrinsics:
        return Intrinsics.from_arrays(self.K, self.dist_coeffs, self.camera_attrs)

    @property
    def num_visible(self) -> int:
        return int(self.uv.shape[0])


def read_sample(h5: "h5py.File | str | Path", h5_path: str, file_label: str = "",
                file_name: str = "") -> Sample:
    """
    Read one sample from an open ``h5py.File`` (or a path) and a group path such
    as ``/scene_00003/camera_002/condition_007``.

    ``file_label`` is the prefix of ``sample_id`` (default: the file stem, which
    is what the manifest uses) and ``file_name`` is stored as ``Sample.file``
    (default: the file name; :class:`SampleReader` passes the manifest's
    dataset-relative path, e.g. ``hdf5/volumetric_000.h5``).
    """
    own = False
    if not isinstance(h5, h5py.File):
        h5 = h5py.File(h5, "r")
        own = True
    try:
        cond_grp = h5[h5_path]
        cam_grp = cond_grp.parent
        scene_grp = cam_grp.parent
        sample = Sample(
            sample_id=f"{file_label or Path(h5.filename).stem}{h5_path}",
            file=file_name or Path(h5.filename).name,
            h5_path=h5_path,
            points_3d=scene_grp["points_3d"][()],
            point_labels=scene_grp["point_labels"][()],
            K=cam_grp["K"][()],
            dist_coeffs=cam_grp["dist_coeffs"][()],
            pose_Rt=cam_grp["pose_Rt"][()],
            camera_center=cam_grp["camera_center"][()],
            uv_clean=cam_grp["points_2d_clean"][()],
            indices=cam_grp["point_indices"][()],
            depths=cam_grp["depths"][()],
            uv=cond_grp["points_2d"][()],
            outlier_mask=cond_grp["outlier_mask"][()].astype(bool),
            scene_attrs=read_attrs(scene_grp),
            camera_attrs=read_attrs(cam_grp),
            condition_attrs=read_attrs(cond_grp),
        )
    finally:
        if own:
            h5.close()
    return sample


class SampleReader:
    """
    Reads samples listed in a manifest, keeping a bounded number of HDF5 files open.

    HDF5 keeps a metadata cache per open file that grows with every object touched.
    A pass over a large tier touches hundreds of thousands of groups, so holding
    every shard open until the end costs several gigabytes; keeping at most
    ``max_open`` files and reopening one after ``reopen_after`` reads bounds the
    resident set to a constant, at the price of an occasional file open. Access
    patterns in this package are grouped by file, so files are rarely evicted.
    """

    def __init__(self, data_dir: "str | Path", max_open: int = 4, reopen_after: int = 2000):
        self.data_dir = Path(data_dir)
        self.max_open = max(1, int(max_open))
        self.reopen_after = max(1, int(reopen_after))
        self._files: "OrderedDict[str, h5py.File]" = OrderedDict()
        self._reads: Dict[str, int] = {}

    def file(self, rel_path: str) -> h5py.File:
        handle = self._files.get(rel_path)
        if handle is not None and self._reads[rel_path] >= self.reopen_after:
            handle.close()
            del self._files[rel_path]
            handle = None
        if handle is None:
            handle = h5py.File(self.data_dir / rel_path, "r")
            self._files[rel_path] = handle
            self._reads[rel_path] = 0
            while len(self._files) > self.max_open:
                _, evicted = self._files.popitem(last=False)
                evicted.close()
        self._files.move_to_end(rel_path)
        self._reads[rel_path] += 1
        return handle

    def read(self, row: "pd.Series | Dict[str, Any]") -> Sample:
        rel = str(row["file"])
        return read_sample(self.file(rel), str(row["h5_path"]), file_label=Path(rel).stem, file_name=rel)

    def iter_rows(self, manifest: pd.DataFrame) -> Iterator[Sample]:
        for _, row in manifest.iterrows():
            yield self.read(row)

    def close(self) -> None:
        for fh in self._files.values():
            fh.close()
        self._files.clear()
        self._reads.clear()

    def __enter__(self) -> "SampleReader":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


# ----------------------------------------------------------------------------
# JSON examples
# ----------------------------------------------------------------------------
def sample_to_json_dict(sample: Sample, max_points: Optional[int] = None) -> Dict[str, Any]:
    """Human-readable JSON representation of a sample (optionally truncated)."""
    def scal(d):
        return {k: json_safe(v) for k, v in d.items()}

    m = sample.num_visible if max_points is None else min(sample.num_visible, int(max_points))
    return json_safe({
        "sample_id": sample.sample_id,
        "source": {"file": sample.file, "h5_path": sample.h5_path},
        "scene": scal(sample.scene_attrs),
        "camera": scal(sample.camera_attrs),
        "condition": scal(sample.condition_attrs),
        "K": sample.K.tolist(),
        "dist_coeffs": sample.dist_coeffs.tolist(),
        "pose_Rt": sample.pose_Rt.tolist(),
        "camera_center": sample.camera_center.tolist(),
        "num_correspondences_total": sample.num_visible,
        "num_correspondences_listed": m,
        "correspondences": [
            {
                "point_index": int(sample.indices[i]),
                "point_3d": sample.points_3d[sample.indices[i]].tolist(),
                "point_2d": sample.uv[i].tolist(),
                "point_2d_clean": sample.uv_clean[i].tolist(),
                "depth": float(sample.depths[i]),
                "is_outlier": bool(sample.outlier_mask[i]),
            }
            for i in range(m)
        ],
    })


def export_examples(data_dir: "str | Path", out_dir: "str | Path", per_group: int = 1,
                    max_points: int = 200, seed: int = 0) -> List[Path]:
    """
    Write JSON examples covering every (scene type, camera model) combination and
    a spread of noise conditions.  Returns the written paths.
    """
    data_dir = Path(data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(data_dir)
    rng = np.random.default_rng(seed)
    written: List[Path] = []
    with SampleReader(data_dir) as reader:
        groups = manifest.groupby(["scene_type", "camera_model"], sort=True)
        for (scene_type, model), grp in groups:
            # Prefer a mid-range condition (noise + some outliers) for illustration.
            preferred = grp[(grp["outlier_ratio"] > 0) & (grp["outlier_ratio"] <= 0.5) & (grp["noise_sigma"] > 0)]
            pool = preferred if len(preferred) else grp
            picks = pool.sample(n=min(per_group, len(pool)), random_state=int(rng.integers(2**31 - 1)))
            for _, row in picks.iterrows():
                sample = reader.read(row)
                payload = sample_to_json_dict(sample, max_points=max_points)
                name = f"{scene_type}__{model}__{row['condition_name']}.json"
                path = out_dir / name
                dump_json(payload, path, indent=1)
                written.append(path)
    index = {"examples": [p.name for p in written], "note": "Each file lists at most "
             f"{max_points} correspondences of one sample; the HDF5 files hold the complete data."}
    dump_json(index, out_dir / "index.json")
    return written
