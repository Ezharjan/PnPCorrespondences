#!/usr/bin/env python
"""
Delete every cache and build artefact of the project with one command.

    python scripts/clean_caches.py                 # clean the repository
    python scripts/clean_caches.py --dry-run       # list what would be deleted
    python scripts/clean_caches.py --all           # also the Hugging Face upload cache
    python scripts/clean_caches.py --root runs     # clean another directory tree

Generated *data* is never touched: datasets (``data/``, ``runs/``) and benchmark
results (``results/``) are deliberately left in place and must be removed by hand
when you want to regenerate them, and ``docs/`` - including the figures the README
embeds - is version-controlled documentation that no script deletes.  Only the entries
listed in ``CACHE_DIRS`` / ``CACHE_FILES`` below are removed, matched by exact
name, so the script can never delete a dataset by accident.
"""
import argparse
import shutil
import sys
from pathlib import Path

# Directory names removed anywhere under the root.
CACHE_DIRS = (
    "__pycache__",        # Python bytecode
    ".pytest_cache",      # pytest
    ".mypy_cache",        # mypy
    ".ruff_cache",        # ruff
    ".ipynb_checkpoints",  # Jupyter
    "htmlcov",            # coverage HTML report
    "build",              # setuptools build tree
    "dist",               # built wheels / sdists
)
# Directory names removed only at the root of the tree (never nested, so a
# user directory called "*.egg-info" deeper in a dataset is left alone).
CACHE_DIR_SUFFIXES = (".egg-info",)
# File names / glob patterns removed anywhere under the root.
CACHE_FILE_GLOBS = ("*.pyc", "*.pyo", ".coverage", ".coverage.*")
# Removed only with --all: resumable-upload state written by huggingface_hub
# inside the dataset directory (deleting it restarts an interrupted upload).
HUB_CACHE = Path(".cache") / "huggingface"

# Never descend into these: they hold the generated dataset and are large.
SKIP_DIRS = {".git", ".hg", ".svn", "hdf5"}


def _size(path: Path) -> int:
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total


def find_targets(root: Path, include_hub_cache: bool = False):
    """Return the list of cache paths under ``root`` (deepest first)."""
    targets = []
    for entry in root.rglob("*"):
        parts = set(entry.parts)
        if parts & SKIP_DIRS:
            continue
        if entry.is_dir():
            if entry.name in CACHE_DIRS or entry.name.endswith(CACHE_DIR_SUFFIXES):
                targets.append(entry)
        elif entry.is_file():
            if any(entry.match(pattern) for pattern in CACHE_FILE_GLOBS):
                targets.append(entry)
    if include_hub_cache:
        for entry in root.rglob(str(HUB_CACHE)):
            if entry.is_dir():
                targets.append(entry)
    # Shallowest first, then drop every entry that already lives inside another
    # target (e.g. the .pyc files inside a __pycache__ directory) so that
    # nothing is reported or counted twice.
    targets.sort(key=lambda p: (len(p.parts), str(p)))
    kept, kept_dirs = [], []
    for path in targets:
        if any(parent in path.parents for parent in kept_dirs):
            continue
        kept.append(path)
        if path.is_dir():
            kept_dirs.append(path)
    return sorted(kept, key=lambda p: str(p))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=None, help="directory to clean (default: the repository root)")
    parser.add_argument("--dry-run", action="store_true", help="only list what would be deleted")
    parser.add_argument("--all", dest="include_hub_cache", action="store_true",
                        help="also delete .cache/huggingface (resumable-upload state) inside dataset directories")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    if not root.is_dir():
        sys.exit(f"{root} is not a directory")
    targets = find_targets(root, args.include_hub_cache)
    if not targets:
        print(f"nothing to clean under {root}")
        return
    freed = 0
    for path in targets:
        size = _size(path)
        freed += size
        kind = "dir " if path.is_dir() else "file"
        print(f"  {'would remove' if args.dry_run else 'removed'} {kind} {path.relative_to(root)}  ({size / 1e6:.2f} MB)")
        if not args.dry_run:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
            parent = path.parent
            if parent.name == ".cache" and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
    verb = "would free" if args.dry_run else "freed"
    print(f"{len(targets)} cache entries, {verb} {freed / 1e6:.2f} MB under {root}")
    if not args.include_hub_cache:
        print("(datasets, results and docs/ are never touched; --all also clears .cache/huggingface)")


if __name__ == "__main__":
    main()
