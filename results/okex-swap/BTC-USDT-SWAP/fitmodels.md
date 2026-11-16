# Parametric refill models: out-of-sample comparison

Data: excess near build-up N(w) and deep depletion J(w) per window, 20–1000 ms (10 windows × 2 series), deep book d > 5, state-matched placebo. Rates are gamma pulses (k = 1: exponential from the sweep; k = 2: delayed hump). Weighted least squares with day-bootstrap standard errors; CV: 5 folds over days. Lower cv_chi2 / AIC / BIC is better; cv_r2 is out-of-sample R² relative to predicting zero. K, K3, P: Hawkes-type impulse responses. Q, Q+: queue-reactive benchmarks given the observed book state at each window start (params = binned intensity values; no AIC/BIC).

| model | description | params | χ² | AIC | BIC | in-sample R² | CV χ² | CV R² |
|---|---|---|---|---|---|---|---|---|
| A | exponential recovery (near inflow only) | 2 | 238.7 | 242.7 | 244.7 | 0.589 | 1577.8 | 0.180 |
| B | replenish + cancel (two exponentials) | 4 | 118.0 | 126.0 | 129.9 | 0.789 | 1003.6 | 0.392 |
| C | withdrawal + delayed source (no move) | 4 | 140.7 | 148.7 | 152.7 | 0.278 | 1121.2 | 0.286 |
| D | withdrawal + move (no new liquidity) | 4 | 127.9 | 135.9 | 139.9 | 0.416 | 869.3 | 0.285 |
| E | three-phase: withdrawal + move + delayed source | 6 | 41.3 | 53.3 | 59.3 | 0.951 | 622.6 | 0.507 |
| F | three-phase, free shapes | 9 | 38.4 | 56.4 | 65.4 | 0.831 | 631.5 | 0.512 |
| G | three-phase + late withdrawal | 8 | 16.7 | 32.7 | 40.7 | 0.959 | 489.2 | 0.602 |
| H | early + late withdrawal + delayed source (no move) | 6 | 113.8 | 125.8 | 131.8 | 0.433 | 1065.1 | 0.324 |
| I | three-phase + late move | 8 | 16.3 | 32.3 | 40.3 | 0.972 | 497.8 | 0.586 |
| K | linear Hawkes, exponential kernels (2 modes) | 6 | 35.6 | 47.6 | 53.6 | 0.943 | 560.7 | 0.570 |
| K3 | linear Hawkes, exponential kernels (3 modes) | 9 | 13.1 | 31.1 | 40.1 | 0.960 | 485.1 | 0.589 |
| P | Hawkes-type power-law decay | 6 | 96.8 | 108.8 | 114.8 | 0.574 | 747.5 | 0.464 |
| Q | queue-reactive, calibrated on placebo times | 288 | 246.1 | – | – | 0.539 | 1673.9 | 0.041 |
| Q+ | queue-reactive, calibrated on placebo + sweep windows | 288 | 218.6 | – | – | 0.541 | 1822.0 | -0.278 |

Best by cross-validated χ²: **K3**.

## Parameters (95% day-bootstrap intervals)

