# Parametric refill models: out-of-sample comparison

Data: excess near build-up N(w) and deep depletion J(w) per window, 20–1000 ms (10 windows × 2 series), deep book d > 5, state-matched placebo. Rates are gamma pulses (k = 1: exponential from the sweep; k = 2: delayed hump). Weighted least squares with day-bootstrap standard errors; CV: 5 folds over days. Lower cv_chi2 / AIC / BIC is better; cv_r2 is out-of-sample R² relative to predicting zero. K, K3, P: Hawkes-type impulse responses. Q, Q+: queue-reactive benchmarks given the observed book state at each window start (params = binned intensity values; no AIC/BIC).

| model | description | params | χ² | AIC | BIC | in-sample R² | CV χ² | CV R² |
|---|---|---|---|---|---|---|---|---|
| A | exponential recovery (near inflow only) | 2 | 100.5 | 104.5 | 106.5 | 0.584 | 946.0 | 0.261 |
| B | replenish + cancel (two exponentials) | 4 | 79.7 | 87.7 | 91.7 | 0.682 | 920.5 | 0.291 |
| C | withdrawal + delayed source (no move) | 4 | 64.2 | 72.2 | 76.2 | 0.756 | 900.5 | 0.230 |
| D | withdrawal + move (no new liquidity) | 4 | 79.6 | 87.6 | 91.6 | 0.574 | 958.8 | 0.201 |
| E | three-phase: withdrawal + move + delayed source | 6 | 60.6 | 72.6 | 78.6 | 0.777 | 883.6 | 0.240 |
| F | three-phase, free shapes | 9 | 44.6 | 62.6 | 71.6 | 0.861 | 906.1 | 0.289 |
| G | three-phase + late withdrawal | 8 | 55.7 | 71.7 | 79.7 | 0.800 | 864.9 | 0.258 |
| H | early + late withdrawal + delayed source (no move) | 6 | 56.5 | 68.5 | 74.4 | 0.802 | 861.8 | 0.268 |
| I | three-phase + late move | 8 | 60.6 | 76.6 | 84.6 | 0.777 | 890.4 | 0.237 |
| K | linear Hawkes, exponential kernels (2 modes) | 6 | 51.1 | 63.1 | 69.1 | 0.791 | 912.2 | 0.181 |
| K3 | linear Hawkes, exponential kernels (3 modes) | 9 | 37.4 | 55.4 | 64.4 | 0.810 | 817.3 | 0.265 |
| P | Hawkes-type power-law decay | 6 | 78.4 | 90.4 | 96.4 | 0.693 | 896.8 | 0.322 |
| Q | queue-reactive, calibrated on placebo times | 282 | 109.2 | – | – | 0.619 | 1268.3 | -0.338 |
| Q+ | queue-reactive, calibrated on placebo + sweep windows | 282 | 98.6 | – | – | 0.626 | 1333.6 | -0.468 |

Best by cross-validated χ²: **K3**.

## Parameters (95% day-bootstrap intervals)

