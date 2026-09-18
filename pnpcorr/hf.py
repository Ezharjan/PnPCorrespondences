"""
Hugging Face Hub integration: dataset card generation and upload helpers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .config import SPLIT_ORDER
from .storage import load_stats, split_manifest_name


def _size_category(n: int) -> str:
    for bound, label in [(1_000, "n<1K"), (10_000, "1K<n<10K"), (100_000, "10K<n<100K"), (1_000_000, "100K<n<1M"),
                         (10_000_000, "1M<n<10M")]:
        if n < bound:
            return label
    return "10M<n<100M"


AUTHOR = "Aizierjiang Aiersilan"

# Hub metadata.  ``task_categories`` must come from the Hub's controlled vocabulary,
# so it stays deliberately short; ``tags`` are free-form and are what the dataset is
# actually found by, both in the Hub's own search and in web search results.
TASK_CATEGORIES = ("robotics", "tabular-regression", "other")

TAGS = (
    "pnp", "perspective-n-point", "camera-pose-estimation", "camera-resectioning",
    "camera-calibration", "2d-3d-correspondences", "point-correspondences",
    "multiple-view-geometry", "projective-geometry", "geometric-computer-vision",
    "3d-vision", "computer-vision", "lens-distortion", "brown-conrady",
    "kannala-brandt", "fisheye", "camera-intrinsics", "camera-extrinsics",
    "ransac", "magsac", "bundle-adjustment", "outlier-robustness",
    "structure-from-motion", "slam", "photogrammetry", "synthetic-data",
    "benchmark", "reproducible-research", "hdf5",
)


def _split_files(data_dir: Path, stats: dict) -> "list[tuple[str, str]]":
    """The per-split Parquet manifests present on disk, in split order."""
    present = list(stats.get("samples_per_split", {}))
    names = [s for s in SPLIT_ORDER if s in present] + sorted(s for s in present if s not in SPLIT_ORDER)
    return [(s, split_manifest_name(s)) for s in names if (data_dir / split_manifest_name(s)).exists()]


def _front_matter(name: str, license_id: str, n_samples: int,
                  split_files: "list[tuple[str, str]]") -> str:
    """
    The Hub's YAML metadata block.

    Every key here is one the Hub indexes: ``license``, ``task_categories``,
    ``size_categories``, ``language`` and ``annotations_creators`` become facets on
    the dataset list, ``tags`` feed free-text search, and ``configs`` is what makes
    the dataset viewer open the manifest and show the splits.
    """
    lines = ["---",
             f"license: {license_id}",
             # The pretty name contains a colon, so it must be a quoted YAML scalar;
             # JSON string syntax is valid YAML and escapes quotes and backslashes.
             f"pretty_name: {json.dumps(name)}",
             "language:", "- en",
             "annotations_creators:", "- machine-generated",
             "source_datasets:", "- original",
             "task_categories:"]
    lines += [f"- {t}" for t in TASK_CATEGORIES]
    lines += ["size_categories:", f"- {_size_category(n_samples)}"]
    lines += ["tags:"] + [f"- {t}" for t in TAGS]
    lines += ["configs:"]
    if split_files:
        lines += ["- config_name: default", "  data_files:"]
        for split, file_name in split_files:
            lines += [f"  - split: {split}", f"    path: {file_name}"]
        lines += ["- config_name: manifest", "  data_files:", "  - split: all", "    path: manifest.parquet"]
    else:
        lines += ["- config_name: default", "  data_files:", "  - split: all", "    path: manifest.parquet"]
    lines += ["viewer: true", "---"]
    return "\n".join(lines) + "\n"


def build_dataset_card(data_dir: "str | Path", repo_id: str, license_id: str = "cc-by-4.0",
                       pretty_name: Optional[str] = None, homepage: str = "",
                       code_url: str = "", doi: str = "") -> str:
    """
    Render the Hugging Face dataset card (README.md with YAML front matter).

    ``code_url``, when given, is linked as the generator's source. ``doi`` is
    added to the citation.
    """
    data_dir = Path(data_dir)
    stats = load_stats(data_dir)
    name = pretty_name or "PnPCorrespondences: Synthetic 2D-3D Point Correspondences for Camera Calibration and PnP Benchmarking"
    short_name = name.split(":")[0].strip()
    n_samples = int(stats["num_samples"])
    size_gb = stats.get("hdf5_bytes", 0) / 1e9
    scenes = ", ".join(f"{k}: {v}" for k, v in stats["scenes_per_type"].items())
    models = ", ".join(f"{k}: {v}" for k, v in stats["cameras_per_model"].items())
    fovs = ", ".join(f"{k}: {v}" for k, v in stats["cameras_per_fov_class"].items())
    conditions = "\n".join(f"| `{k}` | {v:,} |" for k, v in stats["samples_per_condition"].items())
    bibkey = repo_id.split("/")[-1].replace("-", "_").replace(".", "_")
    code_sentence = (f" ([source]({code_url}), MIT license)." if code_url else
                     " (MIT license); the methodology is summarised below.")
    doi_bib = f"\n  doi          = {{{doi}}}," if doi else ""
    files = "\n".join(f"- `hdf5/{f}`" for f in stats["files"])

    split_files = _split_files(data_dir, stats)
    per_split = stats.get("samples_per_split", {})
    scenes_per_split = stats.get("scenes_per_split", {})
    split_rows = "\n".join(
        f"| `{split}` | `{file_name}` | {scenes_per_split.get(split, 0):,} | {per_split.get(split, 0):,} |"
        for split, file_name in split_files)
    if split_files:
        split_section = f"""The `split` column assigns every row to a split, and one Parquet file per split
