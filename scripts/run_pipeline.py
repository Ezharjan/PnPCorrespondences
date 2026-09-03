#!/usr/bin/env python
"""
Run the whole pipeline: generate -> validate -> examples -> benchmark -> analyze -> figures -> dataset card.

    python scripts/run_pipeline.py --config configs/smoke.yaml --out-root runs/smoke --workers 2
    python scripts/run_pipeline.py --config configs/full.yaml  --out-root .           --workers 6 --max-samples 3000

Outputs land in <out-root>/data, <out-root>/results and <out-root>/docs/figures
(the directory the README embeds; override it with --figures).
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd, label):
    print(f"\n=== {label}\n$ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    rc = subprocess.call(cmd)
    print(f"=== {label}: exit {rc} in {time.time() - t0:.0f}s", flush=True)
    if rc != 0:
        sys.exit(rc)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out-root", default=".", help="directory that will contain data/, results/, docs/figures/")
    parser.add_argument("--figures", default=None,
                        help="figure directory (default: <out-root>/docs/figures, which the README embeds)")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=1500, help="benchmark sample budget")
    parser.add_argument("--sweep-samples", type=int, default=400)
    parser.add_argument("--max-rigs", type=int, default=60)
    parser.add_argument("--validate-cameras", type=int, default=None, help="cameras to validate (default: all)")
    parser.add_argument("--repo-id", default="Ezharjan/PnPCorrespondences", help="used in the dataset card")
    parser.add_argument("--skip-generate", action="store_true", help="reuse an existing <out-root>/data")
    parser.add_argument("--skip-benchmark", action="store_true")
    args = parser.parse_args()

    root = Path(args.out_root)
    data, results = root / "data", root / "results"
    figures = Path(args.figures) if args.figures else root / "docs" / "figures"
    py = sys.executable
    s = ROOT / "scripts"
    if not args.skip_generate:
        run([py, str(s / "generate_dataset.py"), "--config", args.config, "--out", str(data), "--workers", str(args.workers),
             "--overwrite"], "generate")
    cmd = [py, str(s / "validate_dataset.py"), "--data", str(data)]
    if args.validate_cameras:
        cmd += ["--max-cameras", str(args.validate_cameras)]
    run(cmd, "validate")
    run([py, str(s / "export_examples.py"), "--data", str(data)], "examples")
    if not args.skip_benchmark:
        run([py, str(s / "run_benchmark.py"), "--data", str(data), "--out", str(results), "--task", "all",
             "--max-samples", str(args.max_samples), "--sweep-samples", str(args.sweep_samples), "--max-rigs", str(args.max_rigs)], "benchmark")
        run([py, str(s / "analyze_results.py"), "--results", str(results)], "analyze")
        run([py, str(s / "make_figures.py"), "--data", str(data), "--results", str(results), "--out", str(figures)], "figures")
    else:
        run([py, str(s / "make_figures.py"), "--data", str(data), "--out", str(figures), "--dataset-only"], "figures")
    run([py, str(s / "build_dataset_card.py"), "--data", str(data), "--repo-id", args.repo_id], "dataset card")
    print(f"\npipeline complete: {data}  {results}  {figures}")


if __name__ == "__main__":
    main()
