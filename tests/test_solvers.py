"""Solver correctness on synthetic ground truth."""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from pnpcorr import solvers
from pnpcorr.cameras import PINHOLE, Intrinsics, project_pinhole
from pnpcorr.metrics import (inlier_classification, intrinsic_errors, reprojection_rmse,
                             rotation_error_deg, translation_error)

K = np.array([[1500.0, 0.0, 960.0], [0.0, 1480.0, 540.0], [0.0, 0.0, 1.0]])
R_GT = Rotation.from_euler("xyz", [12.0, -20.0, 7.0], degrees=True).as_matrix()
T_GT = np.array([0.4, -0.3, 0.8])


def _scene(n=80, planar=False, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.uniform(-2.0, 2.0, (n, 3))
    X[:, 2] += 7.0
    if planar:
        # tilted plane through (0, 0, 7)
        Rp = Rotation.from_euler("xyz", [25.0, -15.0, 40.0], degrees=True).as_matrix()
        X = (X - [0, 0, 7.0]) * [1, 1, 0] @ Rp.T + [0.3, -0.1, 7.0]
    uv, z = project_pinhole(X, K, R_GT, T_GT)
    assert (z > 0).all()
    return X, uv


def _check(est, tol_rot=1e-5, tol_t=1e-4):
    assert est.ok, est.reason
    assert rotation_error_deg(est.R, R_GT) < tol_rot
    assert translation_error(est.t, T_GT) < tol_t


@pytest.mark.parametrize("name", ["dlt", "dlt_lm", "epnp", "epnp_lm", "iterative", "sqpnp"])
def test_nonplanar_solvers_recover_exact_pose(name):
    spec = solvers.SOLVERS[name]
    if spec.needs_cv2 and not solvers.HAVE_CV2:
        pytest.skip("opencv missing")
    X, uv = _scene()
    _check(spec.fn(X, uv, K))


@pytest.mark.parametrize("name", ["p3p", "ap3p", "sqpnp"])
def test_minimal_solvers_with_four_points(name):
    if not solvers.HAVE_CV2:
        pytest.skip("opencv missing")
    X, uv = _scene(n=4, seed=3)
    _check(solvers.SOLVERS[name].fn(X, uv, K), tol_rot=1e-4, tol_t=1e-3)


def test_planar_degeneracy_is_detected_and_planar_solvers_work():
    X, uv = _scene(planar=True)
    est = solvers.dlt_calibrated(X, uv, K)
    assert not est.ok and "coplanar" in est.reason
    assert not solvers.dlt_uncalibrated(X, uv).ok
    if solvers.HAVE_CV2:
        _check(solvers.solve_ippe(X, uv, K), tol_rot=1e-5, tol_t=1e-4)
        _check(solvers.solve_epnp(X, uv, K), tol_rot=1e-4, tol_t=1e-3)
        _check(solvers.solve_sqpnp(X, uv, K), tol_rot=1e-5, tol_t=1e-4)
        _check(solvers.solve_iterative(X, uv, K), tol_rot=1e-5, tol_t=1e-4)
        assert not solvers.solve_ippe(_scene()[0], _scene()[1], K).ok  # refuses non-planar input


def test_ippe_on_axis_aligned_offset_plane():
    """The case where OpenCV's own canonicalisation fails."""
    if not solvers.HAVE_CV2:
        pytest.skip("opencv missing")
    rng = np.random.default_rng(5)
    X = rng.uniform(-2, 2, (50, 3))
    X[:, 2] = 6.0
    uv, _ = project_pinhole(X, K, R_GT, T_GT)
    _check(solvers.solve_ippe(X, uv, K), tol_rot=1e-6, tol_t=1e-5)


@pytest.mark.parametrize("name", ["ransac_dlt", "ransac_p3p", "cv_ransac_epnp", "cv_ransac_epnp_lm",
                                  "cv_ransac_ap3p", "cv_usac_magsac"])
def test_robust_solvers_survive_outliers(name):
    spec = solvers.SOLVERS[name]
    if spec.needs_cv2 and not solvers.HAVE_CV2:
        pytest.skip("opencv missing")
    X, uv = _scene(n=200, seed=1)
    rng = np.random.default_rng(2)
    uv_noisy = uv + rng.normal(0, 0.5, uv.shape)
    out = np.zeros(200, dtype=bool)
    out[rng.choice(200, 100, replace=False)] = True
    uv_noisy[out] = rng.uniform([0, 0], [1920, 1080], (100, 2))
    est = spec.fn(X, uv_noisy, K, threshold=3.0, max_iters=2000, confidence=0.999, seed=0)
    assert est.ok, est.reason
    assert rotation_error_deg(est.R, R_GT) < 0.2
    assert translation_error(est.t, T_GT) < 0.02
    cls = inlier_classification(est.inliers, out)
    assert cls["inlier_precision"] > 0.95 and cls["inlier_recall"] > 0.9


def test_uncalibrated_dlt_recovers_intrinsics():
    Ks = np.array([[1500.0, 2.0, 950.0], [0.0, 1470.0, 530.0], [0.0, 0.0, 1.0]])
    rng = np.random.default_rng(9)
    X = rng.uniform(-2.0, 2.0, (120, 3))
    X[:, 2] += 7.0
    uv, _ = project_pinhole(X, Ks, R_GT, T_GT)
    est = solvers.dlt_uncalibrated(X, uv)
    assert est.ok, est.reason
    assert np.allclose(est.K, Ks, atol=1e-6)
    _check(est, tol_rot=1e-6, tol_t=1e-6)
    errs = intrinsic_errors(est.K, Ks)
    assert errs["fx_err_pct"] < 1e-8 and errs["skew_err_px"] < 1e-6
    # LM refinement with noise improves (or keeps) the fit
    uv_n = uv + rng.normal(0, 1.0, uv.shape)
    lin = solvers.dlt_uncalibrated(X, uv_n)
    ref = solvers.dlt_uncalibrated_lm(X, uv_n)
    assert ref.ok and lin.ok
    r_lin = np.sqrt(np.mean(np.sum((project_pinhole(X, lin.K, lin.R, lin.t)[0] - uv_n) ** 2, axis=1)))
    r_ref = np.sqrt(np.mean(np.sum((project_pinhole(X, ref.K, ref.R, ref.t)[0] - uv_n) ** 2, axis=1)))
    assert r_ref <= r_lin + 1e-9


def test_multiview_calibration():
    if not solvers.HAVE_CV2:
        pytest.skip("opencv missing")
    import cv2
    rng = np.random.default_rng(4)
    X = rng.uniform(-2.0, 2.0, (150, 3))
    X[:, 2] += 7.0
    dist = np.array([0.08, -0.02, 0.001, -0.0005, 0.0])
    views = []
    for i in range(6):
        R = Rotation.from_euler("xyz", rng.uniform(-20, 20, 3), degrees=True).as_matrix()
        t = T_GT + rng.uniform(-0.5, 0.5, 3)
        rvec, _ = cv2.Rodrigues(R)
        uv, _ = cv2.projectPoints(X, rvec, t, K, dist)
        views.append((X, uv.reshape(-1, 2)))
    K0 = K.copy()
    K0[0, 0] *= 1.08
    K0[1, 1] *= 0.95
    K0[0, 2] += 20
    est = solvers.calibrate_multiview(views, (1920, 1080), K0, "brown_conrady")
    assert est.ok, est.reason
    assert np.allclose(est.K, K, atol=1e-3)
    assert np.allclose(est.dist, dist, atol=1e-5)


def test_fisheye_flags_resolve_on_any_opencv_version():
    """OpenCV 4.x has cv2.fisheye.CALIB_*, OpenCV 5.x has cv2.CALIB_* - both must work."""
    if not solvers.HAVE_CV2:
        pytest.skip("opencv missing")
    for name in ("CALIB_USE_INTRINSIC_GUESS", "CALIB_FIX_SKEW", "CALIB_RECOMPUTE_EXTRINSIC"):
        assert isinstance(solvers._fisheye_flag(name), int)
    with pytest.raises(AttributeError):
        solvers._fisheye_flag("CALIB_THIS_FLAG_DOES_NOT_EXIST")


def test_fisheye_multiview_calibration():
    if not solvers.HAVE_CV2:
        pytest.skip("opencv missing")
    from pnpcorr.cameras import KANNALA_BRANDT, Intrinsics, kb_valid_theta, project_points_all

    Kf = np.array([[420.0, 0.0, 640.0], [0.0, 418.0, 360.0], [0.0, 0.0, 1.0]])
    dist = np.array([0.03, -0.01, 0.002, -0.0005])
    rng = np.random.default_rng(0)
    X = rng.uniform(-2.0, 2.0, (200, 3))
    X[:, 2] += 6.0
    intr = Intrinsics(KANNALA_BRANDT, Kf, dist, 1280, 720, valid_radius=kb_valid_theta(dist))
    views = []
    for _ in range(6):
        R = Rotation.from_euler("xyz", rng.uniform(-15, 15, 3), degrees=True).as_matrix()
        t = np.array([0.2, -0.1, 0.5]) + rng.uniform(-0.3, 0.3, 3)
        uv, _ = project_points_all(X, intr, R, t)
        assert np.isfinite(uv).all()
        views.append((X, uv))
    K0 = Kf.copy()
    K0[0, 0] *= 1.05
    K0[1, 1] *= 0.97
    K0[0, 2] += 10
    for est in (solvers.calibrate_multiview(views, (1280, 720), K0, "kannala_brandt"),
                solvers.calibrate_multiview_ba(views, (1280, 720), K0, "kannala_brandt")):
        assert est.ok, est.reason
        assert np.allclose(est.K, Kf, atol=1e-4)
        assert np.allclose(np.asarray(est.dist)[:4], dist, atol=1e-6)


def test_metrics_basic():
    assert rotation_error_deg(np.eye(3), np.eye(3)) == 0.0
    Rz = Rotation.from_euler("z", 30, degrees=True).as_matrix()
    assert abs(rotation_error_deg(Rz, np.eye(3)) - 30.0) < 1e-9
    intr = Intrinsics(PINHOLE, K, np.zeros(5), 1920, 1080)
    X, uv = _scene()
    assert reprojection_rmse(X, uv, intr, R_GT, T_GT) < 1e-9
    assert np.isnan(reprojection_rmse(X, uv, intr, R_GT, T_GT + [0, 0, -50.0]))
