"""
Evaluation metrics (README Section 9.3).

* Rotation error      angle of R_est^T R_gt in degrees.
* Translation error   ||t_est - t_gt||  (scene units, meters) and the same value
                      divided by the mean depth of the ground-truth inliers
                      (a scale-free relative error that is well defined even when
                      the camera sits close to the world origin).
* Camera-center error ||C_est - C_gt|| with C = -R^T t.
* Reprojection RMSE   RMS Euclidean distance between the *clean* ground-truth 2D
                      points and the 3D points projected with the estimated
                      parameters (ground-truth intrinsics/distortion for
                      calibrated PnP, estimated K for uncalibrated DLT),
                      evaluated on the ground-truth inlier correspondences.
* Intrinsic error     percentage error of fx, fy, cx, cy and absolute skew error.
* Inlier classification precision / recall / F1 of an estimated inlier mask
                      against the ground-truth inlier mask.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np

from .cameras import Intrinsics, project_pinhole, project_points_all


def rotation_error_deg(R_est: np.ndarray, R_gt: np.ndarray) -> float:
    """Geodesic angle between two rotations, accurate down to ~1e-14 degrees
    (atan2 of the sine, from the skew part, and the cosine, from the trace)."""
    R_rel = np.asarray(R_est).T @ np.asarray(R_gt)
    cos = (np.trace(R_rel) - 1.0) / 2.0
    sin = np.linalg.norm(R_rel - R_rel.T) / (2.0 * math.sqrt(2.0))
    return float(math.degrees(math.atan2(sin, cos)))


def translation_error(t_est: np.ndarray, t_gt: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(t_est).ravel() - np.asarray(t_gt).ravel()))


def camera_center(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    return -np.asarray(R).T @ np.asarray(t).ravel()


def reprojection_rmse(points_3d: np.ndarray, uv_clean: np.ndarray, intr: Intrinsics, R: np.ndarray,
                      t: np.ndarray, mask: Optional[np.ndarray] = None) -> float:
    """RMSE between clean GT observations and the projection with (R, t) through
    the ground-truth camera model.  NaN when a point falls behind the estimated
    camera or outside the invertible domain of its distortion polynomial."""
    if mask is not None:
        points_3d, uv_clean = points_3d[mask], uv_clean[mask]
    if len(points_3d) == 0:
        return float("nan")
    uv, _ = project_points_all(points_3d, intr, R, t)
    if not np.isfinite(uv).all():
        return float("nan")
    return float(np.sqrt(np.mean(np.sum((uv - uv_clean) ** 2, axis=1))))


def reprojection_rmse_pinhole(points_3d: np.ndarray, uv_clean: np.ndarray, K: np.ndarray, R: np.ndarray,
                              t: np.ndarray, mask: Optional[np.ndarray] = None) -> float:
    """RMSE for an estimated *pinhole* camera (uncalibrated DLT benchmarks)."""
    if mask is not None:
        points_3d, uv_clean = points_3d[mask], uv_clean[mask]
    if len(points_3d) == 0:
        return float("nan")
    uv, z = project_pinhole(points_3d, K, R, t)
    if (z <= 0).any() or not np.isfinite(uv).all():
        return float("nan")
    return float(np.sqrt(np.mean(np.sum((uv - uv_clean) ** 2, axis=1))))


def intrinsic_errors(K_est: np.ndarray, K_gt: np.ndarray) -> Dict[str, float]:
    return {
        "fx_err_pct": float(abs(K_est[0, 0] - K_gt[0, 0]) / abs(K_gt[0, 0]) * 100.0),
        "fy_err_pct": float(abs(K_est[1, 1] - K_gt[1, 1]) / abs(K_gt[1, 1]) * 100.0),
        "cx_err_pct": float(abs(K_est[0, 2] - K_gt[0, 2]) / abs(K_gt[0, 2]) * 100.0),
        "cy_err_pct": float(abs(K_est[1, 2] - K_gt[1, 2]) / abs(K_gt[1, 2]) * 100.0),
        "cx_err_px": float(abs(K_est[0, 2] - K_gt[0, 2])),
        "cy_err_px": float(abs(K_est[1, 2] - K_gt[1, 2])),
        "skew_err_px": float(abs(K_est[0, 1] - K_gt[0, 1])),
    }


def inlier_classification(est_inliers: Optional[np.ndarray], gt_outlier_mask: np.ndarray) -> Dict[str, float]:
    gt_inl = ~np.asarray(gt_outlier_mask, dtype=bool)
    if est_inliers is None:
        return {"inlier_precision": float("nan"), "inlier_recall": float("nan"), "inlier_f1": float("nan"),
                "num_inliers_est": float("nan")}
    est = np.asarray(est_inliers, dtype=bool)
    tp = float(np.sum(est & gt_inl))
    fp = float(np.sum(est & ~gt_inl))
    fn = float(np.sum(~est & gt_inl))
    precision = tp / (tp + fp) if tp + fp > 0 else 0.0
    recall = tp / (tp + fn) if tp + fn > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
    return {"inlier_precision": precision, "inlier_recall": recall, "inlier_f1": f1,
            "num_inliers_est": float(est.sum())}


def pose_metrics(R_est: np.ndarray, t_est: np.ndarray, R_gt: np.ndarray, t_gt: np.ndarray,
                 depth_scale: float) -> Dict[str, Any]:
    t_err = translation_error(t_est, t_gt)
    return {
        "rot_err_deg": rotation_error_deg(R_est, R_gt),
        "trans_err": t_err,
        "trans_err_rel": t_err / depth_scale if depth_scale > 0 else float("nan"),
        "center_err": float(np.linalg.norm(camera_center(R_est, t_est) - camera_center(R_gt, t_gt))),
    }


def is_success(rot_err_deg: float, trans_err_rel: float, rot_thr: float = 5.0, trans_thr: float = 0.05) -> bool:
    return bool(np.isfinite(rot_err_deg) and np.isfinite(trans_err_rel)
                and rot_err_deg <= rot_thr and trans_err_rel <= trans_thr)
