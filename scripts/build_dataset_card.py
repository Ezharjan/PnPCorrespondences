#!/usr/bin/env python
"""
Write the Hugging Face dataset card (README.md with YAML metadata) into the dataset directory.

Also writes one Parquet manifest per split, which the card's `configs:` block declares so
the Hub's dataset viewer shows the splits.

    python scripts/build_dataset_card.py --data data --repo-id Ezharjan/PnPCorrespondences --license cc-by-4.0
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.hf import build_dataset_card  # noqa: E402
from pnpcorr.storage import write_split_manifests  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True, help="dataset directory")
    parser.add_argument("--repo-id", required=True, help="Hugging Face dataset id, e.g. Ezharjan/PnPCorrespondences")
    parser.add_argument("--license", default="cc-by-4.0", help="SPDX-like license id used by the Hub")
    parser.add_argument("--pretty-name", default=None)
    parser.add_argument("--homepage", default="")
    parser.add_argument("--code-url", default="", help="link the generator source in the card (omit if the repository is private)")
    parser.add_argument("--doi", default="", help="DOI of the dataset, once minted on the Hub")
    args = parser.parse_args()
    # One Parquet manifest per split, which is what the card's `configs:` block
    # points the Hub's dataset viewer at.
    for path in write_split_manifests(args.data):
        print(f"split manifest: {path}")
    card = build_dataset_card(args.data, args.repo_id, args.license, args.pretty_name, args.homepage,
                              code_url=args.code_url, doi=args.doi)
    path = Path(args.data) / "README.md"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(card)
    print(f"dataset card written to {path}")


if __name__ == "__main__":
    main()