| model | parameter | value | 95% CI |
|---|---|---|---|
| A | S_mass | 1.68 | [0.598, 2.66] |
| A | S_peak_ms | 0 | [0, 0] |
| A | S_mean_ms | 5e+03 | [2.38e+03, 5e+03] |
| B | W_mass | 0.157 | [0.0756, 1.16] |
| B | W_peak_ms | 0 | [0, 0] |
| B | W_mean_ms | 270 | [94, 5e+03] |
| B | S_mass | 1.68 | [0.768, 2.56] |
| B | S_peak_ms | 0 | [0, 0] |
| B | S_mean_ms | 5e+03 | [4.46e+03, 5e+03] |
| C | W_mass | 0.157 | [0.0833, 1.09] |
| C | W_peak_ms | 0 | [0, 0] |
| C | W_mean_ms | 271 | [88.4, 5e+03] |
| C | S_mass | 0.498 | [0.248, 0.862] |
| C | S_peak_ms | 372 | [270, 505] |
| C | S_mean_ms | 744 | [539, 1.01e+03] |
| D | W_mass | 0.0755 | [0.0264, 0.138] |
| D | W_peak_ms | 0 | [0, 0] |
| D | W_mean_ms | 73.6 | [50.6, 107] |
| D | T_mass | 0.24 | [0.0762, 0.451] |
| D | T_peak_ms | 377 | [95.3, 591] |
| D | T_mean_ms | 754 | [191, 1.18e+03] |
| E | W_mass | 0.106 | [0.0482, 0.192] |
| E | W_peak_ms | 0 | [0, 0] |
| E | W_mean_ms | 104 | [64.8, 191] |
| E | T_mass | 0.167 | [1.51e-16, 2.74] |
| E | T_peak_ms | 591 | [427, 5e+03] |
| E | T_mean_ms | 1.18e+03 | [853, 1e+04] |
| E | S_mass | 0.369 | [0.227, 0.57] |
| E | S_peak_ms | 345 | [218, 460] |
| E | S_mean_ms | 691 | [436, 920] |
| F | W_mass | 0.104 | [0.0547, 0.164] |
| F | W_peak_ms | 75.4 | [41.3, 94.4] |
| F | W_mean_ms | 96.7 | [63.1, 115] |
| F | W_k | 4.52 | [1.74, 8] |
| F | T_mass | 0.0989 | [0.0147, 0.233] |
| F | T_peak_ms | 574 | [497, 839] |
| F | T_mean_ms | 656 | [568, 1.33e+03] |
| F | T_k | 8 | [2.86, 8] |
| F | S_mass | 0.274 | [0.17, 0.369] |
| F | S_peak_ms | 317 | [196, 396] |
| F | S_mean_ms | 430 | [313, 502] |
| F | S_k | 3.8 | [2.4, 7.95] |
| G | W_mass | 1.71e-12 | [4.63e-33, 0.0918] |
| G | W_peak_ms | 0 | [0, 0] |
| G | W_mean_ms | 4.8e+03 | [2.06, 5e+03] |
| G | W2_mass | 0.103 | [0.047, 0.144] |
| G | W2_peak_ms | 48.8 | [36.1, 63.1] |
| G | W2_mean_ms | 97.6 | [72.2, 126] |
| G | T_mass | 0.177 | [1.39e-06, 0.747] |
| G | T_peak_ms | 602 | [385, 5e+03] |
| G | T_mean_ms | 1.2e+03 | [771, 1e+04] |
| G | S_mass | 0.364 | [0.248, 0.597] |
| G | S_peak_ms | 343 | [248, 488] |
| G | S_mean_ms | 687 | [496, 975] |
| H | W_mass | 0.54 | [4.01e-09, 1.08] |
| H | W_peak_ms | 0 | [0, 0] |
| H | W_mean_ms | 5e+03 | [5e+03, 5e+03] |
| H | W2_mass | 0.0895 | [0.035, 0.165] |
| H | W2_peak_ms | 48.1 | [30.2, 62.9] |
| H | W2_mean_ms | 96.2 | [60.3, 126] |
| H | S_mass | 0.498 | [0.282, 0.793] |
| H | S_peak_ms | 372 | [251, 496] |
| H | S_mean_ms | 744 | [503, 992] |
| I | W_mass | 0.106 | [0.0378, 0.182] |
| I | W_peak_ms | 0 | [0, 0] |
| I | W_mean_ms | 104 | [55.3, 173] |
| I | T_mass | 1.33e-09 | [1.09e-34, 0.923] |
| I | T_peak_ms | 1.29e+03 | [2.2, 5e+03] |
| I | T_mean_ms | 2.58e+03 | [4.41, 1e+04] |
| I | T2_mass | 0.167 | [1.54e-14, 1.98] |
| I | T2_peak_ms | 591 | [334, 5e+03] |
| I | T2_mean_ms | 1.18e+03 | [667, 1e+04] |
| I | S_mass | 0.369 | [0.244, 0.564] |
| I | S_peak_ms | 345 | [239, 530] |
| I | S_mean_ms | 691 | [477, 1.06e+03] |
| K | H1_aN | -0.175 | [-2.77, -0.12] |
| K | H1_aJ | 0.067 | [-0.107, 0.855] |
| K | H1_tau_ms | 85.3 | [13.9, 213] |
| K | H2_aN | 0.7 | [0.381, 3] |
| K | H2_aJ | 0.152 | [-0.807, 0.388] |
| K | H2_tau_ms | 727 | [227, 1.27e+03] |
| K3 | H1_aN | -1.2 | [-3, 0.000998] |
| K3 | H1_aJ | -3 | [-3, -0.241] |
| K3 | H1_tau_ms | 4.6 | [3.8, 34.1] |
| K3 | H2_aN | -0.0594 | [-2.34, 0.769] |
| K3 | H2_aJ | 0.175 | [-0.546, 3] |
| K3 | H2_tau_ms | 59.1 | [31.9, 272] |
| K3 | H3_aN | 1.01 | [0.333, 3] |
| K3 | H3_aJ | 0.237 | [-0.0398, 0.782] |
| K3 | H3_tau_ms | 1.82e+03 | [372, 5e+03] |
| P | PN_mass | 3 | [3, 3] |
| P | PN_c_ms | 5e+03 | [5e+03, 5e+03] |
| P | PN_beta | 0.567 | [0.261, 1.05] |
| P | PJ_mass | 0.47 | [0.0755, 3] |
| P | PJ_c_ms | 110 | [59.8, 5e+03] |
| P | PJ_beta | 0.204 | [0.05, 5] |
