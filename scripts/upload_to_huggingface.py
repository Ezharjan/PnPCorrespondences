#!/usr/bin/env python
"""
Upload the dataset directory to the Hugging Face Hub as a dataset repository.

Authentication: run `hf auth login` (or `huggingface-cli login`) once, or pass
--token / set the HF_TOKEN environment variable.

    python scripts/upload_to_huggingface.py --data data --repo-id Ezharjan/PnPCorrespondences --private
    python scripts/upload_to_huggingface.py --data data --repo-id Ezharjan/PnPCorrespondences --public --dry-run
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pnpcorr.hf import build_dataset_card, upload_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True, help="dataset directory to upload")
    parser.add_argument("--repo-id", required=True, help="dataset id on the Hub, e.g. Ezharjan/PnPCorrespondences")
    parser.add_argument("--private", dest="private", action="store_true", default=True, help="private repository (default)")
    parser.add_argument("--public", dest="private", action="store_false", help="public repository")
    parser.add_argument("--token", default=None, help="Hub token (default: HF_TOKEN env var or cached login)")
    parser.add_argument("--license", default="cc-by-4.0")
    parser.add_argument("--no-card", action="store_true", help="do not (re)generate README.md before uploading")
    parser.add_argument("--simple-upload", action="store_true", help="use upload_folder instead of upload_large_folder")
    parser.add_argument("--dry-run", action="store_true", help="list what would be uploaded and exit")
    args = parser.parse_args()

    data = Path(args.data)
    if not (data / "manifest.parquet").exists():
        sys.exit(f"{data} does not look like a generated dataset (manifest.parquet missing)")
    if not args.no_card:
        with open(data / "README.md", "w", encoding="utf-8") as fh:
            fh.write(build_dataset_card(data, args.repo_id, args.license))
        print("dataset card refreshed:", data / "README.md")
    files = sorted(p for p in data.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in files)
    print(f"{len(files)} files, {total / 1e9:.3f} GB -> https://huggingface.co/datasets/{args.repo_id} "
          f"({'private' if args.private else 'public'})")
    if args.dry_run:
        for p in files[:50]:
            print("  ", p.relative_to(data), f"{p.stat().st_size / 1e6:.2f} MB")
        if len(files) > 50:
            print(f"   ... {len(files) - 50} more")
        return
    token = args.token or os.environ.get("HF_TOKEN")
    upload_dataset(data, args.repo_id, private=args.private, token=token, large=not args.simple_upload)


if __name__ == "__main__":
    main()
