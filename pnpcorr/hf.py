"""
Hugging Face Hub integration: dataset card generation and upload helpers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .storage import load_stats


def _size_category(n: int) -> str:
    for bound, label in [(1_000, "n<1K"), (10_000, "1K<n<10K"), (100_000, "10K<n<100K"), (1_000_000, "100K<n<1M"),
                         (10_000_000, "1M<n<10M")]:
        if n < bound:
            return label
    return "10M<n<100M"


AUTHOR = "Aizierjiang Aiersilan"


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
    n_samples = int(stats["num_samples"])
    size_gb = stats.get("hdf5_bytes", 0) / 1e9
    scenes = ", ".join(f"{k}: {v}" for k, v in stats["scenes_per_type"].items())
    models = ", ".join(f"{k}: {v}" for k, v in stats["cameras_per_model"].items())
    fovs = ", ".join(f"{k}: {v}" for k, v in stats["cameras_per_fov_class"].items())
    splits = ", ".join(f"{k}: {v}" for k, v in stats["samples_per_split"].items())
    conditions = "\n".join(f"| `{k}` | {v:,} |" for k, v in stats["samples_per_condition"].items())
    bibkey = repo_id.split("/")[-1].replace("-", "_").replace(".", "_")
    code_sentence = (f" ([source]({code_url}), MIT license)." if code_url else
                     " (MIT license); the methodology is summarised below.")
    doi_bib = f"\n  doi          = {{{doi}}}," if doi else ""
    files = "\n".join(f"- `hdf5/{f}`" for f in stats["files"])
    # The pretty name contains a colon, so it must be a quoted YAML scalar; JSON
    # string syntax is valid YAML and escapes quotes and backslashes correctly.
    front = f"""---
license: {license_id}
pretty_name: {json.dumps(name)}
language:
- en
tags:
- camera-calibration
- perspective-n-point
- pnp
- pose-estimation
- computer-vision
- 3d
- synthetic
- correspondences
- hdf5
task_categories:
- other
size_categories:
- {_size_category(n_samples)}
configs:
- config_name: manifest
  data_files: manifest.parquet
---
"""
    body = f"""
# {name}

`{repo_id}` is a fully synthetic, image-free dataset of **2D-3D point correspondences**
with exact ground truth, built for benchmarking Perspective-n-Point (PnP) solvers,
robust estimators, bundle adjustment and camera-calibration methods. Every sample is a
set of 3D world points, their (noisy) 2D pixel observations and the exact camera
intrinsics, lens distortion and extrinsics that produced them.

Because there are no images, every source of error is controlled explicitly: Gaussian
sub-pixel jitter, pixel quantization, outlier ratio (0 % to 95 %), outlier type
(uniform replacements or swapped assignments), lens model (pinhole, Brown-Conrady,
Kannala-Brandt fisheye), field of view (5 deg telephoto to 175 deg fisheye) and scene
structure (planar targets, room corners, volumes, mixed, depth-stratified corridors).

## Contents

| | |
|---|---|
| scenes | {stats['num_scenes']:,} ({scenes}) |
| camera views | {stats['num_cameras']:,} |
| samples (view x noise condition) | {n_samples:,} |
| 2D-3D correspondences | {stats['num_correspondences']:,} |
| camera models | {models} |
| FOV classes | {fovs} |
| splits (samples) | {splits} |
| HDF5 size | {size_gb:.2f} GB |
| master seed | {stats['master_seed']} |

### Noise conditions

| condition | samples |
|---|---|
{conditions}

Condition names read `s<sigma>_q<quantized>_o<outlier ratio>_<outlier type>`.

## Files

- `manifest.parquet` / `manifest.csv` - one row per sample with every scalar factor
  (scene type, split, camera model, FOV, intrinsics, distortion coefficients, noise
  parameters, number of visible points, ...) and the HDF5 location of the arrays.
- `metadata/dataset_stats.json`, `metadata/config_used.yaml` - statistics and the exact
  generator configuration.
- `examples/*.json` - small human-readable samples.
- HDF5 shards (one per scene type and part):
{files}

## HDF5 layout

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

## Generation

The dataset was produced by the `pnpcorr` generator{code_sentence} The exact
configuration is stored in `metadata/config_used.yaml`, and every array is a
deterministic function of the master seed (`{stats['master_seed']}`), so the dataset can
be regenerated bit-for-bit. Camera model conventions follow OpenCV
(`cv2.projectPoints` / `cv2.fisheye.projectPoints`); projections agree with those
functions to 1e-8 px.

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
