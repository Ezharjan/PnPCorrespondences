# Benchmark summary

Environment: pnpcorr_version=1.0.0, python=3.11.15, platform=Linux-6.18.44-fc-v24-x86_64-with-glibc2.39, processor=x86_64, numpy=2.4.6, scipy=1.17.1, pandas=3.0.5, h5py=3.16.0, opencv=5.0.0

## Calibrated PnP

### Solver overview - all conditions

Success = rotation error <= 5 deg and relative translation error <= 5 %. Errors are medians over every evaluated sample (all visible correspondences).

| solver | family | solves | returned (%) | success (%) | success when returned (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 600 | 82.2 | 39.3 | 47.9 | 4.661 | 43.5 | 0.060 | 0.422 | 1.592 |
| dlt_lm | classic | 600 | 82.2 | 43.7 | 53.1 | 0.685 | 38.3 | 0.024 | 0.058 | 7.955 |
| epnp | opencv | 600 | 100.0 | 45.2 | 45.2 | 3.430 | 40.2 | 0.131 | 11.1 | 0.725 |
| epnp_lm | opencv | 600 | 100.0 | 49.7 | 49.7 | 0.988 | 26.5 | 0.051 | 6.787 | 7.197 |
| ippe | opencv | 600 | 17.8 | 7.833 | 43.9 | 4.248 | 57.8 | 0.247 | 0.075 | 0.209 |
| iterative | opencv | 600 | 100.0 | 49.2 | 49.2 | 1.206 | 44.4 | 0.056 | 0.071 | 2.819 |
| sqpnp | opencv | 600 | 100.0 | 47.3 | 47.3 | 1.352 | 32.8 | 0.177 | 0.083 | 0.383 |
| ransac_dlt | robust-classic | 600 | 69.2 | 69.2 | 100.0 | 6.29e-03 | 0.024 | 5.37e-05 | 0.041 | 38.4 |
| ransac_p3p | robust-classic | 600 | 99.5 | 94.7 | 95.1 | 7.39e-03 | 5.984 | 5.73e-05 | 0.045 | 15.8 |
| cv_ransac_epnp | robust-opencv | 600 | 89.7 | 81.8 | 91.3 | 0.014 | 7.306 | 1.84e-04 | 0.123 | 2.016 |
| cv_ransac_epnp_lm | robust-opencv | 600 | 89.7 | 82.7 | 92.2 | 9.63e-03 | 7.829 | 8.53e-05 | 0.066 | 7.415 |
| cv_ransac_ap3p | robust-opencv | 600 | 99.7 | 85.5 | 85.8 | 0.018 | 15.4 | 2.43e-04 | 0.155 | 1.439 |
| cv_usac_magsac | robust-opencv | 600 | 100.0 | 95.5 | 95.5 | 9.75e-03 | 5.377 | 8.58e-05 | 0.061 | 5.750 |

### Solver overview - outlier-free conditions (noise / quantization only)

| solver | family | solves | returned (%) | success (%) | success when returned (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 283 | 83.4 | 82.7 | 99.2 | 0.016 | 0.097 | 1.23e-04 | 0.127 | 1.635 |
| dlt_lm | classic | 283 | 83.4 | 82.7 | 99.2 | 4.08e-03 | 0.150 | 2.51e-05 | 0.027 | 6.270 |
| epnp | opencv | 283 | 100.0 | 91.5 | 91.5 | 8.62e-03 | 8.852 | 1.17e-04 | 0.078 | 0.708 |
| epnp_lm | opencv | 283 | 100.0 | 93.3 | 93.3 | 4.95e-03 | 7.221 | 3.05e-05 | 0.029 | 5.236 |
| ippe | opencv | 283 | 16.6 | 16.6 | 100.0 | 0.013 | 0.022 | 6.29e-05 | 0.034 | 0.192 |
| iterative | opencv | 283 | 100.0 | 99.3 | 99.3 | 5.74e-03 | 0.096 | 2.96e-05 | 0.030 | 1.630 |
| sqpnp | opencv | 283 | 100.0 | 100.0 | 100.0 | 6.24e-03 | 0.018 | 5.28e-05 | 0.041 | 0.297 |
| ransac_dlt | robust-classic | 283 | 81.3 | 81.3 | 100.0 | 3.96e-03 | 0.016 | 3.03e-05 | 0.027 | 20.6 |
| ransac_p3p | robust-classic | 283 | 100.0 | 100.0 | 100.0 | 4.20e-03 | 0.015 | 2.62e-05 | 0.026 | 13.6 |
| cv_ransac_epnp | robust-opencv | 283 | 100.0 | 91.5 | 91.5 | 9.97e-03 | 8.156 | 1.41e-04 | 0.113 | 1.259 |
| cv_ransac_epnp_lm | robust-opencv | 283 | 100.0 | 91.9 | 91.9 | 7.29e-03 | 8.623 | 6.41e-05 | 0.045 | 5.824 |
| cv_ransac_ap3p | robust-opencv | 283 | 100.0 | 91.5 | 91.5 | 0.012 | 8.869 | 1.93e-04 | 0.128 | 1.024 |
| cv_usac_magsac | robust-opencv | 283 | 100.0 | 99.6 | 99.6 | 5.62e-03 | 0.036 | 4.68e-05 | 0.041 | 4.857 |

### Solver overview - conditions with outliers

| solver | family | solves | returned (%) | success (%) | success when returned (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 317 | 81.1 | 0.631 | 0.778 | 69.3 | 83.4 | 0.744 | 302.9 | 1.510 |
| dlt_lm | classic | 317 | 81.1 | 8.833 | 10.9 | 52.6 | 73.4 | 0.937 | 63.9 | 13.6 |
| epnp | opencv | 317 | 100.0 | 3.785 | 3.785 | 54.4 | 68.1 | 0.916 | 208.9 | 0.736 |
| epnp_lm | opencv | 317 | 100.0 | 10.7 | 10.7 | 7.992 | 43.6 | 0.906 | 89.9 | 11.4 |
| ippe | opencv | 317 | 18.9 | 0 | 0 | 137.7 | 103.1 | 0.971 | 144.6 | 0.234 |
| iterative | opencv | 317 | 100.0 | 4.416 | 4.416 | 79.8 | 83.9 | 1.119 | 83.6 | 6.090 |
| sqpnp | opencv | 317 | 100.0 | 0.315 | 0.315 | 49.1 | 62.0 | 0.739 | 174.5 | 0.446 |
| ransac_dlt | robust-classic | 317 | 58.4 | 58.4 | 100.0 | 8.87e-03 | 0.033 | 7.50e-05 | 0.055 | 262.6 |
| ransac_p3p | robust-classic | 317 | 99.1 | 89.9 | 90.8 | 0.011 | 11.4 | 9.51e-05 | 0.055 | 19.3 |
| cv_ransac_epnp | robust-opencv | 317 | 80.4 | 73.2 | 91.0 | 0.016 | 6.363 | 2.12e-04 | 0.133 | 15.9 |
| cv_ransac_epnp_lm | robust-opencv | 317 | 80.4 | 74.4 | 92.5 | 0.012 | 6.947 | 1.01e-04 | 0.073 | 20.2 |
| cv_ransac_ap3p | robust-opencv | 317 | 99.4 | 80.1 | 80.6 | 0.022 | 21.3 | 3.06e-04 | 0.158 | 4.845 |
| cv_usac_magsac | robust-opencv | 317 | 100.0 | 91.8 | 91.8 | 0.013 | 10.1 | 1.15e-04 | 0.079 | 7.255 |

### Median rotation error (deg) vs Gaussian pixel noise sigma (outlier-free)

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| dlt | 4.67e-14 | 4.40e-03 | 0.018 | 0.047 | 0.094 |
| dlt_lm | 7.31e-15 | 1.29e-03 | 5.70e-03 | 0.010 | 0.031 |
| epnp | 3.23e-13 | 2.23e-03 | 9.22e-03 | 0.017 | 0.035 |
| epnp_lm | 8.61e-15 | 1.51e-03 | 6.44e-03 | 0.012 | 0.034 |
| ippe | 1.60e-13 | 2.59e-03 | 0.026 | 0.029 | 0.055 |
| iterative | 1.09e-14 | 1.58e-03 | 6.52e-03 | 0.014 | 0.035 |
| sqpnp | 6.39e-13 | 1.59e-03 | 7.00e-03 | 0.017 | 0.034 |
| ransac_dlt | 7.31e-15 | 1.09e-03 | 5.90e-03 | 0.016 | 0.036 |
| ransac_p3p | 7.37e-15 | 1.42e-03 | 6.71e-03 | 0.015 | 0.033 |
| cv_ransac_epnp | 3.24e-07 | 2.24e-03 | 0.013 | 0.026 | 0.067 |
| cv_ransac_epnp_lm | 7.99e-15 | 1.57e-03 | 9.14e-03 | 0.021 | 0.071 |
| cv_ransac_ap3p | 3.24e-07 | 2.24e-03 | 0.014 | 0.049 | 0.089 |
| cv_usac_magsac | 2.52e-05 | 1.70e-03 | 7.63e-03 | 0.018 | 0.039 |

### Median reprojection RMSE (px) vs noise sigma (outlier-free)

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| dlt | 6.06e-13 | 0.024 | 0.200 | 0.455 | 0.800 |
| dlt_lm | 1.35e-13 | 6.83e-03 | 0.028 | 0.059 | 0.155 |
| epnp | 6.68e-12 | 0.012 | 0.065 | 0.109 | 0.215 |
| epnp_lm | 1.63e-13 | 7.15e-03 | 0.031 | 0.065 | 0.154 |
| ippe | 5.67e-13 | 7.54e-03 | 0.039 | 0.088 | 0.150 |
| iterative | 2.06e-13 | 7.16e-03 | 0.031 | 0.067 | 0.156 |
| sqpnp | 2.12e-11 | 8.14e-03 | 0.034 | 0.081 | 0.165 |
| ransac_dlt | 1.35e-13 | 6.54e-03 | 0.030 | 0.106 | 0.241 |
| ransac_p3p | 1.34e-13 | 6.80e-03 | 0.031 | 0.086 | 0.164 |
| cv_ransac_epnp | 3.19e-06 | 0.011 | 0.083 | 0.187 | 0.442 |
| cv_ransac_epnp_lm | 1.52e-13 | 7.15e-03 | 0.060 | 0.152 | 0.328 |
| cv_ransac_ap3p | 3.19e-06 | 0.011 | 0.081 | 0.398 | 0.552 |
| cv_usac_magsac | 2.34e-04 | 7.87e-03 | 0.045 | 0.101 | 0.196 |

### Median rotation error (deg): effect of pixel quantization

| solver | sigma=0.0 quantized=no | sigma=0.0 quantized=yes | sigma=0.5 quantized=no | sigma=0.5 quantized=yes |
|---|---|---|---|---|
| dlt | 4.67e-14 | 0.013 | 0.018 | 0.021 |
| dlt_lm | 7.31e-15 | 3.26e-03 | 5.70e-03 | 6.93e-03 |
| epnp | 3.23e-13 | 5.00e-03 | 9.22e-03 | 0.011 |
| epnp_lm | 8.61e-15 | 3.56e-03 | 6.44e-03 | 7.37e-03 |
| ippe | 1.60e-13 | 5.24e-03 | 0.026 | 0.014 |
| iterative | 1.09e-14 | 3.50e-03 | 6.52e-03 | 7.98e-03 |
| sqpnp | 6.39e-13 | 3.58e-03 | 7.00e-03 | 9.06e-03 |
| ransac_dlt | 7.31e-15 | 3.26e-03 | 5.90e-03 | 7.68e-03 |
| ransac_p3p | 7.37e-15 | 3.25e-03 | 6.71e-03 | 6.94e-03 |
| cv_ransac_epnp | 3.24e-07 | 4.64e-03 | 0.013 | 0.016 |
| cv_ransac_epnp_lm | 7.99e-15 | 3.67e-03 | 9.14e-03 | 0.010 |
| cv_ransac_ap3p | 3.24e-07 | 5.35e-03 | 0.014 | 0.015 |
| cv_usac_magsac | 2.52e-05 | 3.73e-03 | 7.63e-03 | 7.96e-03 |

### Success rate (%) vs outlier ratio (uniform outliers, sigma = 0.5 px)

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| dlt | 80.0 | 2.222 | 0 | 0 | 0 | 0 |
| dlt_lm | 80.0 | 42.2 | 8.333 | 0 | 0 | 0 |
| epnp | 92.5 | 26.7 | 0 | 0 | 0 | 0 |
| epnp_lm | 92.5 | 55.6 | 5.556 | 0 | 0 | 0 |
| ippe | 20.0 | 0 | 0 | 0 | 0 | 0 |
| iterative | 100.0 | 31.1 | 0 | 0 | 0 | 0 |
| sqpnp | 100.0 | 2.222 | 0 | 0 | 0 | 0 |
| ransac_dlt | 75.0 | 82.2 | 75.0 | 78.6 | 4.348 | 0 |
| ransac_p3p | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 20.0 |
| cv_ransac_epnp | 92.5 | 95.6 | 88.9 | 88.1 | 47.8 | 0 |
| cv_ransac_epnp_lm | 92.5 | 95.6 | 91.7 | 92.9 | 47.8 | 0 |
| cv_ransac_ap3p | 92.5 | 95.6 | 88.9 | 92.9 | 89.1 | 5.000 |
| cv_usac_magsac | 100.0 | 100.0 | 100.0 | 100.0 | 97.8 | 37.5 |

### Median rotation error (deg) vs outlier ratio (uniform outliers, sigma = 0.5 px)

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| dlt | 0.018 | 31.9 | 48.6 | 72.2 | 102.8 | 128.8 |
| dlt_lm | 5.70e-03 | 1.390 | 15.1 | 61.8 | 98.2 | 125.9 |
| epnp | 9.22e-03 | 3.877 | 42.4 | 80.6 | 95.2 | 108.4 |
| epnp_lm | 6.44e-03 | 1.231 | 3.948 | 8.884 | 41.4 | 104.6 |
| ippe | 0.026 | 11.7 | 149.9 | 139.8 | 150.1 | 153.0 |
| iterative | 6.52e-03 | 3.694 | 113.1 | 95.8 | 100.2 | 124.7 |
| sqpnp | 7.00e-03 | 6.568 | 29.8 | 69.8 | 114.2 | 123.6 |
| ransac_dlt | 5.90e-03 | 4.72e-03 | 4.94e-03 | 8.73e-03 | 0.029 | nan |
| ransac_p3p | 6.71e-03 | 5.17e-03 | 5.74e-03 | 8.70e-03 | 0.015 | 103.7 |
| cv_ransac_epnp | 0.013 | 0.010 | 0.013 | 0.012 | 0.029 | nan |
| cv_ransac_epnp_lm | 9.14e-03 | 8.86e-03 | 8.52e-03 | 9.23e-03 | 0.025 | nan |
| cv_ransac_ap3p | 0.014 | 0.011 | 0.016 | 0.014 | 0.022 | 135.3 |
| cv_usac_magsac | 7.63e-03 | 6.86e-03 | 7.61e-03 | 8.58e-03 | 0.015 | 109.8 |

### Median inlier precision of robust solvers vs outlier ratio

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| ransac_dlt | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | nan |
| ransac_p3p | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| cv_ransac_epnp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | nan |
| cv_ransac_epnp_lm | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | nan |
| cv_ransac_ap3p | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| cv_usac_magsac | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.333 |

### Median inlier recall of robust solvers vs outlier ratio

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| ransac_dlt | 1.000 | 0.999 | 0.999 | 1.000 | 1.000 | nan |
| ransac_p3p | 1.000 | 0.999 | 1.000 | 1.000 | 1.000 | 0 |
| cv_ransac_epnp | 0.973 | 0.980 | 0.973 | 0.986 | 0.901 | nan |
| cv_ransac_epnp_lm | 1.000 | 0.999 | 0.999 | 1.000 | 0.996 | nan |
| cv_ransac_ap3p | 0.977 | 0.968 | 0.964 | 0.979 | 0.990 | 0 |
| cv_usac_magsac | 1.000 | 0.999 | 0.999 | 1.000 | 1.000 | 0.014 |

### Success rate (%) by outlier type (uniform replacement vs swapped assignments)

| solver | ratio=0.2 type=swap | ratio=0.2 type=uniform | ratio=0.5 type=swap | ratio=0.5 type=uniform |
|---|---|---|---|---|
| dlt | 2.564 | 0 | 0 | 0 |
| dlt_lm | 15.4 | 8.333 | 0 | 0 |
| epnp | 0 | 0 | 0 | 0 |
| epnp_lm | 17.9 | 5.556 | 0 | 0 |
| ippe | 0 | 0 | 0 | 0 |
| iterative | 0 | 0 | 0 | 0 |
| sqpnp | 0 | 0 | 0 | 0 |
| ransac_dlt | 82.1 | 75.0 | 79.5 | 78.6 |
| ransac_p3p | 100.0 | 100.0 | 100.0 | 100.0 |
| cv_ransac_epnp | 92.3 | 88.9 | 92.3 | 88.1 |
| cv_ransac_epnp_lm | 92.3 | 91.7 | 92.3 | 92.9 |
| cv_ransac_ap3p | 89.7 | 88.9 | 92.3 | 92.9 |
| cv_usac_magsac | 100.0 | 100.0 | 100.0 | 100.0 |

### Median rotation error (deg) by scene type (outlier-free conditions)

| solver | scene_type=depth_stratified | scene_type=mixed | scene_type=planar_multi | scene_type=planar_single | scene_type=volumetric |
|---|---|---|---|---|---|
| dlt | 0.012 | 0.019 | 0.022 | nan | 0.013 |
| dlt_lm | 2.13e-03 | 4.16e-03 | 6.57e-03 | nan | 3.75e-03 |
| epnp | 5.17e-03 | 6.07e-03 | 0.011 | 17.6 | 4.89e-03 |
| epnp_lm | 2.13e-03 | 4.16e-03 | 6.57e-03 | 0.016 | 3.75e-03 |
| ippe | nan | nan | nan | 0.013 | nan |
| iterative | 2.13e-03 | 5.92e-03 | 8.38e-03 | 9.35e-03 | 3.75e-03 |
| sqpnp | 4.01e-03 | 6.10e-03 | 0.010 | 0.012 | 4.83e-03 |
| ransac_dlt | 1.93e-03 | 4.31e-03 | 7.22e-03 | nan | 3.79e-03 |
| ransac_p3p | 2.00e-03 | 4.31e-03 | 7.21e-03 | 6.88e-03 | 3.75e-03 |
| cv_ransac_epnp | 6.20e-03 | 6.88e-03 | 0.016 | 13.4 | 5.39e-03 |
| cv_ransac_epnp_lm | 3.52e-03 | 4.87e-03 | 9.19e-03 | 0.436 | 4.44e-03 |
| cv_ransac_ap3p | 6.39e-03 | 9.27e-03 | 0.017 | 17.4 | 6.27e-03 |
| cv_usac_magsac | 4.68e-03 | 5.21e-03 | 6.93e-03 | 6.86e-03 | 4.97e-03 |

### Median rotation error (deg) by camera model (outlier-free conditions)

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| dlt | 0.016 | 8.49e-03 | 0.020 |
| dlt_lm | 3.15e-03 | 2.77e-03 | 4.95e-03 |
| epnp | 9.10e-03 | 8.41e-03 | 7.62e-03 |
| epnp_lm | 4.44e-03 | 3.50e-03 | 5.90e-03 |
| ippe | 0.014 | 3.09e-03 | 0.028 |
| iterative | 5.91e-03 | 3.50e-03 | 5.98e-03 |
| sqpnp | 6.45e-03 | 3.90e-03 | 6.50e-03 |
| ransac_dlt | 3.08e-03 | 3.35e-03 | 4.95e-03 |
| ransac_p3p | 3.75e-03 | 3.50e-03 | 5.64e-03 |
| cv_ransac_epnp | 9.97e-03 | 0.015 | 9.57e-03 |
| cv_ransac_epnp_lm | 6.31e-03 | 0.010 | 7.22e-03 |
| cv_ransac_ap3p | 0.013 | 0.013 | 0.011 |
| cv_usac_magsac | 5.49e-03 | 4.70e-03 | 6.51e-03 |

### Median rotation error (deg) by field-of-view class (outlier-free conditions)

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| dlt | 8.49e-03 | 0.087 | 0.015 | 0.012 |
| dlt_lm | 2.63e-03 | 5.61e-03 | 3.60e-03 | 4.20e-03 |
| epnp | 7.91e-03 | 0.010 | 7.11e-03 | 8.77e-03 |
| epnp_lm | 2.30e-03 | 8.88e-03 | 3.81e-03 | 5.80e-03 |
| ippe | 4.94e-04 | 0.013 | 0.042 | 8.03e-03 |
| iterative | 2.70e-03 | 7.50e-03 | 4.93e-03 | 6.00e-03 |
| sqpnp | 3.10e-03 | 7.21e-03 | 6.01e-03 | 6.57e-03 |
| ransac_dlt | 2.99e-03 | 5.66e-03 | 3.75e-03 | 4.25e-03 |
| ransac_p3p | 2.05e-03 | 6.62e-03 | 3.67e-03 | 4.61e-03 |
| cv_ransac_epnp | 8.04e-03 | 0.010 | 8.66e-03 | 0.013 |
| cv_ransac_epnp_lm | 6.64e-03 | 8.67e-03 | 5.41e-03 | 8.34e-03 |
| cv_ransac_ap3p | 0.011 | 0.013 | 0.010 | 0.014 |
| cv_usac_magsac | 3.26e-03 | 0.012 | 4.66e-03 | 5.84e-03 |

### Median rotation error (deg) by distortion level (outlier-free conditions)

| solver | distortion_level=mild | distortion_level=none | distortion_level=strong |
|---|---|---|---|
| dlt | 0.017 | 0.020 | 0.011 |
| dlt_lm | 2.70e-03 | 4.95e-03 | 4.17e-03 |
| epnp | 7.30e-03 | 7.62e-03 | 0.012 |
| epnp_lm | 3.75e-03 | 5.90e-03 | 5.36e-03 |
| ippe | 0.014 | 0.028 | 5.68e-03 |
| iterative | 4.89e-03 | 5.98e-03 | 6.66e-03 |
| sqpnp | 5.93e-03 | 6.50e-03 | 6.69e-03 |
| ransac_dlt | 2.80e-03 | 4.95e-03 | 4.49e-03 |
| ransac_p3p | 2.91e-03 | 5.64e-03 | 5.34e-03 |
| cv_ransac_epnp | 7.91e-03 | 9.57e-03 | 0.019 |
| cv_ransac_epnp_lm | 5.62e-03 | 7.22e-03 | 0.012 |
| cv_ransac_ap3p | 9.94e-03 | 0.011 | 0.018 |
| cv_usac_magsac | 5.42e-03 | 6.51e-03 | 4.85e-03 |

### Runtime per solve (all visible correspondences)

| solver | runtime median (ms) | runtime mean (ms) | runtime max (ms) |
|---|---|---|---|
| dlt | 1.592 | 1.502 | 9.553 |
| dlt_lm | 7.955 | 39.5 | 256.7 |
| epnp | 0.725 | 0.710 | 2.106 |
| epnp_lm | 7.197 | 23.1 | 245.8 |
| ippe | 0.209 | 0.322 | 1.435 |
| iterative | 2.819 | 4.309 | 20.7 |
| sqpnp | 0.383 | 0.401 | 1.357 |
| ransac_dlt | 38.4 | 227.1 | 909.9 |
| ransac_p3p | 15.8 | 46.4 | 703.1 |
| cv_ransac_epnp | 2.016 | 40.7 | 236.5 |
| cv_ransac_epnp_lm | 7.415 | 44.8 | 237.2 |
| cv_ransac_ap3p | 1.439 | 16.9 | 162.8 |
| cv_usac_magsac | 5.750 | 7.396 | 42.7 |

### Failure reasons (solver returned no estimate)

| solver | failure_reason | count |
|---|---|---|
| cv_ransac_ap3p | opencv: ransac found no consensus | 2 |
| cv_ransac_epnp | opencv: ransac found no consensus | 62 |
| cv_ransac_epnp_lm | opencv: ransac found no consensus | 62 |
| dlt | degenerate: coplanar points | 107 |
| dlt_lm | degenerate: coplanar points | 107 |
| ippe | ippe requires coplanar points | 493 |
| ransac_dlt | degenerate: coplanar points | 107 |
| ransac_dlt | ransac: no consensus | 78 |
| ransac_p3p | ransac: no consensus | 3 |

## Calibrated PnP - number-of-points sweep

### Solver overview - all subset sizes pooled (outlier-free conditions)

Success = rotation error <= 5 deg and relative translation error <= 5 %. Each solver is scored only at the subset sizes it accepts, so `solves` differs between rows and the percentages compare within a solver, not down the column: `ap3p` at n = 4 only; `cv_ransac_ap3p` from n = 8 up; `cv_ransac_epnp` from n = 8 up; `cv_ransac_epnp_lm` from n = 8 up; `cv_usac_magsac` from n = 8 up; `dlt` from n = 6 up; `dlt_lm` from n = 6 up; `iterative` from n = 6 up; `p3p` at n = 4 only; `ransac_dlt` from n = 12 up; `ransac_p3p` from n = 8 up.

| solver | family | solves | returned (%) | success (%) | success when returned (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 832 | 78.0 | 72.6 | 93.1 | 0.114 | 3.574 | 1.00e-03 | 1.278 | 0.463 |
| dlt_lm | classic | 832 | 78.0 | 76.7 | 98.3 | 0.022 | 3.125 | 1.83e-04 | 0.167 | 3.387 |
| epnp | opencv | 952 | 100.0 | 83.8 | 83.8 | 0.064 | 13.8 | 8.06e-04 | 0.552 | 0.242 |
| epnp_lm | opencv | 952 | 100.0 | 90.8 | 90.8 | 0.041 | 10.3 | 3.02e-04 | 0.256 | 3.364 |
| p3p | opencv | 120 | 100.0 | 95.0 | 95.0 | 0.240 | 1.683 | 2.55e-03 | 1.090 | 0.200 |
| ap3p | opencv | 120 | 100.0 | 95.0 | 95.0 | 0.240 | 1.683 | 2.55e-03 | 1.090 | 0.173 |
| ippe | opencv | 952 | 22.4 | 21.4 | 95.8 | 0.079 | 2.427 | 6.34e-04 | 0.279 | 0.114 |
| iterative | opencv | 832 | 100.0 | 98.7 | 98.7 | 0.029 | 2.252 | 2.20e-04 | 0.197 | 0.363 |
| sqpnp | opencv | 952 | 100.0 | 99.5 | 99.5 | 0.039 | 0.444 | 3.39e-04 | 0.271 | 0.190 |
| ransac_dlt | robust-classic | 592 | 74.8 | 74.8 | 100.0 | 0.017 | 0.069 | 1.22e-04 | 0.134 | 11.7 |
| ransac_p3p | robust-classic | 712 | 100.0 | 99.9 | 99.9 | 0.024 | 0.128 | 2.00e-04 | 0.160 | 7.789 |
| cv_ransac_epnp | robust-opencv | 712 | 96.1 | 87.9 | 91.5 | 0.041 | 7.340 | 4.90e-04 | 0.397 | 0.521 |
| cv_ransac_epnp_lm | robust-opencv | 712 | 96.1 | 89.6 | 93.3 | 0.032 | 7.173 | 2.39e-04 | 0.229 | 3.584 |
| cv_ransac_ap3p | robust-opencv | 712 | 100.0 | 88.2 | 88.2 | 0.047 | 11.6 | 5.68e-04 | 0.496 | 0.410 |
| cv_usac_magsac | robust-opencv | 712 | 100.0 | 99.9 | 99.9 | 0.031 | 0.153 | 2.41e-04 | 0.209 | 3.440 |

### Median rotation error (deg) vs number of correspondences (outlier-free)

| solver | num_points_setting=4 | num_points_setting=6 | num_points_setting=8 | num_points_setting=12 | num_points_setting=20 | num_points_setting=50 | num_points_setting=100 | num_points_setting=500 |
|---|---|---|---|---|---|---|---|---|
| dlt | nan | 1.352 | 0.447 | 0.227 | 0.114 | 0.070 | 0.046 | 0.018 |
| dlt_lm | nan | 0.091 | 0.062 | 0.038 | 0.032 | 0.016 | 0.012 | 5.99e-03 |
| epnp | 1.773 | 0.127 | 0.109 | 0.073 | 0.053 | 0.038 | 0.025 | 0.015 |
| epnp_lm | 0.167 | 0.096 | 0.081 | 0.048 | 0.048 | 0.023 | 0.015 | 7.14e-03 |
| p3p | 0.240 | nan | nan | nan | nan | nan | nan | nan |
| ap3p | 0.240 | nan | nan | nan | nan | nan | nan | nan |
| ippe | 0.656 | 0.138 | 0.121 | 0.120 | 0.100 | 0.042 | 0.051 | 0.020 |
| iterative | nan | 0.093 | 0.076 | 0.044 | 0.041 | 0.022 | 0.017 | 9.12e-03 |
| sqpnp | 0.128 | 0.089 | 0.079 | 0.047 | 0.042 | 0.024 | 0.019 | 0.011 |
| ransac_dlt | nan | nan | nan | 0.036 | 0.029 | 0.018 | 0.014 | 7.20e-03 |
| ransac_p3p | nan | nan | 0.078 | 0.042 | 0.040 | 0.021 | 0.015 | 6.65e-03 |
| cv_ransac_epnp | nan | nan | 0.097 | 0.056 | 0.045 | 0.038 | 0.026 | 0.017 |
| cv_ransac_epnp_lm | nan | nan | 0.081 | 0.042 | 0.046 | 0.029 | 0.018 | 0.015 |
| cv_ransac_ap3p | nan | nan | 0.124 | 0.081 | 0.063 | 0.036 | 0.031 | 0.017 |
| cv_usac_magsac | nan | nan | 0.073 | 0.043 | 0.047 | 0.027 | 0.020 | 9.90e-03 |

### Success rate (%) vs number of correspondences (outlier-free)

| solver | num_points_setting=4 | num_points_setting=6 | num_points_setting=8 | num_points_setting=12 | num_points_setting=20 | num_points_setting=50 | num_points_setting=100 | num_points_setting=500 |
|---|---|---|---|---|---|---|---|---|
| dlt | nan | 53.3 | 70.8 | 75.0 | 76.7 | 77.1 | 78.0 | 77.6 |
| dlt_lm | nan | 70.0 | 76.7 | 78.3 | 78.3 | 78.0 | 78.0 | 77.6 |
| epnp | 57.5 | 85.8 | 88.3 | 85.8 | 87.5 | 89.0 | 89.0 | 87.9 |
| epnp_lm | 80.0 | 90.0 | 93.3 | 91.7 | 92.5 | 92.4 | 93.2 | 93.1 |
| p3p | 95.0 | nan | nan | nan | nan | nan | nan | nan |
| ap3p | 95.0 | nan | nan | nan | nan | nan | nan | nan |
| ippe | 19.2 | 21.7 | 20.8 | 21.7 | 21.7 | 22.0 | 22.0 | 22.4 |
| iterative | nan | 93.3 | 97.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| sqpnp | 96.7 | 100.0 | 99.2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| ransac_dlt | nan | nan | nan | 67.5 | 75.0 | 77.1 | 77.1 | 77.6 |
| ransac_p3p | nan | nan | 99.2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| cv_ransac_epnp | nan | nan | 87.5 | 85.8 | 88.3 | 89.0 | 89.0 | 87.9 |
| cv_ransac_epnp_lm | nan | nan | 91.7 | 87.5 | 89.2 | 90.7 | 89.8 | 88.8 |
| cv_ransac_ap3p | nan | nan | 88.3 | 85.8 | 88.3 | 89.8 | 89.0 | 87.9 |
| cv_usac_magsac | nan | nan | 99.2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

### Median runtime (ms) vs number of correspondences (outlier-free)

| solver | num_points_setting=4 | num_points_setting=6 | num_points_setting=8 | num_points_setting=12 | num_points_setting=20 | num_points_setting=50 | num_points_setting=100 | num_points_setting=500 |
|---|---|---|---|---|---|---|---|---|
| dlt | nan | 0.352 | 0.352 | 0.470 | 0.489 | 0.572 | 0.555 | 0.984 |
| dlt_lm | nan | 3.537 | 3.267 | 3.443 | 3.385 | 3.336 | 3.286 | 4.398 |
| epnp | 0.262 | 0.207 | 0.203 | 0.222 | 0.226 | 0.244 | 0.262 | 0.408 |
| epnp_lm | 3.911 | 3.190 | 3.129 | 3.142 | 3.140 | 3.243 | 3.272 | 4.409 |
| p3p | 0.200 | nan | nan | nan | nan | nan | nan | nan |
| ap3p | 0.173 | nan | nan | nan | nan | nan | nan | nan |
| ippe | 0.094 | 0.107 | 0.105 | 0.105 | 0.110 | 0.112 | 0.116 | 0.142 |
| iterative | nan | 0.332 | 0.307 | 0.318 | 0.322 | 0.358 | 0.438 | 1.011 |
| sqpnp | 0.204 | 0.172 | 0.165 | 0.168 | 0.167 | 0.179 | 0.187 | 0.239 |
| ransac_dlt | nan | nan | nan | 11.2 | 11.5 | 9.884 | 11.0 | 14.1 |
| ransac_p3p | nan | nan | 7.206 | 7.555 | 7.597 | 7.474 | 7.747 | 10.2 |
| cv_ransac_epnp | nan | nan | 0.361 | 0.460 | 0.482 | 0.528 | 0.532 | 0.821 |
| cv_ransac_epnp_lm | nan | nan | 3.258 | 3.392 | 3.376 | 3.534 | 3.617 | 4.609 |
| cv_ransac_ap3p | nan | nan | 0.331 | 0.370 | 0.364 | 0.410 | 0.437 | 0.678 |
| cv_usac_magsac | nan | nan | 2.305 | 1.733 | 1.626 | 3.921 | 4.031 | 4.494 |

## Single-view calibration (uncalibrated DLT)

### Single-view uncalibrated DLT - overview

Success = mean focal-length error <= 5 % and rotation error <= 5 deg. Lens distortion is not modelled by the DLT, so distorted cameras show a systematic bias.

| solver | solves | returned (%) | success (%) | focal err median (%) | cx err median (px) | cy err median (px) | rot err median (deg) | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt_uncalibrated | 600 | 100.0 | 77.5 | 0.430 | 9.585 | 9.700 | 0.928 | 0.410 | 1.776 |
| dlt_uncalibrated_lm | 600 | 100.0 | 78.3 | 0.387 | 11.0 | 9.512 | 0.972 | 0.362 | 13.5 |

### Median focal-length error (%) by camera model

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| dlt_uncalibrated | 0.631 | 11.6 | 0.020 |
| dlt_uncalibrated_lm | 0.603 | 7.727 | 0.016 |

### Median focal-length error (%) by distortion level

| solver | distortion_level=mild | distortion_level=none | distortion_level=strong |
|---|---|---|---|
| dlt_uncalibrated | 0.976 | 0.020 | 3.348 |
| dlt_uncalibrated_lm | 0.903 | 0.016 | 2.156 |

### Median focal-length error (%) by field-of-view class

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| dlt_uncalibrated | 5.816 | 0.353 | 0.222 | 0.335 |
| dlt_uncalibrated_lm | 7.383 | 0.340 | 0.173 | 0.258 |

### Median focal-length error (%) by scene type

| solver | scene_type=depth_stratified | scene_type=mixed | scene_type=planar_multi | scene_type=volumetric |
|---|---|---|---|---|
| dlt_uncalibrated | 1.768 | 0.476 | 0.819 | 0.231 |
| dlt_uncalibrated_lm | 1.751 | 0.381 | 0.758 | 0.167 |

### Median focal-length error (%) vs noise sigma (pinhole cameras, no quantization)

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| dlt_uncalibrated | 8.43e-14 | 3.84e-03 | 0.038 | 0.042 | 0.178 |
| dlt_uncalibrated_lm | 1.03e-14 | 3.17e-03 | 0.037 | 0.073 | 0.181 |

## Multi-view calibration

### Multi-view calibration - overview

Each rig = all views sharing one intrinsic set and one noise condition. Success = mean focal error <= 1 % and mean rotation error <= 1 deg. `opencv` = calibrateCamera / fisheye.calibrate, `ba_scratch` = from-scratch bundle adjustment.

| solver | rigs | returned (%) | success (%) | focal err median (%) | cx err median (px) | dist coeff RMSE median | rot err median (deg) | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| opencv | 30 | 100.0 | 80.0 | 0.020 | 0.876 | 0.077 | 0.062 | 0.054 | 126.3 |
| ba_scratch | 30 | 100.0 | 86.7 | 0.016 | 0.536 | 0.015 | 0.050 | 0.044 | 2,616 |

### Median focal-length error (%) by camera model

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| ba_scratch | 0.018 | 6.17e-03 | 0.029 |
| opencv | 0.018 | 1.079 | 0.029 |

### Success rate (%) by camera model

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| ba_scratch | 80.0 | 85.7 | 100.0 |
| opencv | 93.3 | 42.9 | 87.5 |

### Median focal-length error (%) by field-of-view class

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| ba_scratch | 0.011 | 0.118 | 0.015 | 9.21e-03 |
| opencv | 29.8 | 0.107 | 0.015 | 9.21e-03 |

### Success rate (%) by field-of-view class

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| ba_scratch | 83.3 | 71.4 | 90.0 | 100.0 |
| opencv | 33.3 | 85.7 | 90.0 | 100.0 |

### Median focal-length error (%) by noise sigma

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| ba_scratch | 6.55e-12 | 9.21e-03 | 0.032 | 0.038 | 0.120 |
| opencv | 1.51e-06 | 9.21e-03 | 0.038 | 0.038 | 0.107 |

### Success rate (%) by noise sigma

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| ba_scratch | 100.0 | 100.0 | 88.9 | 66.7 | 66.7 |
| opencv | 85.7 | 100.0 | 66.7 | 100.0 | 66.7 |

### Median focal-length error (%) by scene type

| solver | scene_type=depth_stratified | scene_type=mixed | scene_type=planar_multi | scene_type=volumetric |
|---|---|---|---|---|
| ba_scratch | 5.77e-03 | 0.053 | 0.019 | 0.015 |
| opencv | 5.77e-03 | 0.054 | 0.095 | 0.015 |

### Success rate (%) by scene type

| solver | scene_type=depth_stratified | scene_type=mixed | scene_type=planar_multi | scene_type=volumetric |
|---|---|---|---|---|
| ba_scratch | 100.0 | 83.3 | 70.0 | 100.0 |
| opencv | 83.3 | 100.0 | 50.0 | 100.0 |
