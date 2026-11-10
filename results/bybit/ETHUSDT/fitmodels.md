# Parametric refill models: out-of-sample comparison

Data: excess near build-up N(w) and deep depletion J(w) per window, 20–1000 ms (10 windows × 2 series), deep book d > 5, state-matched placebo. Rates are gamma pulses (k = 1: exponential from the sweep; k = 2: delayed hump). Weighted least squares with day-bootstrap standard errors; CV: 5 folds over days. Lower cv_chi2 / AIC / BIC is better; cv_r2 is out-of-sample R² relative to predicting zero. K, K3, P: Hawkes-type impulse responses. Q, Q+: queue-reactive benchmarks given the observed book state at each window start (params = binned intensity values; no AIC/BIC).

| model | description | params | χ² | AIC | BIC | in-sample R² | CV χ² | CV R² |
|---|---|---|---|---|---|---|---|---|
| A | exponential recovery (near inflow only) | 2 | 725.1 | 729.1 | 731.1 | 0.153 | 4402.5 | 0.137 |
| B | replenish + cancel (two exponentials) | 4 | 239.8 | 247.8 | 251.7 | 0.892 | 1920.0 | 0.827 |
| C | withdrawal + delayed source (no move) | 4 | 334.8 | 342.8 | 346.8 | 0.862 | 2399.8 | 0.800 |
| D | withdrawal + move (no new liquidity) | 4 | 380.0 | 388.0 | 392.0 | 0.821 | 2601.6 | 0.769 |
| E | three-phase: withdrawal + move + delayed source | 6 | 150.5 | 162.5 | 168.5 | 0.926 | 1514.1 | 0.856 |
| F | three-phase, free shapes | 9 | 146.4 | 164.4 | 173.3 | 0.928 | 1508.5 | 0.855 |
| G | three-phase + late withdrawal | 8 | 122.9 | 138.9 | 146.8 | 0.944 | 1350.0 | 0.878 |
| H | early + late withdrawal + delayed source (no move) | 6 | 304.5 | 316.5 | 322.5 | 0.894 | 2225.8 | 0.833 |
| I | three-phase + late move | 8 | 150.5 | 166.5 | 174.4 | 0.926 | 1530.0 | 0.853 |
| K | linear Hawkes, exponential kernels (2 modes) | 6 | 142.1 | 154.1 | 160.1 | 0.906 | 1500.0 | 0.836 |
| K3 | linear Hawkes, exponential kernels (3 modes) | 9 | 115.2 | 133.2 | 142.2 | 0.941 | 1353.0 | 0.869 |
| P | Hawkes-type power-law decay | 6 | 186.0 | 198.0 | 204.0 | 0.917 | 1658.5 | 0.852 |
| Q | queue-reactive, calibrated on placebo times | 278 | 1034.8 | – | – | 0.137 | 6138.2 | 0.097 |
| Q+ | queue-reactive, calibrated on placebo + sweep windows | 286 | 1289.1 | – | – | 0.089 | 7440.0 | 0.039 |

Best by cross-validated χ²: **G**.

## Parameters (95% day-bootstrap intervals)