| model | parameter | value | 95% CI |
|---|---|---|---|
| A | S_mass | 0.967 | [0.365, 1.91] |
| A | S_peak_ms | 0 | [0, 0] |
| A | S_mean_ms | 598 | [17.4, 1.13e+03] |
| B | W_mass | 0.571 | [0.433, 0.723] |
| B | W_peak_ms | 0 | [0, 0] |
| B | W_mean_ms | 29.8 | [23.2, 39.7] |
| B | S_mass | 0.967 | [0.459, 1.96] |
| B | S_peak_ms | 0 | [0, 0] |
| B | S_mean_ms | 598 | [15.2, 1.09e+03] |
| C | W_mass | 0.571 | [0.423, 0.76] |
| C | W_peak_ms | 0 | [0, 0] |
| C | W_mean_ms | 29.8 | [23.4, 40] |
| C | S_mass | 0.288 | [0.229, 0.776] |
| C | S_peak_ms | 11.9 | [8.42, 149] |
| C | S_mean_ms | 23.8 | [16.8, 297] |
| D | W_mass | 1.05 | [0.203, 2.76] |
| D | W_peak_ms | 0 | [0, 0] |
| D | W_mean_ms | 2.39e+03 | [35.8, 5e+03] |
| D | T_mass | 0.283 | [0.237, 0.362] |
| D | T_peak_ms | 13.7 | [9.31, 18.4] |
| D | T_mean_ms | 27.4 | [18.6, 36.8] |
| E | W_mass | 0.688 | [0.261, 2.78] |
| E | W_peak_ms | 0 | [0, 0] |
| E | W_mean_ms | 1.33e+03 | [35.9, 5e+03] |
| E | T_mass | 0.313 | [0.239, 0.456] |
| E | T_peak_ms | 10.5 | [7.35, 13.2] |
| E | T_mean_ms | 21 | [14.7, 26.3] |
| E | S_mass | 0.791 | [0.461, 1.28] |
| E | S_peak_ms | 261 | [182, 317] |
| E | S_mean_ms | 523 | [364, 635] |
| F | W_mass | 0.193 | [0.136, 1.31] |
| F | W_peak_ms | 45.4 | [1.16e-14, 55.4] |
| F | W_mean_ms | 55.9 | [44.3, 2.23e+03] |
| F | W_k | 5.34 | [1, 8] |
| F | T_mass | 0.146 | [0.116, 0.515] |
| F | T_peak_ms | 21.9 | [1.01e-14, 25.1] |
| F | T_mean_ms | 25 | [15.7, 28.7] |
| F | T_k | 8 | [1, 8] |
| F | S_mass | 0.875 | [0.414, 1.26] |
| F | S_peak_ms | 194 | [44.1, 278] |
| F | S_mean_ms | 569 | [396, 697] |
| F | S_k | 1.52 | [1.09, 2.14] |
| G | W_mass | 1.72 | [0.263, 2.58] |
| G | W_peak_ms | 0 | [0, 0] |
| G | W_mean_ms | 5e+03 | [876, 5e+03] |
| G | W2_mass | 0.21 | [0.139, 0.285] |
| G | W2_peak_ms | 19.1 | [15.6, 26.5] |
| G | W2_mean_ms | 38.2 | [31.3, 53] |
| G | T_mass | 0.342 | [0.237, 0.53] |
| G | T_peak_ms | 8.62 | [6.67, 10.8] |
| G | T_mean_ms | 17.2 | [13.3, 21.6] |
| G | S_mass | 0.779 | [0.431, 1.15] |
| G | S_peak_ms | 237 | [173, 290] |
| G | S_mean_ms | 473 | [345, 579] |
| H | W_mass | 0.618 | [0.467, 0.793] |
| H | W_peak_ms | 0 | [0, 0] |
| H | W_mean_ms | 24.6 | [19.8, 34.7] |
| H | W2_mass | 0.518 | [0.182, 1.33] |
| H | W2_peak_ms | 475 | [268, 997] |
| H | W2_mean_ms | 950 | [536, 1.99e+03] |
| H | S_mass | 0.288 | [0.217, 0.706] |
| H | S_peak_ms | 11.9 | [8.79, 140] |
| H | S_mean_ms | 23.8 | [17.6, 280] |
| I | W_mass | 0.339 | [0.239, 0.459] |
| I | W_peak_ms | 0 | [0, 0] |
| I | W_mean_ms | 31.7 | [24, 46] |
| I | T_mass | 0.342 | [0.239, 0.544] |
| I | T_peak_ms | 8.49 | [6.77, 10.5] |
| I | T_mean_ms | 17 | [13.5, 21.1] |
| I | T2_mass | 0.573 | [0.204, 1.22] |
| I | T2_peak_ms | 527 | [312, 1.18e+03] |
| I | T2_mean_ms | 1.05e+03 | [625, 2.36e+03] |
| I | S_mass | 0.403 | [0.261, 0.583] |
| I | S_peak_ms | 166 | [130, 209] |
| I | S_mean_ms | 332 | [260, 417] |
| K | H1_aN | 0.379 | [0.266, 0.588] |
| K | H1_aJ | 0.853 | [0.548, 1.23] |
| K | H1_tau_ms | 15.3 | [11.6, 21.8] |
| K | H2_aN | 1.82 | [0.64, 3] |
| K | H2_aJ | 0.896 | [0.309, 1.59] |
| K | H2_tau_ms | 2.04e+03 | [811, 4.57e+03] |
| K3 | H1_aN | 2.28 | [0.835, 3] |
| K3 | H1_aJ | -2.73 | [-3, 0.247] |
| K3 | H1_tau_ms | 13.5 | [8.84, 21.8] |
| K3 | H2_aN | -1.57 | [-2.58, -0.274] |
| K3 | H2_aJ | 3 | [0.53, 3] |
| K3 | H2_tau_ms | 16 | [13.7, 25.4] |
| K3 | H3_aN | 1.32 | [0.524, 3] |
| K3 | H3_aJ | 0.45 | [0.0731, 1.16] |
| K3 | H3_tau_ms | 1.05e+03 | [412, 2.04e+03] |
| P | PN_mass | 2.57 | [0.921, 3] |
| P | PN_c_ms | 2 | [2, 1.41e+03] |
| P | PN_beta | 0.05 | [0.05, 2.46] |
| P | PJ_mass | 2.96 | [0.607, 3] |
| P | PJ_c_ms | 2 | [2, 131] |
| P | PJ_beta | 0.885 | [0.279, 5] |