carries exactly those rows:

| split | file | scenes | samples |
|---|---|---|---|
{split_rows}

Scenes, not samples, are assigned to a split, so no 3D structure and no camera is
shared across the boundary. Two configurations are declared: `default` exposes the
three splits above, and `manifest` is the complete table in one piece.

```python
from datasets import load_dataset

test = load_dataset("{repo_id}", split="test")                 # one split of the manifest
everything = load_dataset("{repo_id}", "manifest", split="all")  # every row
```
"""
    else:
        split_section = ("The `split` column assigns every row to a split. Scenes, not samples, are\n"
                         "assigned, so no 3D structure and no camera is shared across the boundary.\n")

    front = _front_matter(name, license_id, n_samples, split_files)
    body = f"""
# Dataset Card for {short_name}

`{repo_id}` is a fully synthetic, image-free dataset of **2D-3D point correspondences**
with exact ground truth, built for benchmarking Perspective-n-Point (PnP) solvers,
robust estimators, bundle adjustment and camera-calibration methods. Every sample is a
set of 3D world points, their (noisy) 2D pixel observations and the exact camera
intrinsics, lens distortion and extrinsics that produced them.

- **Curated by:** {AUTHOR}
- **License:** `{license_id}`
- **Version:** {stats.get('dataset_version', '1.0.0')} (format {stats.get('format_version', '1.0')})
- **Size:** {n_samples:,} samples, {stats['num_correspondences']:,} correspondences, {size_gb:.2f} GB of HDF5
- **Formats:** HDF5 (arrays), Parquet and CSV (manifest), JSON (readable examples)

## Dataset summary

Because there are no images, every source of error is controlled explicitly: Gaussian
sub-pixel jitter, pixel quantization, outlier ratio (0 % to 95 %), outlier type
(uniform replacement, swapped assignments or a mixture), lens model (pinhole, Brown-Conrady,
Kannala-Brandt fisheye), field of view (5 deg telephoto to 175 deg fisheye) and scene
structure (planar targets, room corners, volumes, mixed, depth-stratified corridors).
The same geometry is observed under every noise condition, so any two conditions differ
in exactly the factor that separates them and the effect of that factor is measurable
without confounds.

