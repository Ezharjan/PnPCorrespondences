# Benchmark summary

Environment: pnpcorr_version=1.0.0, python=3.11.15, platform=Linux-6.18.44-fc-v24-x86_64-with-glibc2.39, processor=x86_64, numpy=2.4.4, pandas=3.0.2, opencv=4.13.0

## Calibrated PnP

### Solver overview - all conditions

Success = rotation error <= 5 deg and relative translation error <= 5 %. Errors are medians over every evaluated sample (all visible correspondences).

| solver | family | solves | returned (%) | success (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 600 | 80.3 | 37.8 | 5.909 | 47.3 | 0.063 | 0.376 | 1.939 |
| dlt_lm | classic | 600 | 80.3 | 42.0 | 0.749 | 42.3 | 0.039 | 0.058 | 10.6 |
| epnp | opencv | 600 | 100.0 | 45.2 | 2.196 | 37.4 | 0.128 | 19.7 | 1.435 |
| epnp_lm | opencv | 600 | 100.0 | 49.8 | 1.257 | 21.9 | 0.049 | 12.6 | 10.4 |
| ippe | opencv | 118 | 100.0 | 45.8 | 2.271 | 49.6 | 0.184 | 0.140 | 1.501 |
| iterative | opencv | 600 | 100.0 | 49.3 | 1.414 | 44.2 | 0.057 | 0.068 | 9.432 |
| sqpnp | opencv | 600 | 100.0 | 46.8 | 2.392 | 33.4 | 0.190 | 0.080 | 0.892 |
| ransac_dlt | robust-classic | 600 | 67.7 | 67.3 | 7.60e-03 | 0.037 | 5.94e-05 | 0.047 | 53.2 |
| ransac_p3p | robust-classic | 600 | 99.7 | 93.7 | 8.92e-03 | 6.650 | 6.23e-05 | 0.044 | 25.6 |
| cv_ransac_epnp | robust-opencv | 600 | 89.3 | 82.0 | 0.013 | 6.410 | 1.77e-04 | 0.106 | 11.7 |
| cv_ransac_epnp_lm | robust-opencv | 600 | 89.3 | 83.0 | 0.010 | 6.624 | 8.18e-05 | 0.058 | 18.2 |
| cv_ransac_ap3p | robust-opencv | 600 | 99.8 | 87.2 | 0.019 | 12.3 | 2.42e-04 | 0.155 | 7.756 |
| cv_usac_magsac | robust-opencv | 600 | 100.0 | 95.2 | 0.010 | 5.757 | 8.35e-05 | 0.057 | 11.4 |

### Solver overview - outlier-free conditions (noise / quantization only)

| solver | family | solves | returned (%) | success (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 280 | 80.7 | 80.7 | 0.017 | 0.058 | 1.49e-04 | 0.122 | 1.902 |
| dlt_lm | classic | 280 | 80.7 | 80.7 | 4.97e-03 | 0.012 | 3.63e-05 | 0.031 | 7.944 |
| epnp | opencv | 280 | 100.0 | 91.1 | 8.73e-03 | 7.984 | 1.14e-04 | 0.070 | 1.395 |
| epnp_lm | opencv | 280 | 100.0 | 93.9 | 5.63e-03 | 6.024 | 4.01e-05 | 0.032 | 7.417 |
| ippe | opencv | 54 | 100.0 | 100.0 | 0.011 | 0.032 | 6.14e-05 | 0.038 | 1.477 |
| iterative | opencv | 280 | 100.0 | 100.0 | 5.69e-03 | 0.016 | 3.96e-05 | 0.032 | 4.542 |
| sqpnp | opencv | 280 | 100.0 | 100.0 | 6.36e-03 | 0.016 | 6.39e-05 | 0.039 | 0.640 |
| ransac_dlt | robust-classic | 280 | 79.3 | 79.3 | 5.67e-03 | 0.018 | 4.38e-05 | 0.032 | 27.6 |
| ransac_p3p | robust-classic | 280 | 100.0 | 100.0 | 5.68e-03 | 0.014 | 3.67e-05 | 0.031 | 20.2 |
| cv_ransac_epnp | robust-opencv | 280 | 100.0 | 91.1 | 0.010 | 7.367 | 1.26e-04 | 0.093 | 3.901 |
| cv_ransac_epnp_lm | robust-opencv | 280 | 100.0 | 92.5 | 7.49e-03 | 7.405 | 6.51e-05 | 0.040 | 10.5 |
| cv_ransac_ap3p | robust-opencv | 280 | 100.0 | 91.4 | 0.013 | 7.997 | 1.74e-04 | 0.143 | 3.973 |
| cv_usac_magsac | robust-opencv | 280 | 100.0 | 100.0 | 6.46e-03 | 0.026 | 6.04e-05 | 0.043 | 8.428 |

### Solver overview - conditions with outliers

| solver | family | solves | returned (%) | success (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 320 | 80.0 | 0.312 | 76.1 | 89.0 | 0.894 | 307.0 | 1.997 |
| dlt_lm | classic | 320 | 80.0 | 8.125 | 68.1 | 79.7 | 0.928 | 62.9 | 20.3 |
| epnp | opencv | 320 | 100.0 | 5.000 | 48.0 | 63.2 | 0.908 | 220.4 | 1.459 |
| epnp_lm | opencv | 320 | 100.0 | 11.2 | 6.384 | 35.8 | 0.872 | 91.1 | 15.9 |
| ippe | opencv | 64 | 100.0 | 0 | 107.7 | 91.5 | 0.857 | 151.5 | 1.526 |
| iterative | opencv | 320 | 100.0 | 5.000 | 69.6 | 82.8 | 1.016 | 67.5 | 22.9 |
| sqpnp | opencv | 320 | 100.0 | 0.312 | 49.6 | 62.6 | 0.774 | 158.1 | 1.130 |
| ransac_dlt | robust-classic | 320 | 57.5 | 56.9 | 9.60e-03 | 0.060 | 7.78e-05 | 0.053 | 511.9 |
| ransac_p3p | robust-classic | 320 | 99.4 | 88.1 | 0.012 | 12.5 | 9.10e-05 | 0.054 | 48.8 |
| cv_ransac_epnp | robust-opencv | 320 | 80.0 | 74.1 | 0.015 | 5.365 | 1.97e-04 | 0.116 | 131.3 |
| cv_ransac_epnp_lm | robust-opencv | 320 | 80.0 | 74.7 | 0.012 | 5.770 | 8.94e-05 | 0.066 | 138.7 |
| cv_ransac_ap3p | robust-opencv | 320 | 99.7 | 83.4 | 0.025 | 16.1 | 3.00e-04 | 0.168 | 54.9 |
| cv_usac_magsac | robust-opencv | 320 | 100.0 | 90.9 | 0.014 | 10.8 | 1.02e-04 | 0.067 | 17.3 |

### Median rotation error (deg) vs Gaussian pixel noise sigma (outlier-free)

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| dlt | 5.13e-14 | 4.64e-03 | 0.024 | 0.042 | 0.087 |
| dlt_lm | 8.45e-15 | 1.54e-03 | 5.69e-03 | 0.012 | 0.031 |
| epnp | 5.00e-13 | 2.18e-03 | 8.81e-03 | 0.016 | 0.042 |
| epnp_lm | 8.39e-15 | 1.58e-03 | 6.68e-03 | 0.013 | 0.032 |
| ippe | 9.08e-14 | 2.24e-03 | 0.014 | 0.019 | 0.044 |
| iterative | 2.03e-14 | 1.62e-03 | 6.43e-03 | 0.013 | 0.030 |
| sqpnp | 1.33e-12 | 1.83e-03 | 6.69e-03 | 0.014 | 0.033 |
| ransac_dlt | 8.45e-15 | 1.54e-03 | 7.21e-03 | 0.015 | 0.034 |
| ransac_p3p | 8.45e-15 | 1.54e-03 | 6.73e-03 | 0.014 | 0.033 |
| cv_ransac_epnp | 3.49e-07 | 2.16e-03 | 0.010 | 0.029 | 0.076 |
| cv_ransac_epnp_lm | 8.45e-15 | 1.60e-03 | 7.83e-03 | 0.025 | 0.072 |
| cv_ransac_ap3p | 3.49e-07 | 2.09e-03 | 0.017 | 0.064 | 0.136 |
| cv_usac_magsac | 3.36e-05 | 1.91e-03 | 8.39e-03 | 0.015 | 0.040 |

### Median reprojection RMSE (px) vs noise sigma (outlier-free)

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| dlt | 5.27e-13 | 0.037 | 0.290 | 0.343 | 0.439 |
| dlt_lm | 1.36e-13 | 6.53e-03 | 0.034 | 0.063 | 0.125 |
| epnp | 6.60e-12 | 0.012 | 0.071 | 0.104 | 0.204 |
| epnp_lm | 1.23e-13 | 6.81e-03 | 0.035 | 0.068 | 0.125 |
| ippe | 7.13e-13 | 0.010 | 0.041 | 0.055 | 0.220 |
| iterative | 2.33e-13 | 6.96e-03 | 0.033 | 0.066 | 0.129 |
| sqpnp | 1.32e-11 | 9.58e-03 | 0.043 | 0.082 | 0.159 |
| ransac_dlt | 1.36e-13 | 6.53e-03 | 0.048 | 0.117 | 0.187 |
| ransac_p3p | 1.36e-13 | 6.81e-03 | 0.040 | 0.080 | 0.157 |
| cv_ransac_epnp | 2.51e-06 | 0.011 | 0.095 | 0.189 | 0.364 |
| cv_ransac_epnp_lm | 1.31e-13 | 7.38e-03 | 0.050 | 0.179 | 0.342 |
| cv_ransac_ap3p | 2.51e-06 | 0.012 | 0.215 | 0.314 | 0.635 |
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
| ransac_dlt | 8.45e-15 | 3.90e-03 | 7.21e-03 | 7.70e-03 |
| ransac_p3p | 8.45e-15 | 3.88e-03 | 6.73e-03 | 6.96e-03 |
| cv_ransac_epnp | 3.49e-07 | 6.09e-03 | 0.010 | 0.012 |
| cv_ransac_epnp_lm | 8.45e-15 | 4.86e-03 | 7.83e-03 | 9.70e-03 |
| cv_ransac_ap3p | 3.49e-07 | 6.56e-03 | 0.017 | 0.014 |
| cv_usac_magsac | 3.36e-05 | 4.58e-03 | 8.39e-03 | 8.45e-03 |

### Success rate (%) vs outlier ratio (uniform outliers, sigma = 0.5 px)

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| dlt | 81.1 | 2.222 | 0 | 0 | 0 | 0 |
| dlt_lm | 81.1 | 40.0 | 10.5 | 0 | 0 | 0 |
| epnp | 91.9 | 35.6 | 0 | 0 | 0 | 0 |
| epnp_lm | 97.3 | 60.0 | 7.895 | 0 | 0 | 0 |
| ippe | 100.0 | 0 | 0 | 0 | 0 | 0 |
| iterative | 100.0 | 35.6 | 0 | 0 | 0 | 0 |
| sqpnp | 100.0 | 2.222 | 0 | 0 | 0 | 0 |
| ransac_dlt | 75.7 | 82.2 | 78.9 | 71.4 | 4.545 | 0 |
| ransac_p3p | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 7.317 |
| cv_ransac_epnp | 91.9 | 95.6 | 92.1 | 90.5 | 43.2 | 0 |
| cv_ransac_epnp_lm | 91.9 | 95.6 | 92.1 | 92.9 | 43.2 | 0 |
| cv_ransac_ap3p | 91.9 | 95.6 | 92.1 | 92.9 | 93.2 | 19.5 |
| cv_usac_magsac | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 29.3 |

### Median rotation error (deg) vs outlier ratio (uniform outliers, sigma = 0.5 px)

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| dlt | 0.024 | 21.1 | 75.3 | 79.1 | 118.5 | 133.4 |
| dlt_lm | 5.69e-03 | 1.629 | 45.7 | 77.3 | 117.0 | 132.3 |
| epnp | 8.81e-03 | 2.334 | 18.2 | 90.0 | 80.0 | 102.2 |
| epnp_lm | 6.68e-03 | 1.393 | 3.737 | 11.7 | 31.3 | 91.9 |
| ippe | 0.014 | 2.415 | 106.6 | 158.8 | 149.7 | 120.2 |
| iterative | 6.43e-03 | 2.813 | 14.0 | 89.1 | 135.1 | 157.7 |
| sqpnp | 6.69e-03 | 8.747 | 34.7 | 75.1 | 112.0 | 120.3 |
| ransac_dlt | 7.21e-03 | 6.33e-03 | 6.28e-03 | 0.011 | 0.109 | nan |
| ransac_p3p | 6.73e-03 | 7.41e-03 | 5.87e-03 | 9.81e-03 | 0.015 | 106.8 |
| cv_ransac_epnp | 0.010 | 9.41e-03 | 0.011 | 0.015 | 0.076 | nan |
| cv_ransac_epnp_lm | 7.83e-03 | 0.010 | 7.72e-03 | 0.013 | 0.039 | nan |
| cv_ransac_ap3p | 0.017 | 0.012 | 0.016 | 0.015 | 0.028 | 102.0 |
| cv_usac_magsac | 8.39e-03 | 7.25e-03 | 9.19e-03 | 9.96e-03 | 0.015 | 92.5 |

### Median inlier precision of robust solvers vs outlier ratio

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| ransac_dlt | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | nan |
| ransac_p3p | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.200 |
| cv_ransac_epnp | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | nan |
| cv_ransac_epnp_lm | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | nan |
| cv_ransac_ap3p | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.100 |
| cv_usac_magsac | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |

### Median inlier recall of robust solvers vs outlier ratio

| solver | outlier_ratio=0.0 | outlier_ratio=0.05 | outlier_ratio=0.2 | outlier_ratio=0.5 | outlier_ratio=0.8 | outlier_ratio=0.95 |
|---|---|---|---|---|---|---|
| ransac_dlt | 0.999 | 0.999 | 0.999 | 1.000 | 0.997 | nan |
| ransac_p3p | 0.999 | 0.999 | 1.000 | 1.000 | 1.000 | 0.010 |
| cv_ransac_epnp | 0.973 | 0.969 | 0.985 | 0.986 | 0.699 | nan |
| cv_ransac_epnp_lm | 0.999 | 0.999 | 0.999 | 0.999 | 0.985 | nan |
| cv_ransac_ap3p | 0.946 | 0.959 | 0.968 | 0.984 | 0.984 | 4.67e-03 |
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
| ransac_dlt | 82.1 | 78.9 | 65.8 | 71.4 |
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
| sqpnp | 4.79e-03 | 5.51e-03 | 7.37e-03 | 0.011 | 5.67e-03 |
| ransac_dlt | 2.64e-03 | 6.68e-03 | 6.11e-03 | nan | 6.63e-03 |
| ransac_p3p | 2.13e-03 | 6.01e-03 | 6.56e-03 | 6.47e-03 | 6.63e-03 |
| cv_ransac_epnp | 6.10e-03 | 6.28e-03 | 0.011 | 0.359 | 5.91e-03 |
| cv_ransac_epnp_lm | 3.56e-03 | 5.73e-03 | 7.56e-03 | 0.144 | 6.63e-03 |
| cv_ransac_ap3p | 7.16e-03 | 8.68e-03 | 0.019 | 0.174 | 0.010 |
| cv_usac_magsac | 4.84e-03 | 5.36e-03 | 8.27e-03 | 8.55e-03 | 8.45e-03 |

### Median rotation error (deg) by camera model (outlier-free conditions)

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| dlt | 0.015 | 0.015 | 0.031 |
| dlt_lm | 3.91e-03 | 5.31e-03 | 5.36e-03 |
| epnp | 5.94e-03 | 0.011 | 0.012 |
| epnp_lm | 4.54e-03 | 6.92e-03 | 5.62e-03 |
| ippe | 5.59e-03 | 0.032 | 0.018 |
| iterative | 3.91e-03 | 5.94e-03 | 7.61e-03 |
| sqpnp | 3.77e-03 | 7.89e-03 | 7.66e-03 |
| ransac_dlt | 3.69e-03 | 7.55e-03 | 5.86e-03 |
| ransac_p3p | 4.03e-03 | 9.00e-03 | 5.72e-03 |
| cv_ransac_epnp | 5.57e-03 | 0.014 | 0.012 |
| cv_ransac_epnp_lm | 5.18e-03 | 0.012 | 7.69e-03 |
| cv_ransac_ap3p | 7.79e-03 | 0.017 | 0.018 |
| cv_usac_magsac | 4.89e-03 | 8.01e-03 | 8.39e-03 |

### Median rotation error (deg) by field-of-view class (outlier-free conditions)

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| dlt | 8.61e-03 | 0.048 | 0.015 | 0.016 |
| dlt_lm | 4.94e-03 | 4.19e-03 | 5.02e-03 | 5.46e-03 |
| epnp | 7.73e-03 | 6.07e-03 | 7.95e-03 | 0.012 |
| epnp_lm | 4.94e-03 | 5.85e-03 | 4.96e-03 | 6.95e-03 |
| ippe | nan | 7.08e-03 | 0.017 | 0.022 |
| iterative | 4.94e-03 | 4.47e-03 | 5.47e-03 | 7.24e-03 |
| sqpnp | 7.00e-03 | 3.39e-03 | 6.37e-03 | 9.32e-03 |
| ransac_dlt | 6.83e-03 | 4.18e-03 | 4.75e-03 | 7.19e-03 |
| ransac_p3p | 9.62e-03 | 4.47e-03 | 4.96e-03 | 6.54e-03 |
| cv_ransac_epnp | 0.013 | 4.94e-03 | 8.65e-03 | 0.014 |
| cv_ransac_epnp_lm | 0.010 | 5.87e-03 | 5.35e-03 | 9.76e-03 |
| cv_ransac_ap3p | 0.015 | 0.010 | 0.011 | 0.017 |
| cv_usac_magsac | 6.81e-03 | 6.52e-03 | 4.84e-03 | 8.02e-03 |

### Median rotation error (deg) by distortion level (outlier-free conditions)

| solver | distortion_level=mild | distortion_level=none | distortion_level=strong |
|---|---|---|---|
| dlt | 0.021 | 0.031 | 0.011 |
| dlt_lm | 4.72e-03 | 5.36e-03 | 4.74e-03 |
| epnp | 6.90e-03 | 0.012 | 9.00e-03 |
| epnp_lm | 5.73e-03 | 5.62e-03 | 5.53e-03 |
| ippe | 6.02e-03 | 0.018 | 0.028 |
| iterative | 4.72e-03 | 7.61e-03 | 5.09e-03 |
| sqpnp | 5.27e-03 | 7.66e-03 | 6.01e-03 |
| ransac_dlt | 5.07e-03 | 5.86e-03 | 5.30e-03 |
| ransac_p3p | 5.08e-03 | 5.72e-03 | 5.87e-03 |
| cv_ransac_epnp | 7.86e-03 | 0.012 | 0.011 |
| cv_ransac_epnp_lm | 7.36e-03 | 7.69e-03 | 8.23e-03 |
| cv_ransac_ap3p | 0.010 | 0.018 | 0.012 |
| cv_usac_magsac | 6.36e-03 | 8.39e-03 | 5.42e-03 |

### Runtime per solve (all visible correspondences)

| solver | runtime median (ms) | runtime mean (ms) | runtime max (ms) |
|---|---|---|---|
| dlt | 1.939 | 2.303 | 116.0 |
| dlt_lm | 10.6 | 55.0 | 501.2 |
| epnp | 1.435 | 1.413 | 4.078 |
| epnp_lm | 10.4 | 28.2 | 357.2 |
| ippe | 1.501 | 1.514 | 2.112 |
| iterative | 9.432 | 15.1 | 44.1 |
| sqpnp | 0.892 | 1.003 | 4.649 |
| ransac_dlt | 53.2 | 363.9 | 1,497 |
| ransac_p3p | 25.6 | 165.3 | 2,250 |
| cv_ransac_epnp | 11.7 | 367.6 | 1,758 |
| cv_ransac_epnp_lm | 18.2 | 373.1 | 1,798 |
| cv_ransac_ap3p | 7.756 | 204.8 | 1,518 |
| cv_usac_magsac | 11.4 | 37.7 | 467.2 |

### Failure reasons (solver returned no estimate)

| solver | failure_reason | count |
|---|---|---|
| cv_ransac_ap3p | opencv: ransac found no consensus | 1 |
| cv_ransac_epnp | opencv: ransac found no consensus | 64 |
| cv_ransac_epnp_lm | opencv: ransac found no consensus | 64 |
| dlt | degenerate: coplanar points | 118 |
| dlt_lm | degenerate: coplanar points | 118 |
| ransac_dlt | degenerate: coplanar points | 118 |
| ransac_dlt | ransac: no consensus | 76 |
| ransac_p3p | ransac: no consensus | 2 |

## Calibrated PnP - number-of-points sweep

### Solver overview - all subset sizes pooled (outlier-free conditions)

Success = rotation error <= 5 deg and relative translation error <= 5 %.

| solver | family | solves | returned (%) | success (%) | rot err median (deg) | rot err mean (deg) | trans err rel median | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt | classic | 836 | 78.1 | 72.1 | 0.164 | 2.359 | 1.14e-03 | 1.495 | 0.571 |
| dlt_lm | classic | 836 | 78.1 | 77.8 | 0.029 | 0.918 | 2.29e-04 | 0.175 | 5.288 |
| epnp | opencv | 956 | 100.0 | 81.1 | 0.077 | 15.9 | 1.02e-03 | 0.597 | 0.929 |
| epnp_lm | opencv | 956 | 100.0 | 90.8 | 0.042 | 11.0 | 3.31e-04 | 0.239 | 5.823 |
| p3p | opencv | 120 | 98.3 | 90.8 | 0.305 | 2.280 | 2.16e-03 | 1.105 | 0.840 |
| ap3p | opencv | 120 | 98.3 | 90.8 | 0.305 | 2.280 | 2.16e-03 | 1.105 | 0.770 |
| ippe | opencv | 212 | 99.5 | 97.2 | 0.070 | 1.345 | 5.14e-04 | 0.312 | 0.975 |
| iterative | opencv | 836 | 100.0 | 99.4 | 0.032 | 1.004 | 2.55e-04 | 0.194 | 3.301 |
| sqpnp | opencv | 956 | 100.0 | 99.7 | 0.041 | 0.493 | 3.76e-04 | 0.281 | 0.539 |
| ransac_dlt | robust-classic | 596 | 74.8 | 74.7 | 0.022 | 0.086 | 1.75e-04 | 0.135 | 20.6 |
| ransac_p3p | robust-classic | 716 | 100.0 | 100.0 | 0.028 | 0.103 | 2.09e-04 | 0.171 | 14.5 |
| cv_ransac_epnp | robust-opencv | 716 | 96.1 | 86.9 | 0.051 | 8.482 | 6.18e-04 | 0.407 | 2.834 |
| cv_ransac_epnp_lm | robust-opencv | 716 | 96.1 | 87.7 | 0.036 | 8.672 | 2.96e-04 | 0.227 | 8.312 |
| cv_ransac_ap3p | robust-opencv | 716 | 100.0 | 86.3 | 0.059 | 12.4 | 6.93e-04 | 0.492 | 3.066 |
| cv_usac_magsac | robust-opencv | 716 | 100.0 | 99.7 | 0.035 | 0.180 | 2.61e-04 | 0.212 | 6.847 |

### Median rotation error (deg) vs number of correspondences (outlier-free)

| solver | num_points_setting=4 | num_points_setting=6 | num_points_setting=8 | num_points_setting=12 | num_points_setting=20 | num_points_setting=50 | num_points_setting=100 | num_points_setting=500 |
|---|---|---|---|---|---|---|---|---|
| dlt | nan | 1.208 | 0.461 | 0.258 | 0.160 | 0.087 | 0.055 | 0.024 |
| dlt_lm | nan | 0.098 | 0.069 | 0.049 | 0.032 | 0.024 | 0.015 | 6.32e-03 |
| epnp | 4.669 | 0.156 | 0.097 | 0.119 | 0.074 | 0.043 | 0.034 | 0.018 |
| epnp_lm | 0.301 | 0.107 | 0.074 | 0.067 | 0.034 | 0.025 | 0.017 | 7.82e-03 |
| p3p | 0.305 | nan | nan | nan | nan | nan | nan | nan |
| ap3p | 0.305 | nan | nan | nan | nan | nan | nan | nan |
| ippe | 0.499 | 0.216 | 0.144 | 0.094 | 0.063 | 0.049 | 0.035 | 0.019 |
| iterative | nan | 0.100 | 0.069 | 0.054 | 0.035 | 0.025 | 0.016 | 7.82e-03 |
| sqpnp | 0.145 | 0.103 | 0.079 | 0.063 | 0.039 | 0.032 | 0.021 | 7.81e-03 |
| ransac_dlt | nan | nan | nan | 0.043 | 0.036 | 0.024 | 0.016 | 7.51e-03 |
| ransac_p3p | nan | nan | 0.072 | 0.054 | 0.033 | 0.025 | 0.016 | 7.26e-03 |
| cv_ransac_epnp | nan | nan | 0.093 | 0.096 | 0.060 | 0.038 | 0.037 | 0.018 |
| cv_ransac_epnp_lm | nan | nan | 0.073 | 0.056 | 0.036 | 0.032 | 0.022 | 0.015 |
| cv_ransac_ap3p | nan | nan | 0.095 | 0.114 | 0.076 | 0.040 | 0.035 | 0.020 |
| cv_usac_magsac | nan | nan | 0.078 | 0.065 | 0.042 | 0.034 | 0.022 | 0.011 |

### Success rate (%) vs number of correspondences (outlier-free)

| solver | num_points_setting=4 | num_points_setting=6 | num_points_setting=8 | num_points_setting=12 | num_points_setting=20 | num_points_setting=50 | num_points_setting=100 | num_points_setting=500 |
|---|---|---|---|---|---|---|---|---|
| dlt | nan | 60.0 | 65.0 | 71.7 | 75.8 | 76.5 | 78.2 | 78.0 |
| dlt_lm | nan | 76.7 | 76.7 | 78.3 | 78.3 | 78.2 | 78.2 | 78.0 |
| epnp | 45.8 | 85.8 | 90.0 | 86.7 | 87.5 | 84.9 | 84.0 | 83.9 |
| epnp_lm | 75.8 | 90.8 | 94.2 | 91.7 | 95.0 | 95.0 | 92.4 | 91.5 |
| p3p | 90.8 | nan | nan | nan | nan | nan | nan | nan |
| ap3p | 90.8 | nan | nan | nan | nan | nan | nan | nan |
| ippe | 86.2 | 92.6 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| iterative | nan | 98.3 | 98.3 | 99.2 | 100.0 | 100.0 | 100.0 | 100.0 |
| sqpnp | 98.3 | 99.2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| ransac_dlt | nan | nan | nan | 65.8 | 75.0 | 77.3 | 78.2 | 77.1 |
| ransac_p3p | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| cv_ransac_epnp | nan | nan | 90.8 | 86.7 | 88.3 | 85.7 | 84.9 | 84.7 |
| cv_ransac_epnp_lm | nan | nan | 91.7 | 87.5 | 89.2 | 86.6 | 85.7 | 85.6 |
| cv_ransac_ap3p | nan | nan | 90.0 | 86.7 | 87.5 | 85.7 | 84.0 | 83.9 |
| cv_usac_magsac | nan | nan | 98.3 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

### Median runtime (ms) vs number of correspondences (outlier-free)

| solver | num_points_setting=4 | num_points_setting=6 | num_points_setting=8 | num_points_setting=12 | num_points_setting=20 | num_points_setting=50 | num_points_setting=100 | num_points_setting=500 |
|---|---|---|---|---|---|---|---|---|
| dlt | nan | 0.478 | 0.462 | 0.547 | 0.567 | 0.681 | 0.698 | 1.377 |
| dlt_lm | nan | 5.333 | 4.955 | 5.196 | 4.940 | 4.951 | 5.374 | 6.941 |
| epnp | 0.917 | 0.887 | 0.865 | 0.907 | 0.929 | 0.929 | 0.959 | 1.191 |
| epnp_lm | 7.045 | 5.495 | 5.525 | 5.634 | 5.424 | 5.601 | 5.711 | 7.117 |
| p3p | 0.840 | nan | nan | nan | nan | nan | nan | nan |
| ap3p | 0.770 | nan | nan | nan | nan | nan | nan | nan |
| ippe | 0.887 | 0.942 | 0.913 | 0.953 | 0.978 | 0.992 | 1.146 | 1.467 |
| iterative | nan | 3.554 | 3.388 | 3.104 | 3.044 | 3.027 | 3.095 | 3.867 |
| sqpnp | 0.601 | 0.504 | 0.490 | 0.506 | 0.535 | 0.521 | 0.527 | 0.609 |
| ransac_dlt | nan | nan | nan | 20.4 | 17.2 | 19.3 | 20.1 | 23.9 |
| ransac_p3p | nan | nan | 12.5 | 14.1 | 13.4 | 13.7 | 14.7 | 17.7 |
| cv_ransac_epnp | nan | nan | 1.962 | 2.162 | 3.101 | 3.231 | 3.544 | 3.988 |
| cv_ransac_epnp_lm | nan | nan | 6.766 | 7.754 | 7.954 | 7.939 | 9.038 | 10.5 |
| cv_ransac_ap3p | nan | nan | 2.158 | 2.375 | 3.172 | 3.154 | 3.601 | 4.208 |
| cv_usac_magsac | nan | nan | 5.310 | 4.421 | 4.473 | 8.091 | 8.235 | 9.147 |

## Single-view calibration (uncalibrated DLT)

### Single-view uncalibrated DLT - overview

Success = mean focal-length error <= 5 % and rotation error <= 5 deg. Lens distortion is not modelled by the DLT, so distorted cameras show a systematic bias.

| solver | solves | returned (%) | success (%) | focal err median (%) | cx err median (px) | cy err median (px) | rot err median (deg) | reproj RMSE median (px) | runtime median (ms) |
|---|---|---|---|---|---|---|---|---|---|
| dlt_uncalibrated | 600 | 100.0 | 76.2 | 0.680 | 7.705 | 10.4 | 0.762 | 0.748 | 2.886 |
| dlt_uncalibrated_lm | 600 | 100.0 | 76.5 | 0.488 | 10.9 | 10.4 | 0.870 | 0.744 | 22.3 |

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
| opencv | 30 | 100.0 | 86.7 | 0.022 | 0.426 | 0.024 | 0.052 | 0.058 | 156.7 |
| ba_scratch | 30 | 100.0 | 96.7 | 7.50e-03 | 0.123 | 8.71e-05 | 0.022 | 0.041 | 1,545 |

### Median focal-length error (%) by camera model

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| ba_scratch | 6.87e-03 | 0.030 | 4.99e-03 |
| opencv | 6.89e-03 | 6.478 | 0.018 |

### Success rate (%) by camera model

| solver | camera_model=brown_conrady | camera_model=kannala_brandt | camera_model=pinhole |
|---|---|---|---|
| ba_scratch | 92.9 | 100.0 | 100.0 |
| opencv | 100.0 | 40.0 | 90.9 |

### Median focal-length error (%) by field-of-view class

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| ba_scratch | 0.040 | 0.185 | 4.08e-03 | 1.82e-03 |
| opencv | 0.041 | 0.123 | 4.79e-03 | 0.025 |

### Success rate (%) by field-of-view class

| solver | fov_class=fisheye | fov_class=narrow | fov_class=normal | fov_class=wide |
|---|---|---|---|---|
| ba_scratch | 100.0 | 75.0 | 100.0 | 100.0 |
| opencv | 100.0 | 100.0 | 93.3 | 66.7 |

### Median focal-length error (%) by noise sigma

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| ba_scratch | 5.41e-10 | 3.96e-03 | 9.65e-03 | 4.99e-03 | 0.090 |
| opencv | 7.90e-07 | 8.18e-03 | 9.83e-03 | 0.026 | 0.092 |

### Success rate (%) by noise sigma

| solver | noise_sigma=0.0 | noise_sigma=0.1 | noise_sigma=0.5 | noise_sigma=1.0 | noise_sigma=2.0 |
|---|---|---|---|---|---|
| ba_scratch | 100.0 | 100.0 | 100.0 | 100.0 | 83.3 |
| opencv | 85.7 | 100.0 | 77.8 | 100.0 | 83.3 |

### Median focal-length error (%) by scene type

| solver | scene_type=depth_stratified | scene_type=mixed | scene_type=planar_multi | scene_type=volumetric |
|---|---|---|---|---|
| ba_scratch | 4.16e-03 | 0.015 | 0.017 | 0.019 |
| opencv | 0.016 | 0.248 | 0.014 | 0.019 |

### Success rate (%) by scene type

| solver | scene_type=depth_stratified | scene_type=mixed | scene_type=planar_multi | scene_type=volumetric |
|---|---|---|---|---|
| ba_scratch | 100.0 | 83.3 | 100.0 | 100.0 |
| opencv | 100.0 | 66.7 | 80.0 | 100.0 |
