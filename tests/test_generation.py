"""Scenes, poses, noise injection, HDF5 round trip and determinism."""
import numpy as np
import pytest

from pnpcorr.cameras import PINHOLE, Intrinsics, project_points
from pnpcorr.config import DEFAULTS, allocate_counts, expand_conditions, load_config, scene_specs
from pnpcorr.generate import generate_dataset, generate_scene_record
from pnpcorr.noise import apply_condition
from pnpcorr.poses import look_at_rotation, pose_matrix, sample_camera_pose
from pnpcorr.scenes import generate_scene, is_planar
from pnpcorr.storage import SampleReader, load_manifest, load_stats
from pnpcorr.validate import max_deviation_sigmas


def _cfg(scenes_per_type=1, intrinsics=1, poses=2):
    cfg = load_config()
    cfg["scenes"]["counts"] = {k: scenes_per_type for k in cfg["scenes"]["counts"]}
    cfg["cameras"]["num_intrinsics_per_scene"] = intrinsics
    cfg["cameras"]["num_poses_per_intrinsics"] = poses
    return cfg


# ----------------------------------------------------------------------------- scenes
@pytest.mark.parametrize("scene_type", ["planar_single", "planar_multi", "volumetric", "mixed", "depth_stratified"])
def test_scene_generation_properties(scene_type):
    rng = np.random.default_rng(7)
    scene = generate_scene(rng, scene_type, DEFAULTS)
    assert scene.points.shape == (scene.num_points, 3)
    assert scene.labels.shape == (scene.num_points,)
    assert np.isclose(np.linalg.norm(scene.front_axis), 1.0)
    assert np.allclose(scene.frame_R @ scene.frame_R.T, np.eye(3), atol=1e-12)
    if scene_type == "planar_single":
        assert is_planar(scene.points)
        assert (scene.labels == 0).all()
    else:
        assert not is_planar(scene.points)
    if scene_type == "planar_multi":
        n_planes = scene.params["num_planes"]
        assert 2 <= n_planes <= 4
        for k in range(n_planes):
            assert is_planar(scene.points[scene.labels == k])
    if scene_type == "mixed":
        assert is_planar(scene.points[scene.labels == 0])
        assert (scene.labels == -1).sum() == scene.num_points - (scene.labels == 0).sum()
    if scene_type == "depth_stratified":
        local = (scene.points - scene.frame_t) @ scene.frame_R
        lo, hi = DEFAULTS["scenes"]["depth_stratified"]["depth_range"]
        assert local[:, 2].min() >= lo - 1e-9 and local[:, 2].max() <= hi + 1e-9
        assert scene.pose_strategy == "corridor"


# ----------------------------------------------------------------------------- poses
def test_look_at_rotation_is_proper_and_points_at_target():
    R = look_at_rotation([1.0, 2.0, -3.0], [0.5, 0.0, 4.0], [0.0, 1.0, 0.0], roll_deg=20.0)
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-12)
    assert np.isclose(np.linalg.det(R), 1.0)
    C = np.array([1.0, 2.0, -3.0])
    T = np.array([0.5, 0.0, 4.0])
    tc = R @ (T - C)
    assert np.allclose(tc[:2], 0.0, atol=1e-12) and tc[2] > 0  # target on the optical axis


def test_look_at_handles_view_parallel_to_up():
    R = look_at_rotation([0.0, 5.0, 0.0], [0.0, 0.0, 0.0], [0.0, 1.0, 0.0])
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-12)


def test_hemisphere_pose_respects_elevation_and_frames_scene():
    rng = np.random.default_rng(11)
    scene = generate_scene(rng, "volumetric", DEFAULTS)
    K = np.array([[1000.0, 0, 640.0], [0, 1000.0, 360.0], [0, 0, 1]])
    intr = Intrinsics(PINHOLE, K, np.zeros(5), 1280, 720, hfov_deg=65.0, vfov_deg=39.6)
    for _ in range(50):
        R, t, C, info = sample_camera_pose(rng, scene, intr, DEFAULTS["poses"])
        assert info["elevation_deg"] >= DEFAULTS["poses"]["min_elevation_deg"] - 1e-9
        assert np.allclose(t, -R @ C)
        Rt = pose_matrix(R, t)
        pc = (Rt @ np.append(scene.center, 1.0))[:3]
        assert pc[2] > 0  # the scene center is in front of the camera
        proj = project_points(scene.points, intr, R, t)
        assert proj.uv.shape[0] >= 20


