"""Projection and distortion checks against OpenCV and analytic properties."""
import math

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from pnpcorr.cameras import (
    BROWN_CONRADY, KANNALA_BRANDT, PINHOLE, Intrinsics, brown_valid_radius, corner_radius,
    distort_points, in_valid_domain, kb_valid_theta, normalized_from_pixel, pixel_from_normalized,
    project_points, project_points_all, sample_intrinsics, undistort_points, undistort_to_pinhole_pixels,
)
from pnpcorr.config import DEFAULTS

cv2 = pytest.importorskip("cv2")


def _random_points(rng, n=500):
    pts = rng.uniform(-2.0, 2.0, (n, 3))
    pts[:, 2] += 6.0
    return pts


def _pose():
    R = Rotation.from_euler("xyz", [8.0, -12.0, 4.0], degrees=True).as_matrix()
    t = np.array([0.3, -0.2, 0.4])
    return R, t


def test_brown_conrady_matches_opencv():
    rng = np.random.default_rng(0)
    K = np.array([[1400.0, 0.0, 960.0], [0.0, 1380.0, 540.0], [0.0, 0.0, 1.0]])
    coeffs = np.array([0.12, -0.05, 0.0015, -0.0008, 0.01])
    R, t = _pose()
    pts = _random_points(rng)
    intr = Intrinsics(BROWN_CONRADY, K, coeffs, 1920, 1080, valid_radius=brown_valid_radius(coeffs))
    uv_all, _ = project_points_all(pts, intr, R, t)
    rvec, _ = cv2.Rodrigues(R)
    uv_cv, _ = cv2.projectPoints(pts, rvec, t, K, coeffs)
    assert np.allclose(uv_all, uv_cv.reshape(-1, 2), atol=1e-8)


def test_kannala_brandt_matches_opencv():
    rng = np.random.default_rng(1)
    K = np.array([[600.0, 0.0, 640.0], [0.0, 610.0, 360.0], [0.0, 0.0, 1.0]])
    coeffs = np.array([0.05, -0.02, 0.004, -0.001])
    R, t = _pose()
    pts = _random_points(rng)
    intr = Intrinsics(KANNALA_BRANDT, K, coeffs, 1280, 720, valid_radius=kb_valid_theta(coeffs))
    uv_all, _ = project_points_all(pts, intr, R, t)
    rvec, _ = cv2.Rodrigues(R)
    uv_cv, _ = cv2.fisheye.projectPoints(pts.reshape(1, -1, 3), rvec, t, K, coeffs)
    assert np.allclose(uv_all, uv_cv.reshape(-1, 2), atol=1e-8)


def test_skew_is_applied_to_u_only():
    K = np.array([[1000.0, 3.0, 500.0], [0.0, 1000.0, 400.0], [0.0, 0.0, 1.0]])
    u, v = pixel_from_normalized(np.array([0.1]), np.array([0.2]), K)
    assert np.isclose(u[0], 1000 * 0.1 + 3.0 * 0.2 + 500)
    assert np.isclose(v[0], 1000 * 0.2 + 400)
    xd, yd = normalized_from_pixel(u, v, K)
    assert np.isclose(xd[0], 0.1) and np.isclose(yd[0], 0.2)


@pytest.mark.parametrize("model", [PINHOLE, BROWN_CONRADY, KANNALA_BRANDT])
def test_distortion_round_trip(model):
    rng = np.random.default_rng(2)
    if model == BROWN_CONRADY:
        coeffs = np.array([-0.25, 0.08, 0.002, -0.001, -0.01])
        valid = brown_valid_radius(coeffs)
        r = rng.uniform(0.0, min(valid, 1.2) * 0.999, 2000)
    elif model == KANNALA_BRANDT:
        coeffs = np.array([-0.04, 0.02, -0.005, 0.001])
        valid = kb_valid_theta(coeffs)
        theta = rng.uniform(0.0, min(valid, 1.45), 2000)
        r = np.tan(theta)
    else:
        coeffs = np.zeros(5)
        valid = float("inf")
        r = rng.uniform(0.0, 3.0, 2000)
    ang = rng.uniform(0.0, 2 * math.pi, 2000)
    xn, yn = r * np.cos(ang), r * np.sin(ang)
    xn[0], yn[0] = 0.0, 0.0  # exercise the r = 0 limit
    xd, yd = distort_points(xn, yn, model, coeffs)
    xb, yb, ok = undistort_points(xd, yd, model, coeffs, valid)
    assert ok.all()
    assert np.max(np.hypot(xb - xn, yb - yn)) < 1e-9


