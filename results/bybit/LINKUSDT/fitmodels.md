# Parametric refill models: out-of-sample comparison

Data: excess near build-up N(w) and deep depletion J(w) per window, 20–1000 ms (10 windows × 2 series), deep book d > 5, state-matched placebo. Rates are gamma pulses (k = 1: exponential from the sweep; k = 2: delayed hump). Weighted least squares with day-bootstrap standard errors; CV: 5 folds over days. Lower cv_chi2 / AIC / BIC is better; cv_r2 is out-of-sample R² relative to predicting zero. K, K3, P: Hawkes-type impulse responses. Q, Q+: queue-reactive benchmarks given the observed book state at each window start (params = binned intensity values; no AIC/BIC).

| model | description | params | χ² | AIC | BIC | in-sample R² | CV χ² | CV R² |
|---|---|---|---|---|---|---|---|---|
| A | exponential recovery (near inflow only) | 2 | 363.5 | 367.5 | 369.4 | 0.003 | 2180.5 | 0.004 |
| B | replenish + cancel (two exponentials) | 4 | 291.3 | 299.3 | 303.2 | 0.778 | 1926.0 | 0.597 |
| C | withdrawal + delayed source (no move) | 4 | 294.9 | 302.9 | 306.8 | 0.778 | 1946.5 | 0.597 |
| D | withdrawal + move (no new liquidity) | 4 | 328.3 | 336.3 | 340.3 | 0.753 | 2119.4 | 0.568 |
| E | three-phase: withdrawal + move + delayed source | 6 | 294.8 | 306.8 | 312.8 | 0.777 | 1954.8 | 0.596 |
| F | three-phase, free shapes | 9 | 290.4 | 308.4 | 317.4 | 0.780 | 1930.0 | 0.598 |
| G | three-phase + late withdrawal | 8 | 294.1 | 310.1 | 318.1 | 0.779 | 1950.8 | 0.596 |
| H | early + late withdrawal + delayed source (no move) | 6 | 294.1 | 306.1 | 312.1 | 0.780 | 1942.1 | 0.598 |
| I | three-phase + late move | 8 | 294.8 | 310.8 | 318.8 | 0.777 | 1954.8 | 0.596 |
| K | linear Hawkes, exponential kernels (2 modes) | 6 | 46.2 | 58.2 | 64.2 | 0.975 | 646.0 | 0.828 |
| K3 | linear Hawkes, exponential kernels (3 modes) | 9 | 38.7 | 56.7 | 65.6 | 0.976 | 659.5 | 0.819 |
| P | Hawkes-type power-law decay | 6 | 133.3 | 145.3 | 151.3 | 0.090 | 986.2 | 0.116 |
| Q | queue-reactive, calibrated on placebo times | 144 | 416.8 | – | – | -0.005 | 2407.6 | 0.002 |
| Q+ | queue-reactive, calibrated on placebo + sweep windows | 154 | 430.0 | – | – | 0.210 | 2449.4 | 0.203 |

Best by cross-validated χ²: **K**.

## Parameters (95% day-bootstrap intervals)

