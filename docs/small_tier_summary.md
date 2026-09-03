# Benchmark summary

Environment: pnpcorr_version=1.0.0, python=3.11.15, platform=Linux-6.18.44-fc-v24-x86_64-with-glibc2.39, processor=x86_64, numpy=2.4.4, pandas=3.0.2, opencv=4.13.0

## Calibrated PnP

### Solver overview - all conditions

Success = rotation error <= 5 deg and relative translation error <= 5 %. Errors are medians over every evaluated sample (all visible correspondences).

| solver | family | solves | returned (%) | success (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 600 | 80.3 | 38.0 | 5.668 | 47.1 | 0.063 | 0.381 | 2.321 |
| dlt_lm | classic | 600 | 80.3 | 42.0 | 0.749 | 42.2 | 0.037 | 0.058 | 13.2 |
| epnp | opencv | 600 | 100.0 | 45.2 | 2.196 | 37.5 | 0.128 | 18.5 | 1.505 |
| epnp_lm | opencv | 600 | 100.0 | 49.8 | 1.225 | 21.9 | 0.049 | 12.9 | 12.9 |
| ippe | opencv | 118 | 100.0 | 45.8 | 2.271 | 49.6 | 0.184 | 0.140 | 1.546 |
| iterative | opencv | 600 | 100.0 | 49.3 | 1.414 | 44.3 | 0.057 | 0.068 | 11.0 |
| sqpnp | opencv | 600 | 100.0 | 46.8 | 2.392 | 33.4 | 0.190 | 0.080 | 0.963 |
| ransac_dlt | robust-classic | 600 | 68.2 | 67.8 | 7.14e-03 | 0.084 | 6.38e-05 | 0.045 | 91.7 |
| ransac_p3p | robust-classic | 600 | 99.7 | 94.8 | 8.34e-03 | 5.388 | 6.05e-05 | 0.043 | 30.8 |
| cv_ransac_epnp | robust-opencv | 600 | 89.5 | 82.2 | 0.013 | 6.399 | 1.78e-04 | 0.106 | 12.2 |
| cv_ransac_epnp_lm | robust-opencv | 600 | 89.5 | 83.2 | 0.010 | 6.612 | 8.21e-05 | 0.059 | 21.7 |
| cv_ransac_ap3p | robust-opencv | 600 | 99.8 | 87.2 | 0.019 | 12.3 | 2.42e-04 | 0.155 | 8.764 |
| cv_usac_magsac | robust-opencv | 600 | 100.0 | 95.2 | 0.010 | 5.757 | 8.31e-05 | 0.057 | 13.0 |

### Solver overview - outlier-free conditions (noise / quantization only)

| solver | family | solves | returned (%) | success (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 280 | 80.7 | 80.7 | 0.017 | 0.053 | 1.49e-04 | 0.125 | 2.396 |
| dlt_lm | classic | 280 | 80.7 | 80.7 | 4.97e-03 | 0.012 | 3.63e-05 | 0.031 | 8.844 |
| epnp | opencv | 280 | 100.0 | 91.1 | 8.62e-03 | 7.983 | 1.14e-04 | 0.070 | 1.492 |
| epnp_lm | opencv | 280 | 100.0 | 93.9 | 5.63e-03 | 6.024 | 4.01e-05 | 0.032 | 8.683 |
| ippe | opencv | 54 | 100.0 | 100.0 | 0.011 | 0.032 | 6.14e-05 | 0.038 | 1.510 |
| iterative | opencv | 280 | 100.0 | 100.0 | 5.69e-03 | 0.016 | 3.96e-05 | 0.032 | 4.926 |
| sqpnp | opencv | 280 | 100.0 | 100.0 | 6.35e-03 | 0.015 | 6.39e-05 | 0.039 | 0.682 |
| ransac_dlt | robust-classic | 280 | 79.3 | 79.3 | 5.26e-03 | 0.016 | 4.00e-05 | 0.032 | 32.3 |
| ransac_p3p | robust-classic | 280 | 100.0 | 100.0 | 5.53e-03 | 0.014 | 3.63e-05 | 0.031 | 23.1 |
| cv_ransac_epnp | robust-opencv | 280 | 100.0 | 91.1 | 0.010 | 7.367 | 1.28e-04 | 0.091 | 4.554 |
| cv_ransac_epnp_lm | robust-opencv | 280 | 100.0 | 92.5 | 7.62e-03 | 7.405 | 6.69e-05 | 0.040 | 12.4 |
| cv_ransac_ap3p | robust-opencv | 280 | 100.0 | 91.4 | 0.013 | 7.998 | 1.74e-04 | 0.143 | 4.391 |
| cv_usac_magsac | robust-opencv | 280 | 100.0 | 100.0 | 6.61e-03 | 0.026 | 6.04e-05 | 0.043 | 9.023 |

### Solver overview - conditions with outliers

| solver | family | solves | returned (%) | success (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 320 | 80.0 | 0.625 | 76.1 | 88.7 | 0.894 | 303.3 | 2.230 |
| dlt_lm | classic | 320 | 80.0 | 8.125 | 68.1 | 79.5 | 0.928 | 63.8 | 24.9 |
| epnp | opencv | 320 | 100.0 | 5.000 | 48.7 | 63.4 | 0.908 | 216.6 | 1.513 |
| epnp_lm | opencv | 320 | 100.0 | 11.2 | 6.294 | 35.8 | 0.872 | 91.5 | 17.6 |
| ippe | opencv | 64 | 100.0 | 0 | 107.7 | 91.5 | 0.857 | 151.5 | 1.573 |
| iterative | opencv | 320 | 100.0 | 5.000 | 69.6 | 83.1 | 1.016 | 67.5 | 26.1 |
| sqpnp | opencv | 320 | 100.0 | 0.312 | 49.6 | 62.6 | 0.774 | 158.1 | 1.203 |
| ransac_dlt | robust-classic | 320 | 58.4 | 57.8 | 0.011 | 0.165 | 9.38e-05 | 0.055 | 597.6 |
| ransac_p3p | robust-classic | 320 | 99.4 | 90.3 | 0.012 | 10.1 | 8.94e-05 | 0.053 | 58.4 |
| cv_ransac_epnp | robust-opencv | 320 | 80.3 | 74.4 | 0.015 | 5.344 | 1.95e-04 | 0.122 | 148.3 |
| cv_ransac_epnp_lm | robust-opencv | 320 | 80.3 | 75.0 | 0.012 | 5.748 | 8.91e-05 | 0.066 | 141.1 |
| cv_ransac_ap3p | robust-opencv | 320 | 99.7 | 83.4 | 0.025 | 16.1 | 3.03e-04 | 0.168 | 56.4 |
| cv_usac_magsac | robust-opencv | 320 | 100.0 | 90.9 | 0.014 | 10.8 | 1.01e-04 | 0.067 | 17.5 |

### Median rotation error (deg) vs Gaussian pixel noise sigma (outlier-free)

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| dlt | 5.13e-14 | 4.64e-03 | 0.024 | 0.043 | 0.082 |
| dlt_lm | 8.45e-15 | 1.54e-03 | 5.69e-03 | 0.012 | 0.031 |
| epnp | 5.00e-13 | 2.18e-03 | 8.81e-03 | 0.017 | 0.040 |
| epnp_lm | 8.39e-15 | 1.58e-03 | 6.68e-03 | 0.012 | 0.032 |
| ippe | 9.08e-14 | 2.24e-03 | 0.014 | 0.019 | 0.044 |
| iterative | 2.03e-14 | 1.62e-03 | 6.43e-03 | 0.013 | 0.030 |
| sqpnp | 1.33e-12 | 1.83e-03 | 6.69e-03 | 0.014 | 0.032 |
| ransac_dlt | 8.45e-15 | 1.54e-03 | 6.21e-03 | 0.014 | 0.030 |
| ransac_p3p | 8.21e-15 | 1.54e-03 | 6.24e-03 | 0.016 | 0.038 |
| cv_ransac_epnp | 3.49e-07 | 2.16e-03 | 0.010 | 0.029 | 0.076 |
| cv_ransac_epnp_lm | 8.45e-15 | 1.60e-03 | 7.83e-03 | 0.025 | 0.072 |
| cv_ransac_ap3p | 3.49e-07 | 2.09e-03 | 0.017 | 0.064 | 0.136 |
| cv_usac_magsac | 3.36e-05 | 1.91e-03 | 8.39e-03 | 0.015 | 0.040 |

### Median reprojection RMSE (px) vs noise sigma (outlier-free)

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| dlt | 5.27e-13 | 0.037 | 0.290 | 0.348 | 0.440 |
| dlt_lm | 1.36e-13 | 6.53e-03 | 0.034 | 0.063 | 0.125 |
| epnp | 6.60e-12 | 0.012 | 0.071 | 0.104 | 0.204 |
| epnp_lm | 1.23e-13 | 6.81e-03 | 0.035 | 0.068 | 0.125 |
| ippe | 7.13e-13 | 0.010 | 0.041 | 0.055 | 0.220 |
| iterative | 2.33e-13 | 6.96e-03 | 0.033 | 0.066 | 0.129 |
| sqpnp | 1.32e-11 | 9.58e-03 | 0.043 | 0.082 | 0.159 |
| ransac_dlt | 1.36e-13 | 6.53e-03 | 0.037 | 0.132 | 0.200 |
| ransac_p3p | 1.12e-13 | 6.81e-03 | 0.039 | 0.090 | 0.164 |
| cv_ransac_epnp | 2.51e-06 | 0.011 | 0.095 | 0.185 | 0.362 |
| cv_ransac_epnp_lm | 1.31e-13 | 7.38e-03 | 0.050 | 0.179 | 0.359 |
| cv_ransac_ap3p | 2.51e-06 | 0.012 | 0.215 | 0.314 | 0.630 |
| cv_usac_magsac | 2.70e-04 | 0.010 | 0.052 | 0.095 | 0.229 |

### Median rotation error (deg): effect of pixel quantization

| solver | sigma=0.0 quantized=no | sigma=0.0 quantized=yes | sigma=0.5 quantized=no | sigma=0.5 quantized=yes |
|---|---|---|---|---|
| dlt | 5.13e-14 | 0.013 | 0.024 | 0.022 |
| dlt_lm | 8.45e-15 | 3.85e-03 | 5.69e-03 | 6.63e-03 |
| epnp | 5.00e-13 | 6.09e-03 | 8.81e-03 | 0.011 |
| epnp_lm | 8.39e-15 | 5.06e-03 | 6.68e-03 | 7.26e-03 |
| ippe | 9.08e-14 | 6.16e-03 | 0.014 | 9.39e-03 |
| iterative | 2.03e-14 | 3.90e-03 | 6.43e-03 | 7.50e-03 |
| sqpnp | 1.33e-12 | 4.16e-03 | 6.69e-03 | 9.02e-03 |
| ransac_dlt | 8.45e-15 | 3.90e-03 | 6.21e-03 | 7.61e-03 |
| ransac_p3p | 8.21e-15 | 3.88e-03 | 6.24e-03 | 7.26e-03 |
| cv_ransac_epnp | 3.49e-07 | 6.09e-03 | 0.010 | 0.012 |
| cv_ransac_epnp_lm | 8.45e-15 | 4.86e-03 | 7.83e-03 | 9.70e-03 |
| cv_ransac_ap3p | 3.49e-07 | 6.56e-03 | 0.017 | 0.014 |
| cv_usac_magsac | 3.36e-05 | 4.58e-03 | 8.39e-03 | 8.45e-03 |

### Success rate (%) vs outlier ratio (uniform outliers, sigma = 0.5 px)

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| dlt | 81.1 | 4.444 | 0 | 0 | 0 | 0 |
| dlt_lm | 81.1 | 40.0 | 10.5 | 0 | 0 | 0 |
| epnp | 91.9 | 35.6 | 0 | 0 | 0 | 0 |
| epnp_lm | 97.3 | 60.0 | 7.895 | 0 | 0 | 0 |
| ippe | 100.0 | 0 | 0 | 0 | 0 | 0 |
| iterative | 100.0 | 35.6 | 0 | 0 | 0 | 0 |
| sqpnp | 100.0 | 2.222 | 0 | 0 | 0 | 0 |
| ransac_dlt | 75.7 | 82.2 | 78.9 | 76.2 | 6.818 | 0 |
| ransac_p3p | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 24.4 |
| cv_ransac_epnp | 91.9 | 95.6 | 92.1 | 90.5 | 45.5 | 0 |
| cv_ransac_epnp_lm | 91.9 | 95.6 | 92.1 | 92.9 | 45.5 | 0 |
| cv_ransac_ap3p | 91.9 | 95.6 | 92.1 | 92.9 | 93.2 | 19.5 |
| cv_usac_magsac | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 29.3 |

### Median rotation error (deg) vs outlier ratio (uniform outliers, sigma = 0.5 px)

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| dlt | 0.024 | 21.1 | 75.3 | 79.1 | 118.3 | 133.4 |
| dlt_lm | 5.69e-03 | 1.629 | 45.7 | 77.3 | 114.9 | 132.3 |
| epnp | 8.81e-03 | 2.334 | 18.2 | 90.0 | 88.8 | 102.2 |
| epnp_lm | 6.68e-03 | 1.393 | 3.737 | 11.7 | 31.3 | 91.9 |
| ippe | 0.014 | 2.415 | 106.6 | 158.8 | 149.7 | 120.2 |
| iterative | 6.43e-03 | 2.813 | 14.0 | 89.1 | 142.3 | 157.7 |
| sqpnp | 6.69e-03 | 8.747 | 34.7 | 75.1 | 112.0 | 120.3 |
| ransac_dlt | 6.21e-03 | 6.38e-03 | 4.09e-03 | 0.012 | 0.015 | nan |
| ransac_p3p | 6.24e-03 | 5.68e-03 | 7.52e-03 | 9.95e-03 | 0.015 | 93.0 |
| cv_ransac_epnp | 0.010 | 0.011 | 0.011 | 0.015 | 0.064 | nan |
| cv_ransac_epnp_lm | 7.83e-03 | 0.010 | 7.72e-03 | 0.013 | 0.038 | nan |
| cv_ransac_ap3p | 0.017 | 0.014 | 0.016 | 0.015 | 0.028 | 102.0 |
| cv_usac_magsac | 8.39e-03 | 7.25e-03 | 9.19e-03 | 9.96e-03 | 0.015 | 92.5 |

### Median inlier precision of robust solvers vs outlier ratio

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| ransac_dlt | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | nan |
| ransac_p3p | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.250 |
| cv_ransac_epnp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | nan |
| cv_ransac_epnp_lm | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | nan |
| cv_ransac_ap3p | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.100 |
| cv_usac_magsac | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |

### Median inlier recall of robust solvers vs outlier ratio

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| ransac_dlt | 0.999 | 0.999 | 0.999 | 0.999 | 0.996 | nan |
| ransac_p3p | 0.999 | 0.999 | 1.000 | 1.000 | 1.000 | 0.013 |
| cv_ransac_epnp | 0.973 | 0.969 | 0.985 | 0.986 | 0.720 | nan |
| cv_ransac_epnp_lm | 0.999 | 0.999 | 0.999 | 0.999 | 0.985 | nan |
| cv_ransac_ap3p | 0.946 | 0.956 | 0.968 | 0.984 | 0.984 | 4.67e-03 |
| cv_usac_magsac | 0.999 | 0.999 | 0.999 | 1.000 | 1.000 | 0 |

### Success rate (%) by outlier type (uniform replacement vs swapped assignments)

| solver | ratio=0.2 type=swap | ratio=0.2 type=uniform | ratio=0.5 type=swap | ratio=0.5 type=uniform |
|---|---|---|---|---|
| dlt | 0 | 0 | 0 | 0 |
| dlt_lm | 10.3 | 10.5 | 0 | 0 |
| epnp | 0 | 0 | 0 | 0 |
| epnp_lm | 15.4 | 7.895 | 0 | 0 |
| ippe | 0 | 0 | 0 | 0 |
| iterative | 0 | 0 | 0 | 0 |
| sqpnp | 0 | 0 | 0 | 0 |
| ransac_dlt | 82.1 | 78.9 | 65.8 | 76.2 |
| ransac_p3p | 100.0 | 100.0 | 100.0 | 100.0 |
| cv_ransac_epnp | 92.3 | 92.1 | 92.1 | 90.5 |
| cv_ransac_epnp_lm | 92.3 | 92.1 | 92.1 | 92.9 |
| cv_ransac_ap3p | 89.7 | 92.1 | 92.1 | 92.9 |
| cv_usac_magsac | 100.0 | 100.0 | 100.0 | 100.0 |

### Median rotation error (deg) by scene type (outlier-free conditions)

| solver | scene_type=depth_stratified | scene_type=mixed | scene_type=planar_multi | scene_type=planar_single | scene_type=volumetric |
|---|---|---|---|---|---|
| dlt | 0.018 | 0.019 | 0.015 | nan | 0.022 |
| dlt_lm | 3.06e-03 | 5.76e-03 | 5.62e-03 | nan | 5.94e-03 |
| epnp | 4.80e-03 | 6.16e-03 | 0.010 | 0.193 | 6.04e-03 |
| epnp_lm | 3.06e-03 | 5.76e-03 | 5.62e-03 | 0.014 | 5.94e-03 |
| ippe | nan | nan | nan | 0.011 | nan |
| iterative | 3.01e-03 | 5.76e-03 | 6.68e-03 | 0.011 | 5.94e-03 |
| sqpnp | 4.02e-03 | 5.51e-03 | 7.37e-03 | 0.011 | 5.67e-03 |
| ransac_dlt | 2.82e-03 | 5.73e-03 | 5.85e-03 | nan | 6.81e-03 |
| ransac_p3p | 2.38e-03 | 6.01e-03 | 6.10e-03 | 6.73e-03 | 6.63e-03 |
| cv_ransac_epnp | 4.94e-03 | 6.28e-03 | 0.011 | 0.359 | 5.91e-03 |
| cv_ransac_epnp_lm | 4.06e-03 | 5.73e-03 | 7.56e-03 | 0.144 | 6.63e-03 |
| cv_ransac_ap3p | 7.55e-03 | 8.68e-03 | 0.019 | 0.174 | 0.010 |
| cv_usac_magsac | 4.93e-03 | 5.36e-03 | 8.27e-03 | 8.55e-03 | 8.45e-03 |

### Median rotation error (deg) by camera model (outlier-free conditions)

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| dlt | 0.015 | 0.015 | 0.031 |
| dlt_lm | 3.91e-03 | 5.31e-03 | 5.36e-03 |
| epnp | 5.94e-03 | 0.011 | 0.012 |
| epnp_lm | 4.54e-03 | 6.92e-03 | 5.62e-03 |
| ippe | 5.59e-03 | 0.032 | 0.018 |
| iterative | 3.91e-03 | 5.94e-03 | 7.61e-03 |
| sqpnp | 3.45e-03 | 7.89e-03 | 7.66e-03 |
| ransac_dlt | 3.69e-03 | 7.74e-03 | 5.19e-03 |
| ransac_p3p | 3.58e-03 | 8.05e-03 | 5.65e-03 |
| cv_ransac_epnp | 4.86e-03 | 0.014 | 0.012 |
| cv_ransac_epnp_lm | 5.66e-03 | 0.012 | 7.69e-03 |
| cv_ransac_ap3p | 8.01e-03 | 0.017 | 0.018 |
| cv_usac_magsac | 5.10e-03 | 8.01e-03 | 8.39e-03 |

### Median rotation error (deg) by field-of-view class (outlier-free conditions)

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| dlt | 8.61e-03 | 0.048 | 0.015 | 0.016 |
| dlt_lm | 4.94e-03 | 4.19e-03 | 5.02e-03 | 5.46e-03 |
| epnp | 7.73e-03 | 6.07e-03 | 7.85e-03 | 0.012 |
| epnp_lm | 4.94e-03 | 5.85e-03 | 4.96e-03 | 6.95e-03 |
| ippe | nan | 7.08e-03 | 0.017 | 0.022 |
| iterative | 4.94e-03 | 4.47e-03 | 5.47e-03 | 7.24e-03 |
| sqpnp | 7.00e-03 | 3.39e-03 | 5.83e-03 | 9.32e-03 |
| ransac_dlt | 9.26e-03 | 4.20e-03 | 3.95e-03 | 6.60e-03 |
| ransac_p3p | 8.18e-03 | 4.47e-03 | 3.90e-03 | 6.53e-03 |
| cv_ransac_epnp | 0.013 | 4.94e-03 | 8.65e-03 | 0.014 |
| cv_ransac_epnp_lm | 0.010 | 5.87e-03 | 5.47e-03 | 9.76e-03 |
| cv_ransac_ap3p | 0.015 | 0.010 | 0.011 | 0.017 |
| cv_usac_magsac | 6.81e-03 | 6.52e-03 | 5.72e-03 | 8.02e-03 |

### Median rotation error (deg) by distortion level (outlier-free conditions)

| solver | distortion_level=mild | distortion_level=none | distortion_level=strong |
|---|---|---|---|
| dlt | 0.021 | 0.031 | 0.011 |
| dlt_lm | 4.72e-03 | 5.36e-03 | 4.74e-03 |
| epnp | 6.90e-03 | 0.012 | 8.59e-03 |
| epnp_lm | 5.73e-03 | 5.62e-03 | 5.53e-03 |
| ippe | 6.02e-03 | 0.018 | 0.028 |
| iterative | 4.72e-03 | 7.61e-03 | 5.09e-03 |
| sqpnp | 5.27e-03 | 7.66e-03 | 5.65e-03 |
| ransac_dlt | 5.26e-03 | 5.19e-03 | 5.65e-03 |
| ransac_p3p | 4.53e-03 | 5.65e-03 | 5.38e-03 |
| cv_ransac_epnp | 7.86e-03 | 0.012 | 0.011 |
| cv_ransac_epnp_lm | 7.36e-03 | 7.69e-03 | 8.85e-03 |
| cv_ransac_ap3p | 0.010 | 0.018 | 0.014 |
| cv_usac_magsac | 6.36e-03 | 8.39e-03 | 5.65e-03 |

### Runtime per solve (all visible correspondences)

| solver | runtime median (ms) | runtime mean (ms) | runtime max (ms) |
|---|---|---|---|
| dlt | 2.321 | 17.1 | 122.9 |
| dlt_lm | 13.2 | 73.5 | 480.7 |
| epnp | 1.505 | 1.667 | 9.504 |
| epnp_lm | 12.9 | 30.9 | 370.8 |
| ippe | 1.546 | 1.571 | 2.040 |
| iterative | 11.0 | 16.4 | 53.4 |
| sqpnp | 0.963 | 1.133 | 9.427 |
| ransac_dlt | 91.7 | 405.5 | 1,569 |
| ransac_p3p | 30.8 | 200.1 | 2,313 |
| cv_ransac_epnp | 12.2 | 378.0 | 1,862 |
| cv_ransac_epnp_lm | 21.7 | 383.8 | 1,805 |
| cv_ransac_ap3p | 8.764 | 210.4 | 1,589 |
| cv_usac_magsac | 13.0 | 39.1 | 449.0 |

### Failure reasons (solver returned no estimate)

| solver | failure_reason | count |
|---|---|---|
| cv_ransac_ap3p | opencv: ransac found no consensus | 1 |
| cv_ransac_epnp | opencv: ransac found no consensus | 63 |
| cv_ransac_epnp_lm | opencv: ransac found no consensus | 63 |
| dlt | degenerate: coplanar points | 118 |
| dlt_lm | degenerate: coplanar points | 118 |
| ransac_dlt | degenerate: coplanar points | 118 |
| ransac_dlt | ransac: no consensus | 73 |
| ransac_p3p | ransac: no consensus | 2 |

## Calibrated PnP - number-of-points sweep

### Solver overview - all subset sizes pooled (outlier-free conditions)

Success = rotation error <= 5 deg and relative translation error <= 5 %.

| solver | family | solves | returned (%) | success (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 836 | 78.2 | 71.7 | 0.141 | 3.357 | 1.33e-03 | 1.428 | 0.563 |
| dlt_lm | classic | 836 | 78.2 | 77.3 | 0.030 | 2.023 | 2.03e-04 | 0.189 | 5.097 |
| epnp | opencv | 956 | 100.0 | 81.5 | 0.074 | 14.7 | 9.29e-04 | 0.557 | 0.919 |
| epnp_lm | opencv | 956 | 100.0 | 91.1 | 0.048 | 9.598 | 3.40e-04 | 0.258 | 5.761 |
| p3p | opencv | 120 | 97.5 | 85.8 | 0.385 | 5.083 | 2.34e-03 | 1.282 | 0.836 |
| ap3p | opencv | 120 | 97.5 | 85.8 | 0.385 | 5.083 | 2.34e-03 | 1.282 | 0.759 |
| ippe | opencv | 209 | 99.5 | 95.2 | 0.067 | 1.761 | 5.45e-04 | 0.305 | 0.962 |
| iterative | opencv | 836 | 100.0 | 99.0 | 0.033 | 1.524 | 2.36e-04 | 0.210 | 3.303 |
| sqpnp | opencv | 956 | 100.0 | 99.2 | 0.044 | 0.523 | 3.75e-04 | 0.286 | 0.518 |
| ransac_dlt | robust-classic | 596 | 74.5 | 74.5 | 0.022 | 0.088 | 1.68e-04 | 0.155 | 19.1 |
| ransac_p3p | robust-classic | 716 | 100.0 | 99.9 | 0.029 | 0.157 | 2.14e-04 | 0.181 | 13.7 |
| cv_ransac_epnp | robust-opencv | 716 | 95.7 | 87.2 | 0.051 | 7.882 | 5.32e-04 | 0.382 | 2.869 |
| cv_ransac_epnp_lm | robust-opencv | 716 | 95.7 | 88.0 | 0.035 | 7.957 | 2.72e-04 | 0.239 | 8.027 |
| cv_ransac_ap3p | robust-opencv | 716 | 100.0 | 87.0 | 0.056 | 12.0 | 7.08e-04 | 0.461 | 2.965 |
| cv_usac_magsac | robust-opencv | 716 | 100.0 | 99.9 | 0.035 | 0.133 | 2.87e-04 | 0.217 | 7.062 |

### Median rotation error (deg) vs number of correspondences (outlier-free)

| solver | num_points_setting=4 | num_points_setting=6 | num_points_setting=8 | num_points_setting=12 | num_points_setting=20 | num_points_setting=50 | num_points_setting=100 | num_points_setting=500 |
|---|---|---|---|---|---|---|---|---|
| dlt | nan | 1.028 | 0.405 | 0.197 | 0.155 | 0.079 | 0.065 | 0.024 |
| dlt_lm | nan | 0.083 | 0.082 | 0.054 | 0.039 | 0.019 | 0.018 | 6.96e-03 |
| epnp | 7.274 | 0.129 | 0.125 | 0.089 | 0.070 | 0.044 | 0.032 | 0.017 |
| epnp_lm | 0.244 | 0.090 | 0.091 | 0.060 | 0.052 | 0.022 | 0.023 | 8.10e-03 |
| p3p | 0.385 | nan | nan | nan | nan | nan | nan | nan |
| ap3p | 0.385 | nan | nan | nan | nan | nan | nan | nan |
| ippe | 0.667 | 0.155 | 0.104 | 0.106 | 0.051 | 0.048 | 0.026 | 0.018 |
| iterative | nan | 0.090 | 0.085 | 0.062 | 0.041 | 0.022 | 0.019 | 8.02e-03 |
| sqpnp | 0.146 | 0.086 | 0.096 | 0.059 | 0.049 | 0.030 | 0.022 | 9.09e-03 |
| ransac_dlt | nan | nan | nan | 0.045 | 0.039 | 0.022 | 0.018 | 7.42e-03 |
| ransac_p3p | nan | nan | 0.084 | 0.060 | 0.051 | 0.022 | 0.019 | 7.29e-03 |
| cv_ransac_epnp | nan | nan | 0.107 | 0.062 | 0.074 | 0.051 | 0.030 | 0.019 |
| cv_ransac_epnp_lm | nan | nan | 0.088 | 0.053 | 0.052 | 0.027 | 0.027 | 0.015 |
| cv_ransac_ap3p | nan | nan | 0.131 | 0.086 | 0.078 | 0.050 | 0.039 | 0.027 |
| cv_usac_magsac | nan | nan | 0.099 | 0.060 | 0.056 | 0.030 | 0.026 | 9.21e-03 |

### Success rate (%) vs number of correspondences (outlier-free)

| solver | num_points_setting=4 | num_points_setting=6 | num_points_setting=8 | num_points_setting=12 | num_points_setting=20 | num_points_setting=50 | num_points_setting=100 | num_points_setting=500 |
|---|---|---|---|---|---|---|---|---|
| dlt | nan | 54.2 | 67.5 | 71.7 | 76.7 | 77.3 | 76.5 | 78.0 |
| dlt_lm | nan | 74.2 | 76.7 | 77.5 | 78.3 | 78.2 | 78.2 | 78.0 |
| epnp | 40.8 | 89.2 | 88.3 | 93.3 | 87.5 | 86.6 | 85.7 | 80.5 |
| epnp_lm | 79.2 | 94.2 | 92.5 | 96.7 | 92.5 | 93.3 | 91.6 | 89.0 |
| p3p | 85.8 | nan | nan | nan | nan | nan | nan | nan |
| ap3p | 85.8 | nan | nan | nan | nan | nan | nan | nan |
| ippe | 66.7 | 100.0 | 96.2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| iterative | nan | 95.8 | 98.3 | 99.2 | 100.0 | 100.0 | 100.0 | 100.0 |
| sqpnp | 94.2 | 100.0 | 99.2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| ransac_dlt | nan | nan | nan | 65.0 | 73.3 | 78.2 | 78.2 | 78.0 |
| ransac_p3p | nan | nan | 99.2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| cv_ransac_epnp | nan | nan | 88.3 | 93.3 | 87.5 | 86.6 | 86.6 | 80.5 |
| cv_ransac_epnp_lm | nan | nan | 90.0 | 93.3 | 87.5 | 88.2 | 87.4 | 81.4 |
| cv_ransac_ap3p | nan | nan | 89.2 | 92.5 | 87.5 | 86.6 | 85.7 | 80.5 |
| cv_usac_magsac | nan | nan | 100.0 | 99.2 | 100.0 | 100.0 | 100.0 | 100.0 |

### Median runtime (ms) vs number of correspondences (outlier-free)

| solver | num_points_setting=4 | num_points_setting=6 | num_points_setting=8 | num_points_setting=12 | num_points_setting=20 | num_points_setting=50 | num_points_setting=100 | num_points_setting=500 |
|---|---|---|---|---|---|---|---|---|
| dlt | nan | 0.457 | 0.459 | 0.541 | 0.547 | 0.678 | 0.713 | 1.356 |
| dlt_lm | nan | 5.230 | 5.051 | 4.990 | 4.746 | 4.968 | 5.037 | 6.747 |
| epnp | 0.896 | 0.868 | 0.869 | 0.891 | 0.899 | 0.922 | 0.944 | 1.241 |
| epnp_lm | 7.253 | 5.474 | 5.455 | 5.259 | 5.306 | 5.603 | 5.636 | 7.636 |
| p3p | 0.836 | nan | nan | nan | nan | nan | nan | nan |
| ap3p | 0.759 | nan | nan | nan | nan | nan | nan | nan |
| ippe | 0.841 | 0.922 | 0.926 | 0.936 | 0.947 | 0.973 | 1.045 | 1.457 |
| iterative | nan | 3.510 | 3.359 | 3.230 | 2.967 | 2.991 | 3.026 | 3.874 |
| sqpnp | 0.567 | 0.496 | 0.483 | 0.499 | 0.487 | 0.501 | 0.511 | 0.590 |
| ransac_dlt | nan | nan | nan | 18.4 | 18.7 | 19.0 | 18.0 | 23.3 |
| ransac_p3p | nan | nan | 12.5 | 13.7 | 12.7 | 13.4 | 13.4 | 17.3 |
| cv_ransac_epnp | nan | nan | 1.988 | 2.476 | 2.808 | 3.209 | 3.308 | 4.150 |
| cv_ransac_epnp_lm | nan | nan | 6.829 | 7.426 | 7.119 | 8.260 | 8.464 | 10.4 |
| cv_ransac_ap3p | nan | nan | 2.227 | 2.604 | 2.423 | 3.051 | 3.283 | 3.954 |
| cv_usac_magsac | nan | nan | 5.617 | 4.461 | 4.104 | 7.589 | 8.015 | 8.803 |

## Single-view calibration (uncalibrated DLT)

### Single-view uncalibrated DLT - overview

Success = mean focal-length error <= 5 % and rotation error <= 5 deg. Lens distortion is not modelled by the DLT, so distorted cameras show a systematic bias.

| solver | solves | returned (%) | success (%) | focal err median (%) | cx err median (px) | cy err median (px) | rot err median (deg) | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt_uncalibrated | 600 | 100.0 | 76.2 | 0.680 | 7.705 | 10.4 | 0.762 | 0.748 | 2.671 |
| dlt_uncalibrated_lm | 600 | 100.0 | 76.5 | 0.488 | 10.9 | 10.4 | 0.870 | 0.744 | 21.2 |

### Median focal-length error (%) by camera model

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| dlt_uncalibrated | 0.960 | 5.142 | 0.041 |
| dlt_uncalibrated_lm | 0.763 | 3.278 | 0.039 |

### Median focal-length error (%) by distortion level

| solver | distortion_level=mild | distortion_level=none | distortion_level=strong |
|---|---|---|---|
| dlt_uncalibrated | 1.709 | 0.041 | 3.314 |
| dlt_uncalibrated_lm | 1.429 | 0.039 | 1.875 |

### Median focal-length error (%) by field-of-view class

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| dlt_uncalibrated | 8.461 | 0.452 | 0.158 | 0.925 |
| dlt_uncalibrated_lm | 6.890 | 0.442 | 0.146 | 0.609 |

### Median focal-length error (%) by scene type

| solver | scene_type=depth_stratified | scene_type=mixed | scene_type=planar_multi | scene_type=volumetric |
|---|---|---|---|---|
| dlt_uncalibrated | 2.265 | 0.972 | 0.495 | 0.118 |
| dlt_uncalibrated_lm | 2.045 | 0.634 | 0.240 | 0.073 |

### Median focal-length error (%) vs noise sigma (pinhole cameras, no quantization)

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| dlt_uncalibrated | 9.99e-14 | 0.013 | 0.079 | 0.146 | 0.493 |
| dlt_uncalibrated_lm | 1.06e-14 | 0.012 | 0.103 | 0.145 | 0.361 |

## Multi-view calibration

### Multi-view calibration - overview

Each rig = all views sharing one intrinsic set and one noise condition. Success = mean focal error <= 1 % and mean rotation error <= 1 deg. `opencv` = calibrateCamera / fisheye.calibrate, `ba_scratch` = from-scratch bundle adjustment.

| solver | rigs | returned (%) | success (%) | focal err median (%) | cx err median (px) | dist coeff RMSE median | rot err median (deg) | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| opencv | 30 | 100.0 | 86.7 | 0.022 | 0.426 | 0.024 | 0.052 | 0.058 | 164.1 |
| ba_scratch | 30 | 100.0 | 93.3 | 0.014 | 0.196 | 0.020 | 0.033 | 0.043 | 4,089 |

### Median focal-length error (%) by camera model

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| ba_scratch | 6.87e-03 | 0.030 | 0.019 |
| opencv | 6.89e-03 | 6.478 | 0.018 |

### Success rate (%) by camera model

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| ba_scratch | 92.9 | 100.0 | 90.9 |
| opencv | 100.0 | 40.0 | 90.9 |

### Median focal-length error (%) by field-of-view class

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| ba_scratch | 0.040 | 0.185 | 4.79e-03 | 8.21e-03 |
| opencv | 0.041 | 0.123 | 4.79e-03 | 0.025 |

### Success rate (%) by field-of-view class

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| ba_scratch | 100.0 | 75.0 | 93.3 | 100.0 |
| opencv | 100.0 | 100.0 | 93.3 | 66.7 |

### Median focal-length error (%) by noise sigma

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| ba_scratch | 5.41e-10 | 8.21e-03 | 9.65e-03 | 0.026 | 0.090 |
| opencv | 7.90e-07 | 8.18e-03 | 9.83e-03 | 0.026 | 0.092 |

### Success rate (%) by noise sigma

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| ba_scratch | 100.0 | 100.0 | 100.0 | 100.0 | 66.7 |
| opencv | 85.7 | 100.0 | 77.8 | 100.0 | 83.3 |

### Median focal-length error (%) by scene type

| solver | scene_type=depth_stratified | scene_type=mixed | scene_type=planar_multi | scene_type=volumetric |
|---|---|---|---|---|
| ba_scratch | 0.016 | 0.015 | 0.014 | 0.019 |
| opencv | 0.016 | 0.248 | 0.014 | 0.019 |

### Success rate (%) by scene type

| solver | scene_type=depth_stratified | scene_type=mixed | scene_type=planar_multi | scene_type=volumetric |
|---|---|---|---|---|
| ba_scratch | 100.0 | 83.3 | 90.0 | 100.0 |
| opencv | 100.0 | 66.7 | 80.0 | 100.0 |
