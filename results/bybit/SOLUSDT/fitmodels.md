# Parametric refill models: out-of-sample comparison

Data: excess near build-up N(w) and deep depletion J(w) per window, 20–1000 ms (10 windows × 2 series), deep book d > 5, state-matched placebo. Rates are gamma pulses (k = 1: exponential from the sweep; k = 2: delayed hump). Weighted least squares with day-bootstrap standard errors; CV: 5 folds over days. Lower cv_chi2 / AIC / BIC is better; cv_r2 is out-of-sample R² relative to predicting zero. K, K3, P: Hawkes-type impulse responses. Q, Q+: queue-reactive benchmarks given the observed book state at each window start (params = binned intensity values; no AIC/BIC).

| model | description | params | χ² | AIC | BIC | in-sample R² | CV χ² | CV R² |
|---|---|---|---|---|---|---|---|---|
| A | exponential recovery (near inflow only) | 2 | 419.5 | 423.5 | 425.5 | 0.013 | 2774.0 | 0.010 |
| B | replenish + cancel (two exponentials) | 4 | 310.3 | 318.3 | 322.3 | 0.818 | 2275.1 | 0.709 |
| C | withdrawal + delayed source (no move) | 4 | 312.4 | 320.4 | 324.4 | 0.817 | 2298.8 | 0.709 |
| D | withdrawal + move (no new liquidity) | 4 | 421.0 | 429.0 | 433.0 | 0.772 | 2797.3 | 0.666 |
| E | three-phase: withdrawal + move + delayed source | 6 | 312.4 | 324.4 | 330.4 | 0.817 | 2321.9 | 0.707 |
| F | three-phase, free shapes | 9 | 309.0 | 327.0 | 335.9 | 0.818 | 2298.9 | 0.708 |
| G | three-phase + late withdrawal | 8 | 312.1 | 328.1 | 336.0 | 0.818 | 2325.2 | 0.705 |
| H | early + late withdrawal + delayed source (no move) | 6 | 312.1 | 324.1 | 330.1 | 0.818 | 2303.0 | 0.706 |
| I | three-phase + late move | 8 | 312.4 | 328.4 | 336.4 | 0.817 | 2321.9 | 0.707 |
| K | linear Hawkes, exponential kernels (2 modes) | 6 | 65.5 | 77.5 | 83.5 | 0.962 | 1057.4 | 0.846 |
| K3 | linear Hawkes, exponential kernels (3 modes) | 9 | 45.2 | 63.2 | 72.2 | 0.958 | 993.3 | 0.842 |
| P | Hawkes-type power-law decay | 6 | 240.5 | 252.5 | 258.5 | 0.024 | 1873.1 | 0.025 |
| Q | queue-reactive, calibrated on placebo times | 210 | 551.6 | – | – | -0.025 | 3593.4 | -0.039 |
| Q+ | queue-reactive, calibrated on placebo + sweep windows | 232 | 774.6 | – | – | 0.383 | 4893.1 | 0.319 |

Best by cross-validated χ²: **K3**.

## Parameters (95% day-bootstrap intervals)