def test_undistort_flags_points_outside_domain():
    coeffs = np.array([-0.30, 0.0, 0.0, 0.0, 0.0])  # folds at r = 1/sqrt(0.9)
    valid = brown_valid_radius(coeffs)
    assert np.isclose(valid, 1.0 / math.sqrt(0.9))
    r_fold = valid * (1 + 0.3 * -valid ** 2)  # r_d at the fold
    xd = np.array([r_fold * 1.5, 0.1])
    yd = np.zeros(2)
    _, _, ok = undistort_points(xd, yd, BROWN_CONRADY, coeffs, valid)
    assert ok.tolist() == [False, True]


def test_brown_domain_accounts_for_tangential_folding():
    """The radial monotonicity limit is not the injectivity limit when p1/p2 != 0."""
    from pnpcorr.cameras import brown_radial_valid_radius, _brown_jacobian_det

    # radially monotonic everywhere, yet the tangential terms fold the map at r ~ 0.66
    coeffs = np.array([-0.50891128, -1.00575878, -0.01445084, 0.01590187, 1.20685218])
    assert brown_radial_valid_radius(coeffs) == float("inf")
    valid = brown_valid_radius(coeffs)
    assert 0.6 < valid < 0.7
    # no fold strictly inside the domain, and a fold immediately outside it
    th = np.linspace(0, 2 * math.pi, 720, endpoint=False)
    r_in = np.linspace(1e-6, valid * 0.999, 400)
    det_in = _brown_jacobian_det(r_in[:, None] * np.cos(th), r_in[:, None] * np.sin(th), coeffs)
    assert (det_in > 0).all()
    r_out = np.linspace(valid * 1.001, valid * 1.2, 200)
    det_out = _brown_jacobian_det(r_out[:, None] * np.cos(th), r_out[:, None] * np.sin(th), coeffs)
    assert (det_out <= 0).any()
    # a point beyond the fold lies outside the domain and is therefore not projected
    K = np.array([[4556.62, 0.0, 1920.0], [0.0, 4556.62, 1080.0], [0.0, 0.0, 1.0]])
    intr = Intrinsics(BROWN_CONRADY, K, coeffs, 3840, 2160, valid_radius=valid)
    assert not in_valid_domain(np.array([-0.678467]), np.array([0.436572]), intr)[0]


def test_purely_radial_distortion_keeps_the_analytic_limit():
    coeffs = np.array([-0.30, 0.0, 0.0, 0.0, 0.0])          # p1 = p2 = 0
    from pnpcorr.cameras import brown_radial_valid_radius
    assert np.isclose(brown_valid_radius(coeffs), brown_radial_valid_radius(coeffs))
    assert np.isclose(brown_valid_radius(coeffs), 1.0 / math.sqrt(0.9))


def test_sampled_intrinsics_have_injective_domains():
    from pnpcorr.cameras import _brown_jacobian_det

    rng = np.random.default_rng(3)
    th = np.linspace(0, 2 * math.pi, 512, endpoint=False)
    checked = 0
    for _ in range(120):
        intr = sample_intrinsics(rng, DEFAULTS["cameras"])
        if intr.model != BROWN_CONRADY:
            continue
        checked += 1
        r = np.linspace(1e-6, intr.valid_radius * 0.999, 400)
        det = _brown_jacobian_det(r[:, None] * np.cos(th), r[:, None] * np.sin(th), intr.coeffs)
        assert (det > 0).all(), "the sampled domain contains a fold"
    assert checked > 10


def test_kb_valid_theta_never_exceeds_half_pi():
    assert kb_valid_theta(np.zeros(4)) == pytest.approx(math.pi / 2)
    assert kb_valid_theta(np.array([-0.5, 0, 0, 0])) < math.pi / 2


