"""End-to-end smoke test of the library API: generate -> validate -> benchmark -> analyse -> card."""
import pytest

from pnpcorr.analysis import summarize_calibration, summarize_pnp, write_summary
from pnpcorr.benchmark import (ransac_threshold, run_calibration_benchmark, run_pnp_benchmark,
                               select_samples)
from pnpcorr.config import load_config
from pnpcorr.generate import generate_dataset
from pnpcorr.hf import build_dataset_card
from pnpcorr.solvers import HAVE_CV2
from pnpcorr.storage import export_examples, load_manifest
from pnpcorr.validate import validate_dataset


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    cfg = load_config()
    cfg["scenes"]["counts"] = {"planar_single": 1, "volumetric": 1, "mixed": 1}
    cfg["scenes"]["num_points"] = [200, 300]
    cfg["cameras"]["num_intrinsics_per_scene"] = 1
    cfg["cameras"]["num_poses_per_intrinsics"] = 2
    cfg["conditions"]["items"] = [
        {"noise_sigma": 0.0, "quantize": False, "outlier_ratio": 0.0, "outlier_type": "uniform"},
        {"noise_sigma": 0.5, "quantize": True, "outlier_ratio": 0.3, "outlier_type": "mixed"},
    ]
    out = tmp_path_factory.mktemp("ds")
    generate_dataset(cfg, out, workers=1, progress=False, log=None)
    return out


def test_validation_passes(dataset):
    report = validate_dataset(dataset, regenerate=1, progress=False, log=None)
    assert report["passed"], report["failures"]
    assert report["num_checks"] > 100


def test_validation_detects_corrupted_observations(dataset, tmp_path):
    """The validator must reject a dataset whose noise no longer matches its metadata."""
    import shutil

    import h5py
    import numpy as np

    corrupted = tmp_path / "corrupted"
    shutil.copytree(dataset, corrupted)
    shard = sorted((corrupted / "hdf5").glob("*.h5"))[0]
    with h5py.File(shard, "r+") as fh:
        scene = fh[sorted(k for k in fh.keys() if k.startswith("scene_"))[0]]
        cam = scene[sorted(k for k in scene.keys() if k.startswith("camera_"))[0]]
        clean = cam["points_2d_clean"][()]
        cond = cam["condition_001"]                       # sigma = 0.5, quantized, 30 % outliers
        cond["points_2d"][...] = clean + 3.0 * (cond["points_2d"][()] - clean)
    report = validate_dataset(corrupted, regenerate=0, progress=False, log=None)
    assert not report["passed"]
    assert any("noise" in failure or "quantiz" in failure for failure in report["failures"])


def test_examples_and_card(dataset):
    paths = export_examples(dataset, dataset / "examples", per_group=1, max_points=20)
    assert paths and all(p.exists() for p in paths)
    card = build_dataset_card(dataset, "someone/pnp-test")
    assert card.startswith("---\nlicense: cc-by-4.0") and "manifest.parquet" in card


def test_dataset_card_front_matter_is_valid_yaml(dataset):
    """The Hub parses the YAML front matter; a colon in pretty_name must not break it."""
    import yaml

    card = build_dataset_card(dataset, "Ezharjan/PnPCorrespondences")
    assert card.startswith("---\n")
    meta = yaml.safe_load(card.split("---", 2)[1])
    assert meta["license"] == "cc-by-4.0"
    assert meta["pretty_name"].startswith("PnPCorrespondences:")
    assert meta["configs"][0]["data_files"] == "manifest.parquet"
    assert "Aizierjiang Aiersilan" in card and "github.com/Ezharjan/PnPCorrespondences" in card


def test_threshold_policy():
    assert ransac_threshold("auto", 0.0, False) == 2.0
    assert ransac_threshold("auto", 2.0, True) == 6.5
    assert ransac_threshold("4", 2.0, False) == 4.0


def test_benchmark_and_analysis(dataset, tmp_path):
    manifest = load_manifest(dataset)
    subset = select_samples(manifest, max_samples=4, seed=0)
    assert len(subset) == 4
    solvers = ["dlt_lm", "ransac_dlt"] + (["sqpnp", "cv_usac_magsac"] if HAVE_CV2 else [])
    df = run_pnp_benchmark(dataset, subset, solvers, ["all", 8], progress=False)
    assert set(df["solver"]) <= set(solvers)
    clean = df[(df["outlier_ratio"] == 0) & df["ok"]]
    assert (clean["rot_err_deg"] < 1e-4).all()
    planar_dlt = df[(df["scene_type"] == "planar_single") & (df["solver"] == "dlt_lm")]
    assert (~planar_dlt["ok"]).all() and planar_dlt["failure_reason"].str.contains("coplanar").all()
    summary = summarize_pnp(df, tmp_path / "tables")
    assert "Solver overview" in summary["markdown"]
    calib_subset = select_samples(manifest, 4, query="outlier_ratio == 0 and scene_type != 'planar_single'")
    cdf = run_calibration_benchmark(dataset, calib_subset, progress=False)
    assert cdf["ok"].all()
    pin = cdf[cdf["camera_model"] == "pinhole"]
    if len(pin):  # exact for undistorted cameras; distorted cameras show the expected DLT bias
        assert (pin["fx_err_pct"] < 1e-6).all()
    parts = {"pnp": summary, "calibration": summarize_calibration(cdf, tmp_path / "tables")}
    path = write_summary(tmp_path, parts, {"opencv": "test"})
    assert path.exists() and (tmp_path / "summary.json").exists()
