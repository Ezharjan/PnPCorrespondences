#!/usr/bin/env python
"""
Export small human-readable JSON examples (one per scene type x camera model).

    python scripts/export_examples.py --data data            # writes data/examples/
    python scripts/export_examples.py --data data --out examples/json --max-points 50
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.storage import export_examples  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True, help="dataset directory")
    parser.add_argument("--out", default=None, help="output directory (default: <data>/examples)")
    parser.add_argument("--per-group", type=int, default=1, help="examples per (scene type, camera model)")
    parser.add_argument("--max-points", type=int, default=200, help="correspondences listed per example")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    out = Path(args.out) if args.out else Path(args.data) / "examples"
    paths = export_examples(args.data, out, per_group=args.per_group, max_points=args.max_points, seed=args.seed)
    print(f"wrote {len(paths)} examples to {out}")


if __name__ == "__main__":
    main()
