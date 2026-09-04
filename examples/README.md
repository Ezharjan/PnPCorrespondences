# Worked examples

Ten self-contained scripts, in the order they are worth reading. Each one runs on
its own, prints a table and explains what the table means; together they cover the
whole surface of the project — the file format, the camera models, the noise design,
the solvers, the calibration tasks, training protocols, adding an estimator of your
own and building a tier of your own.

Every script takes `--help`, and the eight that read a dataset take `--data DIR`
(default `data`); `02` samples its own cameras and `08` generates its own tier.
Anything that reads a dataset works with the `smoke` tier, except `05`, which needs at
least three outlier ratios for a breakdown curve and stops with a message on a tier
that has fewer — the `small` tier and larger provide six.

```bash
python scripts/run_pipeline.py --config configs/smoke.yaml --out-root runs/smoke --workers 2
python examples/quickstart.py --data runs/smoke/data
```

| script | what it shows | needs a dataset |
|---|---|---|
| [`quickstart.py`](quickstart.py) | open one sample, solve it with several solvers, read the errors | yes |
| [`01_read_with_h5py_only.py`](01_read_with_h5py_only.py) | read the dataset with h5py and pandas alone, and re-derive the stored projections from the ground truth in twenty lines of NumPy | yes |
| [`02_camera_models_and_distortion.py`](02_camera_models_and_distortion.py) | the three lens models side by side: forward distortion, its inverse, the injective domain, agreement with OpenCV | no |
| [`03_noise_conditions.py`](03_noise_conditions.py) | all noise conditions of a single view — one controlled experiment on one geometry — against the model of README Section 5.6 | yes |
| [`04_compare_solvers.py`](04_compare_solvers.py) | a miniature benchmark: every solver over a stratified subset, one table, including why each one declined | yes |
| [`05_robustness_to_outliers.py`](05_robustness_to_outliers.py) | the breakdown point of the robust estimators across the outlier sweep, with inlier precision and recall | `small` or larger (≥ 3 outlier ratios) |
| [`06_multiview_calibration.py`](06_multiview_calibration.py) | recover intrinsics and lens distortion from the views that share a camera, at two noise levels, OpenCV against the from-scratch bundle adjustment | yes, with ≥ 3 poses per intrinsic set |
| [`07_training_dataloader.py`](07_training_dataloader.py) | fixed-size normalised batches for a learned solver, respecting the scene-level splits; optional PyTorch wrapper | yes |
| [`08_custom_tier.py`](08_custom_tier.py) | design a tier in Python, generate it, validate it, report its composition | writes its own |
| [`09_bring_your_own_solver.py`](09_bring_your_own_solver.py) | write a solver, register it, and have the real benchmark score it beside the shipped ones | yes |

`data/examples/*.json`, written by `scripts/export_examples.py`, is a different
thing: a handful of samples in strict JSON for inspection without any tooling.