| model | parameter | value | 95% CI |
|---|---|---|---|
| A | S_mass | 0.238 | [0.184, 0.292] |
| A | S_peak_ms | 0 | [0, 0] |
| A | S_mean_ms | 397 | [298, 521] |
| B | W_mass | 0.527 | [0.467, 0.623] |
| B | W_peak_ms | 0 | [0, 0] |
| B | W_mean_ms | 25.3 | [20.8, 31.4] |
| B | S_mass | 0.238 | [0.184, 0.29] |
| B | S_peak_ms | 0 | [0, 0] |
| B | S_mean_ms | 397 | [305, 511] |
| C | W_mass | 0.527 | [0.467, 0.641] |
| C | W_peak_ms | 0 | [0, 0] |
| C | W_mean_ms | 25.3 | [19.1, 30.7] |
| C | S_mass | 0.181 | [0.133, 0.224] |
| C | S_peak_ms | 177 | [141, 216] |
| C | S_mean_ms | 355 | [282, 432] |
| D | W_mass | 0.77 | [0.462, 1.3] |
| D | W_peak_ms | 0 | [0, 0] |
| D | W_mean_ms | 12.6 | [9.14, 20.1] |
| D | T_mass | 0.118 | [0.0966, 0.141] |
| D | T_peak_ms | 30.3 | [27.3, 33.6] |
| D | T_mean_ms | 60.5 | [54.7, 67.1] |
| E | W_mass | 0.582 | [0.368, 1.01] |
| E | W_peak_ms | 0 | [0, 0] |
| E | W_mean_ms | 15.7 | [10.3, 27.7] |
| E | T_mass | 0.1 | [0.0793, 0.118] |
| E | T_peak_ms | 24.1 | [21.7, 26] |
| E | T_mean_ms | 48.2 | [43.3, 52] |
| E | S_mass | 0.179 | [0.139, 0.215] |
| E | S_peak_ms | 276 | [226, 337] |
| E | S_mean_ms | 552 | [452, 673] |
| F | W_mass | 0.792 | [0.363, 2.91] |
| F | W_peak_ms | 2.75e-15 | [1.95e-15, 0.00014] |
| F | W_mean_ms | 12.4 | [6.89, 29.7] |
| F | W_k | 1 | [1, 1] |
| F | T_mass | 0.087 | [0.0631, 0.103] |
| F | T_peak_ms | 37.8 | [18.2, 42.1] |
| F | T_mean_ms | 51.3 | [41.6, 54.6] |
| F | T_k | 3.81 | [1.8, 5.53] |
| F | S_mass | 0.184 | [0.133, 0.253] |
| F | S_peak_ms | 259 | [25.7, 311] |
| F | S_mean_ms | 547 | [470, 661] |
| F | S_k | 1.9 | [1.05, 2.3] |
| G | W_mass | 3 | [3, 3] |
| G | W_peak_ms | 0 | [0, 0] |
| G | W_mean_ms | 5.75 | [5.31, 6.17] |
| G | W2_mass | 0.128 | [0.0917, 0.176] |
| G | W2_peak_ms | 25.4 | [23.3, 28] |
| G | W2_mean_ms | 50.7 | [46.6, 56.1] |
| G | T_mass | 0.0968 | [0.0806, 0.116] |
| G | T_peak_ms | 22.9 | [20.6, 24.5] |
| G | T_mean_ms | 45.8 | [41.2, 49.1] |
| G | S_mass | 0.18 | [0.147, 0.229] |
| G | S_peak_ms | 265 | [230, 308] |
| G | S_mean_ms | 531 | [461, 616] |
| H | W_mass | 3 | [3, 3] |
| H | W_peak_ms | 0 | [0, 0] |
| H | W_mean_ms | 5.79 | [5.44, 6.1] |
| H | W2_mass | 0.222 | [0.185, 0.276] |
| H | W2_peak_ms | 24.9 | [23.2, 27.5] |
| H | W2_mean_ms | 49.7 | [46.3, 55.1] |
| H | S_mass | 0.181 | [0.146, 0.225] |
| H | S_peak_ms | 177 | [146, 216] |
| H | S_mean_ms | 355 | [292, 432] |
| I | W_mass | 0.582 | [0.366, 1.07] |
| I | W_peak_ms | 0 | [0, 0] |
| I | W_mean_ms | 15.7 | [10.2, 28.2] |
| I | T_mass | 0.1 | [0.0775, 0.126] |
| I | T_peak_ms | 24.1 | [21.4, 26.6] |
| I | T_mean_ms | 48.2 | [42.9, 53.2] |
| I | T2_mass | 1.04e-10 | [9.98e-34, 3] |
| I | T2_peak_ms | 2.09 | [2.02, 5e+03] |
| I | T2_mean_ms | 4.18 | [4.04, 1e+04] |
| I | S_mass | 0.179 | [0.133, 0.216] |
| I | S_peak_ms | 276 | [211, 313] |
| I | S_mean_ms | 552 | [422, 626] |
| K | H1_aN | 0.0979 | [0.0734, 0.137] |
| K | H1_aJ | 0.507 | [0.454, 0.564] |
| K | H1_tau_ms | 28.4 | [24, 33.8] |
| K | H2_aN | 0.234 | [0.17, 0.315] |
| K | H2_aJ | -0.0705 | [-0.117, -0.0161] |
| K | H2_tau_ms | 593 | [451, 942] |
| K3 | H1_aN | -0.664 | [-2.39, -0.107] |
| K3 | H1_aJ | 3 | [3, 3] |
| K3 | H1_tau_ms | 5.06 | [4.47, 5.44] |
| K3 | H2_aN | 0.138 | [0.0874, 0.248] |
| K3 | H2_aJ | 0.405 | [0.358, 0.462] |
| K3 | H2_tau_ms | 31.6 | [25.8, 37.6] |
| K3 | H3_aN | 0.238 | [0.171, 0.36] |
| K3 | H3_aJ | -0.0706 | [-0.123, 0.00895] |
| K3 | H3_tau_ms | 714 | [476, 1.19e+03] |
| P | PN_mass | 1.49 | [1.03, 1.91] |
| P | PN_c_ms | 25 | [7.53, 52.6] |
| P | PN_beta | 0.05 | [0.05, 0.05] |
| P | PJ_mass | 0.739 | [0.614, 0.97] |
| P | PJ_c_ms | 82.8 | [48.9, 106] |
| P | PJ_beta | 5 | [3.55, 5] |