| | |
|---|---|
| scenes | {stats['num_scenes']:,} ({scenes}) |
| camera views | {stats['num_cameras']:,} |
| samples (view x noise condition) | {n_samples:,} |
| 2D-3D correspondences | {stats['num_correspondences']:,} |
| camera models | {models} |
| FOV classes | {fovs} |
| HDF5 size | {size_gb:.2f} GB |
| master seed | {stats['master_seed']} |

### Noise conditions

| condition | samples |
|---|---|
{conditions}

Condition names read `s<sigma>_q<quantized>_o<outlier ratio>_<outlier type>`.

## Uses

### Direct use

- Benchmarking PnP and camera-resectioning solvers (DLT, P3P, AP3P, EPnP, IPPE, SQPnP,
  iterative refinement) against exact poses rather than against another estimator.
- Measuring the breakdown point of robust estimators (RANSAC, USAC, MAGSAC++) with a
  ground-truth outlier mask, which makes inlier precision and recall observable.
- Single-view and multi-view camera calibration, including fisheye rigs, with exact
  intrinsics and distortion coefficients to compare against.
- Training and evaluating learned pose estimators and outlier classifiers: splits are
  by scene, and the manifest carries every factor as a column for stratification.
- Ablations over noise, quantization, contamination, lens model, field of view, scene
  structure and number of correspondences, one factor at a time.

### Out-of-scope use

- There are no images, so the dataset says nothing about feature detection, description
  or matching; correspondences are given, and their errors are prescribed.
- It is a controlled geometric benchmark, not a capture of the physical world: there is
  no photometric response, motion blur, rolling shutter or scene semantics.
- Real-world performance should be confirmed on real captures; what this dataset
  isolates is the estimator's behaviour under a known error model.

## Dataset structure

### Splits and configurations

{split_section}
### Files

- `manifest.parquet` / `manifest.csv` - one row per sample with every scalar factor
  (scene type, split, camera model, FOV, intrinsics, distortion coefficients, noise
  parameters, number of visible points, ...) and the HDF5 location of the arrays.
- `metadata/dataset_stats.json`, `metadata/config_used.yaml` - statistics and the exact
  generator configuration.
- `metadata/validation_report.json` - the validator's own report for this build.
- `examples/*.json` - small human-readable samples, one per (scene type, camera model),
  in strict RFC 8259 JSON (non-finite values are written as `null`, never as bare
  `NaN`/`Infinity` literals).
- HDF5 shards (one per scene type and part):
{files}

### HDF5 layout

```
/scene_XXXXX/                     attrs: scene_type, split, num_points, seed, ...
    points_3d        (N, 3) float64   world coordinates [m]
    point_labels     (N,)   int16     plane index of each point, -1 for volumetric points
    /camera_XXX/                  attrs: distortion_model, image_width, image_height, fov_class, hfov_deg, ...
        K                (3, 3) float64   intrinsics [[fx, s, cx], [0, fy, cy], [0, 0, 1]]
        dist_coeffs      (5,) or (4,)     (k1, k2, p1, p2, k3) Brown-Conrady / (k1..k4) Kannala-Brandt
        pose_Rt          (4, 4) float64   world -> camera:  X_c = R X_w + t
        camera_center    (3,)   float64
        points_2d_clean  (M, 2) float64   exact projections of the visible points
        point_indices    (M,)   int32     index into points_3d
        depths           (M,)   float64   z_c of the visible points
        /condition_XXX/           attrs: noise_sigma, quantize, outlier_ratio, outlier_type, num_outliers, ...
            points_2d    (M, 2) float64   noisy observations
            outlier_mask (M,)   bool      True where the observation does not belong to its 3D point
```

## Loading

