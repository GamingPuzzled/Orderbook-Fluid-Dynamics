# Parametric refill models: out-of-sample comparison

Data: excess near build-up N(w) and deep depletion J(w) per window, 20–1000 ms (10 windows × 2 series), deep book d > 5, state-matched placebo. Rates are gamma pulses (k = 1: exponential from the sweep; k = 2: delayed hump). Weighted least squares with day-bootstrap standard errors; CV: 5 folds over days. Lower cv_chi2 / AIC / BIC is better; cv_r2 is out-of-sample R² relative to predicting zero. K, K3, P: Hawkes-type impulse responses. Q, Q+: queue-reactive benchmarks given the observed book state at each window start (params = binned intensity values; no AIC/BIC).

| model | description | params | χ² | AIC | BIC | in-sample R² | CV χ² | CV R² |
|---|---|---|---|---|---|---|---|---|
| A | exponential recovery (near inflow only) | 2 | 422.5 | 426.5 | 428.5 | 0.007 | 2533.1 | 0.006 |
| B | replenish + cancel (two exponentials) | 4 | 363.1 | 371.1 | 375.1 | 0.803 | 2244.6 | 0.729 |
| C | withdrawal + delayed source (no move) | 4 | 375.7 | 383.7 | 387.7 | 0.802 | 2351.8 | 0.727 |
| D | withdrawal + move (no new liquidity) | 4 | 434.7 | 442.7 | 446.7 | 0.780 | 2627.6 | 0.707 |
| E | three-phase: withdrawal + move + delayed source | 6 | 373.0 | 385.0 | 390.9 | 0.800 | 2360.1 | 0.725 |
| F | three-phase, free shapes | 9 | 359.3 | 377.3 | 386.3 | 0.803 | 2276.5 | 0.728 |
| G | three-phase + late withdrawal | 8 | 372.9 | 388.9 | 396.9 | 0.800 | 2360.0 | 0.725 |
| H | early + late withdrawal + delayed source (no move) | 6 | 375.6 | 387.6 | 393.6 | 0.802 | 2351.5 | 0.727 |
| I | three-phase + late move | 8 | 373.0 | 389.0 | 396.9 | 0.800 | 2359.1 | 0.725 |
| K | linear Hawkes, exponential kernels (2 modes) | 6 | 52.8 | 64.8 | 70.7 | 0.984 | 703.7 | 0.881 |
| K3 | linear Hawkes, exponential kernels (3 modes) | 9 | 32.2 | 50.2 | 59.1 | 0.981 | 653.6 | 0.874 |
| P | Hawkes-type power-law decay | 6 | 150.0 | 162.0 | 168.0 | -0.211 | 1193.0 | -0.206 |
| Q | queue-reactive, calibrated on placebo times | 128 | 532.7 | – | – | 0.002 | 3105.3 | -0.000 |
| Q+ | queue-reactive, calibrated on placebo + sweep windows | 136 | 525.4 | – | – | 0.301 | 3053.7 | 0.292 |

Best by cross-validated χ²: **K3**.

## Parameters (95% day-bootstrap intervals)