# ----------------------------------------------------------------------------- noise
def test_noise_conditions():
    rng = np.random.default_rng(3)
    uv = rng.uniform([0, 0], [1920, 1080], (1000, 2))
    clean = {"noise_sigma": 0.0, "quantize": False, "outlier_ratio": 0.0, "outlier_type": "uniform"}
    out, mask = apply_condition(rng, uv, clean, 1920, 1080)
    assert np.array_equal(out, uv) and not mask.any()

    sig = {"noise_sigma": 1.5, "quantize": False, "outlier_ratio": 0.0, "outlier_type": "uniform"}
    out, mask = apply_condition(np.random.default_rng(0), uv, sig, 1920, 1080)
    assert abs(np.std(out - uv) - 1.5) < 0.1

    quant = {"noise_sigma": 0.7, "quantize": True, "outlier_ratio": 0.0, "outlier_type": "uniform"}
    out, mask = apply_condition(rng, uv, quant, 1920, 1080)
    assert np.array_equal(out, np.round(out))

    uni = {"noise_sigma": 0.0, "quantize": False, "outlier_ratio": 0.2, "outlier_type": "uniform"}
    out, mask = apply_condition(rng, uv, uni, 1920, 1080)
    assert mask.sum() == 200
    assert np.array_equal(out[~mask], uv[~mask])
    assert (out[mask, 0] >= 0).all() and (out[mask, 0] < 1920).all()
    assert (out[mask, 1] >= 0).all() and (out[mask, 1] < 1080).all()

    swap = {"noise_sigma": 0.0, "quantize": False, "outlier_ratio": 0.5, "outlier_type": "swap"}
    out, mask = apply_condition(rng, uv, swap, 1920, 1080)
    assert mask.sum() == 500
    assert np.array_equal(out[~mask], uv[~mask])
    assert (np.abs(out[mask] - uv[mask]).sum(axis=1) > 0).all()  # every selected point moved
    # swapped observations are a permutation of the selected clean observations
    assert np.allclose(np.sort(out[mask], axis=0), np.sort(uv[mask], axis=0))

    mixed = {"noise_sigma": 0.0, "quantize": False, "outlier_ratio": 0.95, "outlier_type": "mixed"}
    out, mask = apply_condition(rng, uv, mixed, 1920, 1080)
    assert mask.sum() == 950 and (np.abs(out[mask] - uv[mask]).sum(axis=1) > 0).all()

    # a single "swap" outlier cannot be swapped and is replaced instead
    out, mask = apply_condition(rng, uv[:10], {"noise_sigma": 0.0, "quantize": False, "outlier_ratio": 0.1,
                                                "outlier_type": "swap"}, 1920, 1080)
    assert mask.sum() == 1 and (np.abs(out[mask] - uv[:10][mask]).sum() > 0)


def test_max_deviation_sigmas_is_a_valid_bound():
    # never below 6 sigma, grows like sqrt(2 ln N) and actually bounds the sample
    assert max_deviation_sigmas(1) >= 6.0
    assert max_deviation_sigmas(10 ** 6) > max_deviation_sigmas(10 ** 3) > 6.0
    for n in (10_000, 1_000_000):
        z = np.abs(np.random.default_rng(n).normal(size=n)).max()
        assert z < max_deviation_sigmas(n)


# ----------------------------------------------------------------------------- config
def test_condition_expansion_and_allocation():
    cfg = load_config()
    items = expand_conditions(cfg)
    assert len(items) == len(DEFAULTS["conditions"]["items"])
    cfg["conditions"]["mode"] = "factorial"
    fac = expand_conditions(cfg)
    assert len(fac) == 3 * 2 * (1 + 3 * 2)
    assert allocate_counts(6, [0.8, 0.1, 0.1]) == [4, 1, 1]
    assert allocate_counts(2, [0.8, 0.1, 0.1]) == [2, 0, 0]
    assert allocate_counts(100, [0.8, 0.1, 0.1]) == [80, 10, 10]
    specs = scene_specs(cfg)
    assert [s["scene_id"] for s in specs] == list(range(len(specs)))


# ----------------------------------------------------------------------------- storage / determinism
def test_generate_write_read_roundtrip(tmp_path):
    cfg = _cfg(scenes_per_type=1, intrinsics=1, poses=2)
    stats = generate_dataset(cfg, tmp_path, workers=1, progress=False, log=None)
    manifest = load_manifest(tmp_path)
    assert stats["num_samples"] == len(manifest) == stats["num_cameras"] * len(expand_conditions(cfg))
    assert set(manifest["scene_type"]) == set(cfg["scenes"]["counts"])
    assert load_stats(tmp_path)["num_scenes"] == 5
    with SampleReader(tmp_path) as reader:
        for _, row in manifest.sample(n=12, random_state=0).iterrows():
            s = reader.read(row)
            intr = s.intrinsics
            # stored clean projections are reproduced exactly from the ground truth
            proj = project_points(s.points_3d, intr, s.R, s.t, min_depth=cfg["cameras"]["min_depth"])
            assert np.array_equal(proj.indices, s.indices)
            assert np.allclose(proj.uv, s.uv_clean, atol=1e-9)
            assert np.allclose(proj.depth, s.depths)
            assert s.outlier_mask.sum() == int(row["num_outliers"]) == int(s.num_visible * row["outlier_ratio"])
            resid = s.uv[~s.outlier_mask] - s.uv_clean[~s.outlier_mask]
            atol = max_deviation_sigmas(resid.size) * row["noise_sigma"] + 0.5 + 1e-9
            assert np.allclose(resid, 0.0, atol=atol)
            assert np.isclose(np.linalg.det(s.R), 1.0)
            assert np.allclose(s.camera_center, -s.R.T @ s.t)
            assert row["camera_model"] == intr.model