```python
from huggingface_hub import snapshot_download
import h5py, pandas as pd

root = snapshot_download("{repo_id}", repo_type="dataset")
manifest = pd.read_parquet(f"{{root}}/manifest.parquet")
row = manifest[(manifest.split == "test") & (manifest.outlier_ratio == 0.2)].iloc[0]
with h5py.File(f"{{root}}/{{row.file}}", "r") as f:
    cond = f[row.h5_path]
    cam = cond.parent
    scene = cam.parent
    X = scene["points_3d"][()][cam["point_indices"][()]]   # (M, 3)
    uv = cond["points_2d"][()]                             # (M, 2) noisy observations
    K, dist, Rt = cam["K"][()], cam["dist_coeffs"][()], cam["pose_Rt"][()]
    outliers = cond["outlier_mask"][()]
```

`snapshot_download` accepts `allow_patterns`, so a single scene type can be fetched
without the rest, for example `allow_patterns=["manifest.parquet", "hdf5/planar_single_*"]`.

## Dataset creation

The dataset was produced by the `pnpcorr` generator{code_sentence} The exact
configuration is stored in `metadata/config_used.yaml`, and every array is a
deterministic function of the master seed (`{stats['master_seed']}`), so the dataset can
be regenerated bit-for-bit. Camera model conventions follow OpenCV
(`cv2.projectPoints` / `cv2.fisheye.projectPoints`); across the whole sampled camera
population the projections agree with those functions to better than 1e-11 px.

Notes on the design, relevant when interpreting the data:

- Distortion coefficients are sampled as the *effective* radial displacement at the
  image corner and converted to raw polynomial coefficients, so `mild` and `strong`
  mean the same thing at every focal length and resolution.
- Each distortion polynomial is restricted to its injective domain, bounded for
  Brown-Conrady by the first zero of the full 2-D Jacobian determinant, so every
  stored observation has a unique pre-image and can be undistorted exactly.
- Noise is applied as Gaussian jitter, then outlier contamination, then optional
  quantization, so every stored observation lies on the sensor grid when
  `quantize` is true.
- Observations are not clipped to the image, so the noise statistics are exact at
  the border.

Every build ships the validator's report: `metadata/validation_report.json` records the
number of consistency checks run over the released files and the number that failed.

## License

The dataset is released under `{license_id}`. Copyright (c) 2026 {AUTHOR}.

## Citation

```bibtex
@misc{{{bibkey},
  title        = {{{name}}},
  author       = {{{AUTHOR}}},
  year         = {{2026}},
  publisher    = {{Hugging Face}},{doi_bib}
  url          = {{https://huggingface.co/datasets/{repo_id}}}
}}
```
"""
    if homepage:
        body += f"\nProject page: {homepage}\n"
    return front + body

def upload_dataset(data_dir: "str | Path", repo_id: str, private: Optional[bool] = None,
                   token: Optional[str] = None, commit_message: str = "Upload dataset",
                   large: bool = True, log=print) -> str:
    """
    Create the dataset repository (if needed) and upload ``data_dir``.

    ``private`` is applied to an existing repository as well as to a new one.
    ``create_repo`` ignores its ``private`` argument when the repository already
    exists, so the visibility of an existing repository is set explicitly.
    ``None`` creates a private repository and leaves an existing one untouched.
    """
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset",
                    private=True if private is None else private, exist_ok=True)
    if private is not None:
        api.update_repo_settings(repo_id=repo_id, repo_type="dataset", private=private)
    info = api.repo_info(repo_id=repo_id, repo_type="dataset")
    log(f"repository {repo_id} is {'private' if info.private else 'PUBLIC'}")
    data_dir = str(Path(data_dir))
    if large:
        log("uploading with upload_large_folder (resumable, multi-threaded) ...")
        api.upload_large_folder(repo_id=repo_id, repo_type="dataset", folder_path=data_dir, print_report=True)
    else:
        log("uploading with upload_folder ...")
        api.upload_folder(repo_id=repo_id, repo_type="dataset", folder_path=data_dir, commit_message=commit_message,
                          ignore_patterns=[".cache/**"])
    url = f"https://huggingface.co/datasets/{repo_id}"
    log(f"done: {url}")
    return url