def test_projection_culls_behind_camera_and_outside_image():
    K = np.array([[800.0, 0.0, 320.0], [0.0, 800.0, 240.0], [0.0, 0.0, 1.0]])
    intr = Intrinsics(PINHOLE, K, np.zeros(5), 640, 480)
    pts = np.array([
        [0.0, 0.0, 5.0],      # visible, projects to the principal point
        [0.0, 0.0, -5.0],     # behind the camera
        [10.0, 0.0, 5.0],     # outside the sensor (u = 320 + 1600)
        [0.0, 0.0, 0.0],      # z = 0: culled
        [0.05, -0.05, 1.0],   # visible
    ])
    proj = project_points(pts, intr, np.eye(3), np.zeros(3))
    assert proj.indices.tolist() == [0, 4]
    assert np.allclose(proj.uv[0], [320.0, 240.0])
    assert np.allclose(proj.depth, [5.0, 1.0])
    # half-open bounds: u == W is outside
    pts2 = np.array([[(640.0 - 320.0) / 800.0, 0.0, 1.0]])
    assert project_points(pts2, intr, np.eye(3), np.zeros(3)).uv.shape[0] == 0
    pts3 = np.array([[(639.999 - 320.0) / 800.0, 0.0, 1.0]])
    assert project_points(pts3, intr, np.eye(3), np.zeros(3)).uv.shape[0] == 1


def test_project_points_all_marks_invalid_with_nan():
    K = np.array([[800.0, 0.0, 320.0], [0.0, 800.0, 240.0], [0.0, 0.0, 1.0]])
    intr = Intrinsics(PINHOLE, K, np.zeros(5), 640, 480)
    uv, depth = project_points_all(np.array([[0.0, 0.0, 2.0], [0.0, 0.0, -2.0]]), intr, np.eye(3), np.zeros(3))
    assert np.allclose(uv[0], [320.0, 240.0]) and np.isnan(uv[1]).all()
    assert depth.tolist() == [2.0, -2.0]


def test_undistort_to_pinhole_pixels_inverts_projection():
    rng = np.random.default_rng(3)
    K = np.array([[1400.0, 1.5, 960.0], [0.0, 1380.0, 540.0], [0.0, 0.0, 1.0]])
    coeffs = np.array([-0.2, 0.05, 0.001, -0.002, 0.0])
    intr = Intrinsics(BROWN_CONRADY, K, coeffs, 1920, 1080, valid_radius=brown_valid_radius(coeffs))
    R, t = _pose()
    pts = _random_points(rng)
    proj = project_points(pts, intr, R, t)
    pin = Intrinsics(PINHOLE, K, np.zeros(5), 1920, 1080)
    uv_pin, _ = project_points_all(pts[proj.indices], pin, R, t)
    uv_und, ok = undistort_to_pinhole_pixels(proj.uv, intr)
    assert ok.all()
    assert np.max(np.abs(uv_und - uv_pin)) < 1e-6


def test_sample_intrinsics_consistency():
    rng = np.random.default_rng(4)
    cam_cfg = DEFAULTS["cameras"]
    seen = set()
    for _ in range(300):
        intr = sample_intrinsics(rng, cam_cfg)
        seen.add(intr.model)
        assert intr.coeffs.shape[0] == (4 if intr.model == KANNALA_BRANDT else 5)
        assert intr.width > 0 and intr.height > 0
        assert 0 < intr.hfov_deg < 180
        half = math.radians(intr.hfov_deg) / 2
        if intr.model == KANNALA_BRANDT:
            assert np.isclose(intr.fx, (intr.width / 2) / half)
        else:
            assert np.isclose(intr.fx, (intr.width / 2) / math.tan(half))
        assert abs(intr.fy / intr.fx - 1.0) <= 0.1 + 1e-12
        # the invertible domain covers at least 80 % of the corner radius
        r_c = corner_radius(intr.K, intr.width, intr.height)
        if intr.model == BROWN_CONRADY:
            assert intr.valid_radius >= 0.8 * r_c - 1e-12
        elif intr.model == KANNALA_BRANDT:
            assert intr.valid_radius >= min(0.8 * r_c, math.pi / 2) - 1e-12
        if intr.fov_class == "narrow" and intr.model != PINHOLE:
            assert intr.distortion_level == "mild"
    assert seen == {PINHOLE, BROWN_CONRADY, KANNALA_BRANDT}