| model | parameter | value | 95% CI |
|---|---|---|---|
| A | S_mass | 0.0272 | [0.0214, 0.0335] |
| A | S_peak_ms | 0 | [0, 0] |
| A | S_mean_ms | 321 | [182, 525] |
| B | W_mass | 1.71 | [0.655, 3] |
| B | W_peak_ms | 0 | [0, 0] |
| B | W_mean_ms | 7.15 | [5.39, 10.3] |
| B | S_mass | 0.0272 | [0.0205, 0.0349] |
| B | S_peak_ms | 0 | [0, 0] |
| B | S_mean_ms | 321 | [183, 498] |
| C | W_mass | 1.71 | [0.842, 3] |
| C | W_peak_ms | 0 | [0, 0] |
| C | W_mean_ms | 7.15 | [5.51, 10.4] |
| C | S_mass | 0.0196 | [0.0156, 0.0272] |
| C | S_peak_ms | 171 | [73, 252] |
| C | S_mean_ms | 341 | [146, 505] |
| D | W_mass | 1.73 | [0.844, 3] |
| D | W_peak_ms | 0 | [0, 0] |
| D | W_mean_ms | 7.12 | [5.46, 10.5] |
| D | T_mass | 0.0122 | [0.00922, 0.018] |
| D | T_peak_ms | 317 | [193, 550] |
| D | T_mean_ms | 634 | [386, 1.1e+03] |
| E | W_mass | 1.89 | [0.754, 3] |
| E | W_peak_ms | 0 | [0, 0] |
| E | W_mean_ms | 6.83 | [5.5, 10.3] |
| E | T_mass | 0.00551 | [1.84e-36, 0.232] |
| E | T_peak_ms | 21.6 | [13, 5e+03] |
| E | T_mean_ms | 43.2 | [26.1, 1e+04] |
| E | S_mass | 0.0193 | [0.0145, 0.0265] |
| E | S_peak_ms | 190 | [75.3, 257] |
| E | S_mean_ms | 380 | [151, 514] |
| F | W_mass | 0.162 | [0.121, 2.08] |
| F | W_peak_ms | 20.7 | [8.78, 26.4] |
| F | W_mean_ms | 23.7 | [10.8, 30.4] |
| F | W_k | 8 | [5.31, 8] |
| F | T_mass | 0.00464 | [8.11e-16, 1.58] |
| F | T_peak_ms | 46.1 | [35.7, 2.34e+03] |
| F | T_mean_ms | 52.6 | [41.6, 2.72e+03] |
| F | T_k | 8 | [5.95, 8] |
| F | S_mass | 0.0261 | [0.0186, 0.0344] |
| F | S_peak_ms | 8.47e-14 | [5.79e-14, 159] |
| F | S_mean_ms | 381 | [182, 610] |
| F | S_k | 1 | [1, 2.52] |
| G | W_mass | 2.07e-22 | [4.94e-324, 0.92] |
| G | W_peak_ms | 0 | [0, 0] |
| G | W_mean_ms | 4.88e+03 | [2, 5e+03] |
| G | W2_mass | 0.707 | [0.359, 2.9] |
| G | W2_peak_ms | 5.84 | [3.72, 8.23] |
| G | W2_mean_ms | 11.7 | [7.45, 16.5] |
| G | T_mass | 0.0055 | [9.78e-30, 0.228] |
| G | T_peak_ms | 21.6 | [3.93, 5e+03] |
| G | T_mean_ms | 43.2 | [7.86, 1e+04] |
| G | S_mass | 0.0193 | [0.0143, 0.0274] |
| G | S_peak_ms | 190 | [78.2, 265] |
| G | S_mean_ms | 380 | [156, 530] |
| H | W_mass | 1.99e-07 | [4.39e-95, 2.83] |
| H | W_peak_ms | 0 | [0, 0] |
| H | W_mean_ms | 6.15 | [2, 4.81e+03] |
| H | W2_mass | 0.656 | [0.354, 3] |
| H | W2_peak_ms | 6.08 | [3.47, 8.15] |
| H | W2_mean_ms | 12.2 | [6.95, 16.3] |
| H | S_mass | 0.0196 | [0.016, 0.0275] |
| H | S_peak_ms | 171 | [75.3, 265] |
| H | S_mean_ms | 341 | [151, 529] |
| I | W_mass | 1.9 | [0.817, 3] |
| I | W_peak_ms | 0 | [0, 0] |
| I | W_mean_ms | 6.83 | [5.27, 10.9] |
| I | T_mass | 2.44e-34 | [9.85e-38, 0.283] |
| I | T_peak_ms | 14.3 | [3.04, 5e+03] |
| I | T_mean_ms | 28.6 | [6.08, 1e+04] |
| I | T2_mass | 0.00552 | [1.04e-33, 0.0651] |
| I | T2_peak_ms | 21.6 | [2.39, 4.94e+03] |
| I | T2_mean_ms | 43.2 | [4.77, 9.89e+03] |
| I | S_mass | 0.0193 | [0.015, 0.0261] |
| I | S_peak_ms | 190 | [61.2, 282] |
| I | S_mean_ms | 380 | [122, 564] |
| K | H1_aN | -0.0161 | [-0.0335, -0.00413] |
| K | H1_aJ | 0.602 | [0.441, 1.07] |
| K | H1_tau_ms | 15.4 | [10.5, 24.2] |
| K | H2_aN | 0.0309 | [0.0221, 0.0427] |
| K | H2_aJ | -0.201 | [-0.25, -0.174] |
| K | H2_tau_ms | 140 | [107, 165] |
| K3 | H1_aN | -0.0118 | [-0.0309, 0.00317] |
| K3 | H1_aJ | 0.552 | [0.439, 1.07] |
| K3 | H1_tau_ms | 18.4 | [13.3, 35.2] |
| K3 | H2_aN | 0.0223 | [0.00896, 0.0452] |
| K3 | H2_aJ | -0.221 | [-0.508, -0.197] |
| K3 | H2_tau_ms | 114 | [69.3, 138] |
| K3 | H3_aN | 0.0256 | [0.0166, 0.0761] |
| K3 | H3_aJ | -0.0162 | [-0.0653, 0.0241] |
| K3 | H3_tau_ms | 1.51e+03 | [375, 5e+03] |
| P | PN_mass | 0.0461 | [0.0312, 0.239] |
| P | PN_c_ms | 127 | [33.8, 1.05e+03] |
| P | PN_beta | 0.511 | [0.05, 3.95] |
| P | PJ_mass | -0.178 | [-0.203, -0.153] |
| P | PJ_c_ms | 724 | [595, 884] |
| P | PJ_beta | 5 | [5, 5] |
