#!/usr/bin/env python
"""
Render dataset figures (from the HDF5 files) and benchmark figures (from results/).

Figures are written to ``docs/figures/`` by default - the directory the README
embeds and links, so a regenerated set replaces the committed one in place and
the README then renders your own run.

    python scripts/make_figures.py --data data --results results
    python scripts/make_figures.py --data data --dataset-only
    python scripts/make_figures.py --data data --results results --out /tmp/fig
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pnpcorr.plots import make_benchmark_figures, make_dataset_figures  # noqa: E402

DEFAULT_OUT = ROOT / "docs" / "figures"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default=None, help="dataset directory (for the dataset figures)")
    parser.add_argument("--results", default=None, help="results directory (for the benchmark figures)")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="output directory for the PNG files (default: docs/figures of this repository)")
    parser.add_argument("--dataset-only", action="store_true")
    parser.add_argument("--benchmark-only", action="store_true")
    args = parser.parse_args()
    paths = []
    if args.data and not args.benchmark_only:
        paths += make_dataset_figures(args.data, args.out)
    if args.results and not args.dataset_only:
        paths += make_benchmark_figures(args.results, args.out)
    for p in paths:
        print("wrote", p)
    if not paths:
        print("nothing to draw: pass --data and/or --results")


if __name__ == "__main__":
    main()
