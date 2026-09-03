#!/usr/bin/env python
"""
Build a dataset of your own design, in process, and validate it.

The YAML files under `configs/` only override the documented defaults in
`pnpcorr.config.DEFAULTS`, and nothing stops a caller from doing the same from
Python.  This script assembles a deliberately narrow tier - one lens family, one
sensor, a hand-written condition list - generates it, validates it and reports
what came out, which is the whole loop of Sections 8.5 and 14 of the README in
one file.

    python examples/08_custom_tier.py --out runs/custom
    python examples/08_custom_tier.py --out runs/custom --model kannala_brandt --scenes 2

The equivalent from the command line is a YAML file plus
`python scripts/generate_dataset.py --config <file> --out <dir>`.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.config import config_to_yaml, load_config  # noqa: E402
from pnpcorr.generate import generate_dataset  # noqa: E402
from pnpcorr.storage import load_manifest  # noqa: E402
from pnpcorr.validate import validate_dataset  # noqa: E402


def build_config(model: str, scenes: int, seed: int) -> dict:
    """A narrow, fully specified tier: one lens family, one sensor, four conditions."""
    cfg = load_config()                                   # start from the documented defaults
    cfg["dataset"]["name"] = f"PnPCorrespondences-{model}"
    cfg["dataset"]["master_seed"] = seed
    cfg["dataset"]["compression"] = "none"                # small and fast; see Section 7

    # Only two scene families, so the tier stays small but still contains the
    # planar degeneracy that the DLT cannot solve.
    cfg["scenes"]["counts"] = {"planar_single": scenes, "volumetric": scenes}
    cfg["scenes"]["num_points"] = [300, 600]
    cfg["scenes"]["scene_size"] = [5.0, 8.0]

    # One camera model, one sensor, one field-of-view class: every remaining
    # difference between views is then the pose.
    cfg["cameras"]["model_probs"] = {model: 1.0}
    cfg["cameras"]["fov_class_probs"] = {model: {"wide" if model == "kannala_brandt" else "normal": 1.0}}
    cfg["cameras"]["resolutions"] = [[1280, 720]]
    cfg["cameras"]["skew"] = {"probability": 0.0, "max_pixels": 0.0}
    cfg["cameras"]["num_intrinsics_per_scene"] = 2
    cfg["cameras"]["num_poses_per_intrinsics"] = 3

    # A hand-written condition list: one clean, one noisy, two contaminated.
    cfg["conditions"]["mode"] = "list"
    cfg["conditions"]["items"] = [
        {"noise_sigma": 0.0, "quantize": False, "outlier_ratio": 0.0, "outlier_type": "uniform"},
        {"noise_sigma": 1.0, "quantize": False, "outlier_ratio": 0.0, "outlier_type": "uniform"},
        {"noise_sigma": 1.0, "quantize": False, "outlier_ratio": 0.3, "outlier_type": "uniform"},
        {"noise_sigma": 1.0, "quantize": True, "outlier_ratio": 0.3, "outlier_type": "swap"},
    ]
    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="runs/custom", help="output directory")
    parser.add_argument("--model", default="brown_conrady",
                        choices=["pinhole", "brown_conrady", "kannala_brandt"])
    parser.add_argument("--scenes", type=int, default=3, help="scenes per family")
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--keep", action="store_true", help="do not delete an existing --out first")
    args = parser.parse_args()

    cfg = build_config(args.model, args.scenes, args.seed)   # load_config already validated the defaults
    out = Path(args.out)
    if out.exists() and not args.keep:
        shutil.rmtree(out)

    print("configuration overrides:")
    print("  " + config_to_yaml({"dataset": {k: cfg["dataset"][k] for k in ("name", "master_seed", "compression")},
                                 "scenes": {"counts": cfg["scenes"]["counts"]},
                                 "cameras": {"model_probs": cfg["cameras"]["model_probs"],
                                             "resolutions": cfg["cameras"]["resolutions"]},
                                 "conditions": {"items": cfg["conditions"]["items"]}}).replace("\n", "\n  "))

    stats = generate_dataset(cfg, out, workers=args.workers, progress=False, log=None)
    manifest = load_manifest(out)
    print(f"generated {stats['num_scenes']} scenes, {stats['num_cameras']} views, "
          f"{stats['num_samples']} samples, {stats['num_correspondences']:,} correspondences "
          f"in {stats['generation_seconds']:.1f}s ({stats['hdf5_bytes'] / 1e6:.1f} MB)")

    report = validate_dataset(out, regenerate=1, progress=False, log=None)
    print(f"validation: {report['num_checks']} checks, {report['num_failures']} failures")
    for failure in report["failures"][:5]:
        print("  FAIL", failure)

    print("\ncomposition:")
    print("  " + json.dumps({k: stats[k] for k in ("scenes_per_type", "scenes_per_split",
                                                   "cameras_per_model", "cameras_per_fov_class")}, indent=2)
          .replace("\n", "\n  "))
    print("\nsamples per condition:")
    for name, count in manifest.groupby("condition_name").size().items():
        print(f"  {name:26s} {count:5d}")
    print(f"\nwritten to {out.resolve()}")
    if report["failures"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
