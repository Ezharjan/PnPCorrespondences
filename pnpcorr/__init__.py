"""
pnpcorr - synthetic 2D-3D point-correspondence datasets for camera calibration
and Perspective-n-Point (PnP) benchmarking.

The package implements the methodology documented in Section 5 of the project
README (*Method and dataset design*):

* forward projection through pinhole, Brown-Conrady and Kannala-Brandt cameras,
* structured 3D scenes (planar targets, room corners, volumes, mixed, depth-stratified),
* look-at camera poses sampled on a hemisphere (or along a corridor),
* frustum culling and sensor-bounds checking,
* Gaussian pixel noise, quantization and outlier injection (uniform / swap / mixed),
* an HDF5 serialization with a per-sample manifest,
* PnP / calibration solvers, evaluation metrics, benchmark tooling and figures.
"""

from ._version import __version__, FORMAT_VERSION  # noqa: F401

from .cameras import (  # noqa: F401
    Intrinsics,
    distort_points,
    undistort_points,
    project_points,
    project_points_all,
    sample_intrinsics,
)
from .scenes import Scene, generate_scene  # noqa: F401
from .poses import look_at_rotation, sample_camera_pose  # noqa: F401
from .noise import apply_condition, condition_name  # noqa: F401
from .storage import DatasetWriter, load_manifest, read_sample, Sample  # noqa: F401