def test_generation_is_deterministic_and_worker_independent(tmp_path):
    cfg = _cfg(scenes_per_type=1, intrinsics=1, poses=1)
    a = generate_scene_record(scene_specs(cfg)[2], cfg)
    b = generate_scene_record(scene_specs(cfg)[2], cfg)
    assert np.array_equal(a["points_3d"], b["points_3d"])
    assert np.array_equal(a["cameras"][0]["conditions"][3]["points_2d"], b["cameras"][0]["conditions"][3]["points_2d"])
    generate_dataset(cfg, tmp_path / "w1", workers=1, progress=False, log=None)
    generate_dataset(cfg, tmp_path / "w2", workers=2, progress=False, log=None)
    m1 = load_manifest(tmp_path / "w1")
    m2 = load_manifest(tmp_path / "w2")
    assert m1.drop(columns=[]).equals(m2)
    with SampleReader(tmp_path / "w1") as r1, SampleReader(tmp_path / "w2") as r2:
        s1 = r1.read(m1.iloc[-1])
        s2 = r2.read(m2.iloc[-1])
        assert np.array_equal(s1.uv, s2.uv) and np.array_equal(s1.points_3d, s2.points_3d)


# ----------------------------------------------------------------------------- config semantics
def test_yaml_restrictions_are_not_merged_back(tmp_path):
    """A YAML file that narrows a set of alternatives must win outright: merging the
    default back in would silently reinstate the models the user removed."""
    import yaml as _yaml

    path = tmp_path / "restricted.yaml"
    path.write_text(_yaml.safe_dump({
        "scenes": {"counts": {"volumetric": 4}},
        "cameras": {"model_probs": {"pinhole": 1.0},
                    "fov_class_probs": {"pinhole": {"normal": 1.0}}},
        "dataset": {"splits": {"train": 0.5, "test": 0.5}},
        "conditions": {"mode": "list",
                       "items": [{"noise_sigma": 0.5, "quantize": False,
                                  "outlier_ratio": 0.0, "outlier_type": "uniform"}]},
    }), encoding="utf-8")
    cfg = load_config(path)
    assert cfg["cameras"]["model_probs"] == {"pinhole": 1.0}
    assert cfg["cameras"]["fov_class_probs"] == {"pinhole": {"normal": 1.0}}
    assert cfg["scenes"]["counts"] == {"volumetric": 4}
    assert set(cfg["dataset"]["splits"]) == {"train", "test"}
    assert len(expand_conditions(cfg)) == 1
    # Lookup tables keyed by name stay merged: an unused entry changes nothing.
    assert set(cfg["cameras"]["fov_classes"]) == {"narrow", "normal", "wide", "fisheye"}


def test_config_used_yaml_round_trips(tmp_path):
    """`metadata/config_used.yaml` is the reproducibility record, so re-loading it
    must give back exactly the configuration that produced the dataset."""
    from pnpcorr.config import config_to_yaml

    cfg = _cfg(scenes_per_type=1, intrinsics=1, poses=1)
    cfg["cameras"]["model_probs"] = {"brown_conrady": 1.0}
    cfg["cameras"]["fov_class_probs"] = {"brown_conrady": {"normal": 1.0}}
    generate_dataset(cfg, tmp_path, workers=1, progress=False, log=None)
    reloaded = load_config(tmp_path / "metadata" / "config_used.yaml")
    assert reloaded == cfg
    assert _yaml_roundtrip(cfg) == cfg


def _yaml_roundtrip(cfg):
    import yaml as _yaml

    from pnpcorr.config import config_to_yaml

    return _yaml.safe_load(config_to_yaml(cfg))


def test_num_outliers_is_the_exact_floor():
    """`int(m * ratio)` is not floor(m*ratio) for every ratio; the generator and the
    validator must agree on one definition."""
    from fractions import Fraction

    from pnpcorr.noise import num_outliers

    for ratio in (0.05, 0.2, 0.29, 0.5, 0.7, 0.8, 0.95):
        exact = Fraction(str(ratio))
        for m in range(1, 3000):
            assert num_outliers(m, ratio) == (m * exact).__floor__(), (m, ratio)
