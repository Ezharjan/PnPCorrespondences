#!/usr/bin/env python
"""
Write the Hugging Face dataset card (README.md with YAML metadata) into the dataset directory.

    python scripts/build_dataset_card.py --data data --repo-id Ezharjan/PnPCorrespondences --license cc-by-4.0
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.hf import build_dataset_card  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True, help="dataset directory")
    parser.add_argument("--repo-id", required=True, help="Hugging Face dataset id, e.g. Ezharjan/PnPCorrespondences")
    parser.add_argument("--license", default="cc-by-4.0", help="SPDX-like license id used by the Hub")
    parser.add_argument("--pretty-name", default=None)
    parser.add_argument("--homepage", default="")
    args = parser.parse_args()
    card = build_dataset_card(args.data, args.repo_id, args.license, args.pretty_name, args.homepage)
    path = Path(args.data) / "README.md"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(card)
    print(f"dataset card written to {path}")


if __name__ == "__main__":
    main()
