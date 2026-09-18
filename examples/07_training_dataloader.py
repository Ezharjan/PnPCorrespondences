#!/usr/bin/env python
"""
Feed the dataset to a learned pose estimator.

The `split` column and the per-scene organisation exist for exactly this: scenes,
not samples, are assigned to train / val / test, so no 3D structure is shared
across the split boundary.  This script builds a framework-free iterator that
yields fixed-size, normalised batches, and wraps it in a `torch.utils.data.Dataset`
when PyTorch happens to be installed (it is not a dependency of this project).

    python examples/07_training_dataloader.py --data data
    python examples/07_training_dataloader.py --data data --split train --num-points 256 --batch-size 8
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.cameras import undistort_to_pinhole_pixels  # noqa: E402
from pnpcorr.storage import SampleReader, load_manifest  # noqa: E402


class CorrespondenceDataset:
    """
    Fixed-size views of the dataset, ready to be stacked into a tensor.

    Every item is a dictionary of NumPy arrays:

    ``points_2d``    (n, 2) observations in normalised camera coordinates
    ``points_3d``    (n, 3) the matching world points, centred and scaled
    ``is_outlier``   (n,)   ground-truth label of every correspondence
    ``R``, ``t``     the pose to be predicted, world -> camera
    ``scale``, ``centroid``  what was removed from ``points_3d``, so a predicted
                     translation can be mapped back to metres

    The 2D points are undistorted to the equivalent pinhole image and expressed in
    normalised coordinates, so a network sees one geometry rather than one per lens.
    """

    def __init__(self, data_dir, split=None, query=None, num_points=256, seed=0):
        manifest = load_manifest(data_dir)
        if split:
            manifest = manifest[manifest["split"] == split]
        if query:
            manifest = manifest.query(query)
        # Only views with enough correspondences to fill a batch item.
        self.rows = manifest[manifest["num_visible"] >= num_points].reset_index(drop=True)
        self.num_points = int(num_points)
        self.seed = int(seed)
        self.reader = SampleReader(data_dir)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows.iloc[int(index)]
        sample = self.reader.read(row)
        intr = sample.intrinsics
        uv, invertible = undistort_to_pinhole_pixels(sample.uv, intr)
        uv = np.where(invertible[:, None], uv, sample.uv)
        # Normalised camera coordinates: (u - cx - s*yd) / fx, (v - cy) / fy.
        yn = (uv[:, 1] - intr.cy) / intr.fy
        xn = (uv[:, 0] - intr.cx - intr.skew * yn) / intr.fx
        xy = np.column_stack([xn, yn])

        rng = np.random.default_rng([self.seed, int(row["scene_id"]), int(row["camera_id"]),
                                     int(row["condition_id"])])
        idx = np.sort(rng.choice(sample.num_visible, self.num_points, replace=False))
        X = sample.X[idx]
        centroid = X.mean(axis=0)
        scale = float(np.linalg.norm(X - centroid, axis=1).mean()) or 1.0
        return {
            "points_2d": xy[idx].astype(np.float32),
            "points_3d": ((X - centroid) / scale).astype(np.float32),
            "is_outlier": sample.outlier_mask[idx].astype(np.float32),
            "R": sample.R.astype(np.float32),
            "t": sample.t.astype(np.float32),
            "centroid": centroid.astype(np.float32),
            "scale": np.float32(scale),
            "sample_id": sample.sample_id,
        }

    def batches(self, batch_size=8, shuffle=True, seed=0):
        """Yield dictionaries of stacked arrays; the last short batch is dropped."""
        order = np.arange(len(self))
        if shuffle:
            np.random.default_rng(seed).shuffle(order)
        for start in range(0, len(order) - batch_size + 1, batch_size):
            items = [self[i] for i in order[start:start + batch_size]]
            yield {key: (np.stack([it[key] for it in items]) if key != "sample_id"
                         else [it[key] for it in items]) for key in items[0]}

    def close(self):
        self.reader.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data", help="dataset directory")
    parser.add_argument("--split", default=None, help="train / val / test (default: all)")
    parser.add_argument("--query", default=None, help="pandas query applied to the manifest")
    parser.add_argument("--num-points", type=int, default=256, help="correspondences per item")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--num-batches", type=int, default=2, help="batches to show")
    args = parser.parse_args()

    manifest = load_manifest(args.data)
    print("scenes per split (scenes are split, not samples, so no 3D structure is shared):")
    scenes = manifest.drop_duplicates(["file", "scene_id"])
    for split, count in scenes["split"].value_counts().sort_index().items():
        types = ", ".join(f"{k}: {v}" for k, v in
                          scenes[scenes["split"] == split]["scene_type"].value_counts().sort_index().items())
        print(f"  {split:6s} {count:4d} scenes  ({types})")

    ds = CorrespondenceDataset(args.data, args.split, args.query, args.num_points)
    if len(ds) == 0:
        ds.close()
        sys.exit(f"no view has {args.num_points} correspondences; lower --num-points")
    print(f"\n{len(ds)} items with at least {args.num_points} correspondences"
          f"{' in split ' + args.split if args.split else ''}\n")
    try:
        for i, batch in enumerate(ds.batches(args.batch_size, seed=0)):
            if i >= args.num_batches:
                break
            shapes = "  ".join(f"{k}{tuple(v.shape)}" for k, v in batch.items() if isinstance(v, np.ndarray))
            print(f"batch {i}: {shapes}")
            fractions = " ".join(f"{v:.2f}" for v in batch["is_outlier"].mean(axis=1))
            print(f"          outlier fraction per item: {fractions}")
    finally:
        ds.close()

    try:
        import torch
        from torch.utils.data import DataLoader, Dataset
    except ImportError:
        print("\nPyTorch is not installed, so the tensor wrapper below is skipped; the NumPy batches")
        print("above already have the shapes a model needs. Install torch to run the rest.")
        return

    class TorchWrapper(Dataset):
        def __init__(self, inner):
            self.inner = inner

        def __len__(self):
            return len(self.inner)

        def __getitem__(self, index):
            item = self.inner[index]
            return {k: torch.from_numpy(np.asarray(v)) for k, v in item.items() if k != "sample_id"}

    ds = CorrespondenceDataset(args.data, args.split, args.query, args.num_points)
    try:
        loader = DataLoader(TorchWrapper(ds), batch_size=args.batch_size, shuffle=True, num_workers=0)
        batch = next(iter(loader))
        print("\ntorch batch: " + "  ".join(f"{k}{tuple(v.shape)}" for k, v in batch.items()))
    finally:
        ds.close()


if __name__ == "__main__":
    main()