| model | parameter | value | 95% CI |
|---|---|---|---|
| A | S_mass | 0.0182 | [0.0139, 0.0256] |
| A | S_peak_ms | 0 | [0, 0] |
| A | S_mean_ms | 368 | [225, 704] |
| B | W_mass | 3 | [1.82, 3] |
| B | W_peak_ms | 0 | [0, 0] |
| B | W_mean_ms | 5.62 | [5.25, 6.79] |
| B | S_mass | 0.0182 | [0.0134, 0.0245] |
| B | S_peak_ms | 0 | [0, 0] |
| B | S_mean_ms | 368 | [245, 668] |
| C | W_mass | 3 | [2.16, 3] |
| C | W_peak_ms | 0 | [0, 0] |
| C | W_mean_ms | 5.62 | [5.24, 6.54] |
| C | S_mass | 0.0142 | [0.0118, 0.0195] |
| C | S_peak_ms | 150 | [88.5, 296] |
| C | S_mean_ms | 300 | [177, 592] |
| D | W_mass | 3 | [2.74, 3] |
| D | W_peak_ms | 0 | [0, 0] |
| D | W_mean_ms | 5.61 | [5.32, 6.1] |
| D | T_mass | 0.00843 | [0.00449, 0.0123] |
| D | T_peak_ms | 86.6 | [65.1, 112] |
| D | T_mean_ms | 173 | [130, 224] |
| E | W_mass | 3 | [2.35, 3] |
| E | W_peak_ms | 0 | [0, 0] |
| E | W_mean_ms | 5.62 | [5.18, 6.27] |
| E | T_mass | 0.000506 | [5.94e-26, 0.00451] |
| E | T_peak_ms | 31 | [2.03, 4.93e+03] |
| E | T_mean_ms | 62 | [4.07, 9.86e+03] |
| E | S_mass | 0.0141 | [0.0112, 0.0189] |
| E | S_peak_ms | 156 | [101, 289] |
| E | S_mean_ms | 312 | [202, 578] |
| F | W_mass | 3 | [0.175, 3] |
| F | W_peak_ms | 7.92 | [6.39, 19.3] |
| F | W_mean_ms | 9.92 | [8.82, 22.1] |
| F | W_k | 4.96 | [3.75, 8] |
| F | T_mass | 8.07e-32 | [5.87e-33, 2.09] |
| F | T_peak_ms | 1.94 | [0.00827, 3.5e+04] |
| F | T_mean_ms | 4.29 | [2.07, 4e+04] |
| F | T_k | 1.83 | [1, 8] |
| F | S_mass | 0.0181 | [0.0133, 0.0235] |
| F | S_peak_ms | 9.48 | [1.15e-13, 142] |
| F | S_mean_ms | 365 | [234, 661] |
| F | S_k | 1.03 | [1, 1.71] |
| G | W_mass | 2.96 | [1.26e-06, 3] |
| G | W_peak_ms | 0 | [0, 0] |
| G | W_mean_ms | 3.96 | [2, 4.11] |
| G | W2_mass | 2.99 | [0.918, 3] |
| G | W2_peak_ms | 3.49 | [3.33, 5.17] |
| G | W2_mean_ms | 6.99 | [6.66, 10.3] |
| G | T_mass | 0.000587 | [6.71e-36, 0.00495] |
| G | T_peak_ms | 31.2 | [2, 4.5e+03] |
| G | T_mean_ms | 62.3 | [4, 9.01e+03] |
| G | S_mass | 0.0141 | [0.0104, 0.0188] |
| G | S_peak_ms | 157 | [100, 331] |
| G | S_mean_ms | 314 | [200, 662] |
| H | W_mass | 3 | [1.82e-07, 3] |
| H | W_peak_ms | 0 | [0, 0] |
| H | W_mean_ms | 3.95 | [2, 4.1] |
| H | W2_mass | 3 | [0.881, 3] |
| H | W2_peak_ms | 3.49 | [3.32, 5.46] |
| H | W2_mean_ms | 6.99 | [6.64, 10.9] |
| H | S_mass | 0.0142 | [0.0106, 0.0187] |
| H | S_peak_ms | 150 | [103, 249] |
| H | S_mean_ms | 300 | [205, 498] |
| I | W_mass | 3 | [2.61, 3] |
| I | W_peak_ms | 0 | [0, 0] |
| I | W_mean_ms | 5.62 | [5.14, 6.07] |
| I | T_mass | 0.000505 | [3.74e-44, 0.00466] |
| I | T_peak_ms | 31 | [2, 4.99e+03] |
| I | T_mean_ms | 61.9 | [4, 9.97e+03] |
| I | T2_mass | 1.74e-36 | [2.08e-37, 0.00256] |
| I | T2_peak_ms | 4.97e+03 | [2.05, 4.99e+03] |
| I | T2_mean_ms | 9.94e+03 | [4.1, 9.98e+03] |
| I | S_mass | 0.0141 | [0.0102, 0.0181] |
| I | S_peak_ms | 156 | [95.7, 284] |
| I | S_mean_ms | 312 | [191, 568] |
| K | H1_aN | -0.0657 | [-0.135, -0.000809] |
| K | H1_aJ | 3 | [0.817, 3] |
| K | H1_tau_ms | 5.77 | [5.35, 9.63] |
| K | H2_aN | 0.0191 | [0.0155, 0.0236] |
| K | H2_aJ | -0.141 | [-0.175, -0.121] |
| K | H2_tau_ms | 412 | [299, 587] |
| K3 | H1_aN | -3 | [-3, -0.0844] |
| K3 | H1_aJ | 3 | [-3, 3] |
| K3 | H1_tau_ms | 5.79 | [3.93, 10.4] |
| K3 | H2_aN | 1.5 | [0.0109, 2.24] |
| K3 | H2_aJ | -0.0214 | [-1.68, 2.75] |
| K3 | H2_tau_ms | 7.28 | [6.67, 28.6] |
| K3 | H3_aN | 0.0182 | [0.0128, 0.0239] |
| K3 | H3_aJ | -0.141 | [-0.166, -0.121] |
| K3 | H3_tau_ms | 425 | [325, 627] |
| P | PN_mass | 0.0217 | [0.0149, 0.0577] |
| P | PN_c_ms | 649 | [167, 2.42e+03] |
| P | PN_beta | 1.76 | [0.204, 5] |
| P | PJ_mass | -0.146 | [-0.277, -0.125] |
| P | PJ_c_ms | 2.42e+03 | [252, 3.67e+03] |
| P | PJ_beta | 5 | [0.447, 5] |