| model | parameter | value | 95% CI |
|---|---|---|---|
| A | S_mass | 0.0491 | [0.0352, 0.0751] |
| A | S_peak_ms | 0 | [0, 0] |
| A | S_mean_ms | 673 | [436, 1.39e+03] |
| B | W_mass | 0.632 | [0.474, 0.812] |
| B | W_peak_ms | 0 | [0, 0] |
| B | W_mean_ms | 12.5 | [10.7, 14.4] |
| B | S_mass | 0.0491 | [0.0352, 0.0753] |
| B | S_peak_ms | 0 | [0, 0] |
| B | S_mean_ms | 673 | [434, 1.3e+03] |
| C | W_mass | 0.632 | [0.5, 0.866] |
| C | W_peak_ms | 0 | [0, 0] |
| C | W_mean_ms | 12.5 | [9.86, 14.2] |
| C | S_mass | 0.0331 | [0.0244, 0.0433] |
| C | S_peak_ms | 210 | [146, 292] |
| C | S_mean_ms | 420 | [292, 584] |
| D | W_mass | 0.655 | [0.492, 0.86] |
| D | W_peak_ms | 0 | [0, 0] |
| D | W_mean_ms | 12.1 | [10.3, 13.9] |
| D | T_mass | 0.0154 | [0.00754, 0.023] |
| D | T_peak_ms | 122 | [92.7, 157] |
| D | T_mean_ms | 243 | [185, 314] |
| E | W_mass | 0.632 | [0.449, 0.85] |
| E | W_peak_ms | 0 | [0, 0] |
| E | W_mean_ms | 12.5 | [10.6, 14.3] |
| E | T_mass | 0.000121 | [4.12e-21, 0.00655] |
| E | T_peak_ms | 31.7 | [2.1, 4.4e+03] |
| E | T_mean_ms | 63.3 | [4.2, 8.8e+03] |
| E | S_mass | 0.0331 | [0.0236, 0.0437] |
| E | S_peak_ms | 211 | [150, 317] |
| E | S_mean_ms | 421 | [300, 635] |
| F | W_mass | 0.632 | [0.167, 0.785] |
| F | W_peak_ms | 8.69e-11 | [1.6e-14, 23.6] |
| F | W_mean_ms | 12.5 | [10.9, 28] |
| F | W_k | 1 | [1, 6.13] |
| F | T_mass | 9.66e-24 | [8.92e-35, 0.00332] |
| F | T_peak_ms | 8.94e+03 | [0.0607, 3.24e+04] |
| F | T_mean_ms | 1.03e+04 | [2.07, 3.73e+04] |
| F | T_k | 7.48 | [1.02, 8] |
| F | S_mass | 0.0408 | [0.0254, 0.0597] |
| F | S_peak_ms | 126 | [4.1e-06, 273] |
| F | S_mean_ms | 517 | [305, 872] |
| F | S_k | 1.32 | [1, 2.56] |
| G | W_mass | 3 | [8.08e-07, 3] |
| G | W_peak_ms | 0 | [0, 0] |
| G | W_mean_ms | 4.68 | [2, 5.3] |
| G | W2_mass | 0.178 | [0.123, 0.364] |
| G | W2_peak_ms | 11.8 | [8.58, 15] |
| G | W2_mean_ms | 23.5 | [17.2, 30] |
| G | T_mass | 5.66e-05 | [1.7e-34, 0.00701] |
| G | T_peak_ms | 31.5 | [2, 5e+03] |
| G | T_mean_ms | 63 | [4, 1e+04] |
| G | S_mass | 0.0331 | [0.0246, 0.0477] |
| G | S_peak_ms | 210 | [143, 311] |
| G | S_mean_ms | 421 | [287, 622] |
| H | W_mass | 3 | [1.36e-08, 3] |
| H | W_peak_ms | 0 | [0, 0] |
| H | W_mean_ms | 4.68 | [2, 5.37] |
| H | W2_mass | 0.178 | [0.105, 0.34] |
| H | W2_peak_ms | 11.8 | [9.07, 14.6] |
| H | W2_mean_ms | 23.6 | [18.1, 29.2] |
| H | S_mass | 0.0331 | [0.0232, 0.044] |
| H | S_peak_ms | 210 | [160, 291] |
| H | S_mean_ms | 420 | [319, 582] |
| I | W_mass | 0.632 | [0.492, 0.85] |
| I | W_peak_ms | 0 | [0, 0] |
| I | W_mean_ms | 12.5 | [10.7, 13.8] |
| I | T_mass | 0.000122 | [4.03e-23, 0.00589] |
| I | T_peak_ms | 31.7 | [2.01, 5e+03] |
| I | T_mean_ms | 63.3 | [4.02, 1e+04] |
| I | T2_mass | 6.07e-25 | [3.68e-30, 0.0038] |
| I | T2_peak_ms | 65.2 | [2, 4.69e+03] |
| I | T2_mean_ms | 130 | [4, 9.38e+03] |
| I | S_mass | 0.0331 | [0.0261, 0.0467] |
| I | S_peak_ms | 211 | [154, 333] |
| I | S_mean_ms | 421 | [309, 665] |
| K | H1_aN | -0.0287 | [-0.042, -0.0171] |
| K | H1_aJ | 0.502 | [0.358, 0.635] |
| K | H1_tau_ms | 16.7 | [14.4, 21] |
| K | H2_aN | 0.0394 | [0.0311, 0.0508] |
| K | H2_aJ | -0.146 | [-0.181, -0.112] |
| K | H2_tau_ms | 276 | [212, 407] |
| K3 | H1_aN | -0.0225 | [-0.254, -0.0104] |
| K3 | H1_aJ | 0.448 | [0.381, 3] |
| K3 | H1_tau_ms | 22.3 | [17, 47.2] |
| K3 | H2_aN | 0.0151 | [0.00299, 0.239] |
| K3 | H2_aJ | -0.164 | [-2.82, -0.13] |
| K3 | H2_tau_ms | 126 | [48.3, 202] |
| K3 | H3_aN | 0.0532 | [0.0307, 0.174] |
| K3 | H3_aJ | -0.0719 | [-0.215, -0.0289] |
| K3 | H3_tau_ms | 1.17e+03 | [466, 5e+03] |
| P | PN_mass | 0.0544 | [0.0373, 0.655] |
| P | PN_c_ms | 3.64e+03 | [320, 5e+03] |
| P | PN_beta | 5 | [0.05, 5] |
| P | PJ_mass | -0.121 | [-0.15, -0.102] |
| P | PJ_c_ms | 1.81e+03 | [1.39e+03, 2.59e+03] |
| P | PJ_beta | 5 | [5, 5] |
