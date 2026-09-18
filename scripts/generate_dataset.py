#!/usr/bin/env python
"""
Generate the synthetic 2D-3D correspondence dataset.

Examples
--------
    python scripts/generate_dataset.py --config configs/smoke.yaml --out data_smoke
    python scripts/generate_dataset.py --config configs/full.yaml  --out data --workers 6
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.config import load_config, scene_specs  # noqa: E402
from pnpcorr.generate import generate_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, help="YAML configuration (see configs/)")
    parser.add_argument("--out", required=True, help="output directory of the dataset")
    parser.add_argument("--workers", type=int, default=1, help="worker processes for scene generation (default 1)")
    parser.add_argument("--seed", type=int, default=None, help="override dataset.master_seed")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing dataset in --out")
    parser.add_argument("--no-progress", action="store_true", help="disable the progress bar")
    args = parser.parse_args()

    out = Path(args.out)
    if (out / "manifest.csv").exists() or (out / "hdf5").exists():
        if not args.overwrite:
            sys.exit(f"{out} already contains a dataset; pass --overwrite to replace it or choose another --out")
        shutil.rmtree(out / "hdf5", ignore_errors=True)
        shutil.rmtree(out / "metadata", ignore_errors=True)
        shutil.rmtree(out / "examples", ignore_errors=True)
        for name in ("manifest.csv", "manifest.parquet", "README.md"):
            if (out / name).exists():
                (out / name).unlink()

    cfg = load_config(args.config)
    if args.seed is not None:
        cfg["dataset"]["master_seed"] = int(args.seed)
    specs = scene_specs(cfg)
    n_cam = cfg["cameras"]["num_intrinsics_per_scene"] * cfg["cameras"]["num_poses_per_intrinsics"]
    print(f"config: {args.config}  scenes: {len(specs)}  cameras/scene: {n_cam}  "
          f"conditions: {len(cfg['conditions']['items']) if cfg['conditions']['mode'] == 'list' else 'factorial'}  "
          f"seed: {cfg['dataset']['master_seed']}  workers: {args.workers}")
    generate_dataset(cfg, args.out, workers=args.workers, progress=not args.no_progress)
    print(f"dataset written to {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
