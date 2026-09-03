"""End-to-end smoke test of the library API: generate -> validate -> benchmark -> analyse -> card."""
import pandas as pd
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
    """The validator must reject a dataset whose noise does not match its metadata."""
    import shutil

    import h5py

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


@pytest.mark.parametrize("attack", ["reset_outliers", "manifest_fx", "pinhole_coeffs"])
def test_validation_detects_metadata_corruption(dataset, tmp_path, attack):
    """Corrupting metadata rather than geometry must still fail validation."""
    import shutil

    import h5py
    import pandas as pd

    root = tmp_path / attack
    shutil.copytree(dataset, root)
    shard = sorted((root / "hdf5").glob("*.h5"))[0]
    if attack == "manifest_fx":
        m = pd.read_parquet(root / "manifest.parquet")
        m.loc[0, "fx"] = 9999.0
        m.to_parquet(root / "manifest.parquet", index=False)
        m.to_csv(root / "manifest.csv", index=False)
    else:
        with h5py.File(shard, "r+") as fh:
            scene = fh[sorted(k for k in fh if k.startswith("scene_"))[0]]
            cam = scene[sorted(k for k in scene if k.startswith("camera_"))[0]]
            if attack == "pinhole_coeffs":
                if str(cam.attrs["distortion_model"]) != "pinhole":
                    pytest.skip("first camera is not pinhole in this dataset")
                coeffs = cam["dist_coeffs"][()]
                coeffs[0] = 0.01
                cam["dist_coeffs"][...] = coeffs
            else:
                clean = cam["points_2d_clean"][()]
                for name in cam:
                    if name.startswith("condition_") and cam[name]["outlier_mask"][()].any():
                        mask = cam[name]["outlier_mask"][()].astype(bool)
                        uv = cam[name]["points_2d"][()]
                        uv[mask] = clean[mask]          # outliers put back on their own points
                        cam[name]["points_2d"][...] = uv
                        break
                else:
                    pytest.skip("no outliers in this dataset")
    report = validate_dataset(root, regenerate=0, progress=False, log=None)
    assert not report["passed"], f"{attack} was not detected"


def test_zero_sigma_conditions_are_exact(dataset):
    """At sigma = 0 the observation is a deterministic function of the clean projection.

    Rounding error is not a random sample: the fractional parts of a projected
    grid are correlated, so the residual has a scene-dependent mean and variance
    and only an exact comparison is meaningful.
    """
    import h5py
    import numpy as np

    checked = 0
    for shard in sorted((dataset / "hdf5").glob("*.h5")):
        with h5py.File(shard, "r") as fh:
            for scene in (fh[k] for k in fh if k.startswith("scene_")):
                for cam in (scene[k] for k in scene if k.startswith("camera_")):
                    clean = cam["points_2d_clean"][()]
                    for cond in (cam[k] for k in cam if k.startswith("condition_")):
                        if float(cond.attrs["noise_sigma"]) != 0.0:
                            continue
                        inl = ~cond["outlier_mask"][()].astype(bool)
                        uv = cond["points_2d"][()]
                        want = np.round(clean[inl]) if bool(cond.attrs["quantize"]) else clean[inl]
                        assert np.array_equal(uv[inl], want)
                        checked += 1
    assert checked > 0


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
    assert "Aizierjiang Aiersilan" in card
    # The card must stand alone: it cites the Hub dataset and links no source
    # repository unless one is explicitly supplied.
    assert "huggingface.co/datasets/Ezharjan/PnPCorrespondences" in card
    assert "github" not in card.lower()
    linked = build_dataset_card(dataset, "Ezharjan/PnPCorrespondences",
                                code_url="https://example.org/src", doi="10.57967/hf/0000000")
    assert "[source](https://example.org/src)" in linked
    assert "doi          = {10.57967/hf/0000000}" in linked
    assert yaml.safe_load(linked.split("---", 2)[1])["license"] == "cc-by-4.0"


def test_exported_json_is_strict(dataset, tmp_path):
    """No NaN/Infinity literals: those are not JSON and break every strict parser."""
    import json

    def reject_constant(name):
        raise AssertionError(f"non-finite JSON literal: {name}")

    paths = export_examples(dataset, tmp_path / "ex", per_group=1, max_points=10)
    for path in list(paths) + [tmp_path / "ex" / "index.json",
                               dataset / "metadata" / "dataset_stats.json"]:
        with open(path, "r", encoding="utf-8") as fh:
            json.load(fh, parse_constant=reject_constant)
    payload = json.load(open(paths[0], "r", encoding="utf-8"))
    assert payload["camera"]["valid_radius"] is None or isinstance(payload["camera"]["valid_radius"], float)


def test_sweep_subsets_do_not_depend_on_the_solver_list(dataset):
    """--seed must fix the point subsets, whatever --solvers is set to."""
    manifest = load_manifest(dataset)
    subset = select_samples(manifest, max_samples=2, query="outlier_ratio == 0", seed=0)
    a = run_pnp_benchmark(dataset, subset, ["dlt_lm"], ["all", 8], seed=0, progress=False)
    b = run_pnp_benchmark(dataset, subset, ["ransac_dlt", "dlt_lm"], ["all", 8], seed=0, progress=False)
    cols = ["sample_id", "num_points_setting", "num_points_used", "rot_err_deg"]
    a = a[a.solver == "dlt_lm"][cols].reset_index(drop=True)
    b = b[b.solver == "dlt_lm"][cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)


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


def test_robust_solver_seed_does_not_depend_on_the_solver_list(dataset):
    """--solvers must not change the numbers a solver produces: a restricted run has
    to be directly comparable with a full one, seeds included."""
    manifest = load_manifest(dataset)
    subset = select_samples(manifest, max_samples=4, seed=0)
    full = run_pnp_benchmark(dataset, subset, ["ransac_dlt", "dlt_lm"], ["all"], seed=0, progress=False)
    solo = run_pnp_benchmark(dataset, subset, ["ransac_dlt"], ["all"], seed=0, progress=False)
    cols = ["sample_id", "rot_err_deg", "num_inliers_est", "trans_err_rel"]
    a = full[full.solver == "ransac_dlt"][cols].reset_index(drop=True)
    b = solo[solo.solver == "ransac_dlt"][cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)


def test_every_solver_is_scored_over_the_same_samples(dataset):
    """Domain-restricted solvers decline instead of being skipped, so `returned (%)`
    means the same thing for all of them."""
    manifest = load_manifest(dataset)
    subset = select_samples(manifest, max_samples=6, seed=0)
    solvers = ["dlt_lm"] + (["ippe", "sqpnp"] if HAVE_CV2 else [])
    df = run_pnp_benchmark(dataset, subset, solvers, ["all"], seed=0, progress=False)
    counts = df.groupby("solver").size()
    assert counts.nunique() == 1, counts.to_dict()
    if HAVE_CV2:
        ippe = df[df.solver == "ippe"]
        assert (ippe[~ippe["subset_planar"]]["failure_reason"].str.contains("coplanar")).all()
        assert ippe[ippe["subset_planar"]]["ok"].all()


def test_sample_reader_bounds_the_number_of_open_files(dataset):
    """A pass over a large tier must not accumulate HDF5 file caches."""
    from pnpcorr.storage import SampleReader

    manifest = load_manifest(dataset)
    with SampleReader(dataset, max_open=1, reopen_after=3) as reader:
        for _, row in manifest.iterrows():
            sample = reader.read(row)
            assert sample.num_visible > 0
            assert len(reader._files) <= 1
        files = list(reader._files.values())
        assert all(f for f in files)          # the surviving handle is still usable
    assert not reader._files
