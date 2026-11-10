# Parametric refill models: out-of-sample comparison

Data: excess near build-up N(w) and deep depletion J(w) per window, 20–1000 ms (10 windows × 2 series), deep book d > 5, state-matched placebo. Rates are gamma pulses (k = 1: exponential from the sweep; k = 2: delayed hump). Weighted least squares with day-bootstrap standard errors; CV: 5 folds over days. Lower cv_chi2 / AIC / BIC is better; cv_r2 is out-of-sample R² relative to predicting zero.

| model | description | params | χ² | AIC | BIC | in-sample R² | CV χ² | CV R² |
|---|---|---|---|---|---|---|---|---|
| A | exponential recovery (near inflow only) | 2 | 1056.5 | 1060.5 | 1062.5 | 0.437 | 5615.2 | 0.401 |
| B | replenish + cancel (two exponentials) | 4 | 320.3 | 328.3 | 332.3 | 0.824 | 1924.7 | 0.785 |
| C | withdrawal + delayed source (no move) | 4 | 490.7 | 498.7 | 502.7 | 0.474 | 3017.3 | 0.498 |
| D | withdrawal + move (no new liquidity) | 4 | 496.5 | 504.5 | 508.5 | 0.466 | 2753.2 | 0.461 |
| E | three-phase: withdrawal + move + delayed source | 6 | 140.3 | 152.3 | 158.3 | 0.883 | 1211.2 | 0.821 |
| F | three-phase, free shapes | 9 | 137.5 | 155.5 | 164.4 | 0.910 | 1253.2 | 0.823 |
| G | three-phase + late withdrawal | 8 | 82.1 | 98.1 | 106.1 | 0.970 | 882.5 | 0.903 |
| H | early + late withdrawal + delayed source (no move) | 6 | 430.4 | 442.4 | 448.4 | 0.563 | 2797.2 | 0.564 |
| I | three-phase + late move | 8 | 81.3 | 97.3 | 105.2 | 0.971 | 877.3 | 0.904 |

Best by cross-validated χ²: **I**.

## Parameters (95% day-bootstrap intervals)

| model | parameter | value | 95% CI |
|---|---|---|---|
| A | S_mass | 0.629 | [0.499, 0.799] |
| A | S_peak_ms | 0 | [0, 0] |
| A | S_mean_ms | 517 | [340, 725] |
| B | W_mass | 0.554 | [0.502, 0.607] |
| B | W_peak_ms | 0 | [0, 0] |
| B | W_mean_ms | 57.7 | [52.4, 64.9] |
| B | S_mass | 0.629 | [0.492, 0.782] |
| B | S_peak_ms | 0 | [0, 0] |
| B | S_mean_ms | 517 | [320, 765] |
| C | W_mass | 0.554 | [0.504, 0.599] |
| C | W_peak_ms | 0 | [0, 0] |
| C | W_mean_ms | 57.7 | [51, 64.1] |
| C | S_mass | 0.204 | [0.181, 0.232] |
| C | S_peak_ms | 29.4 | [25.5, 37.9] |
| C | S_mean_ms | 58.8 | [51, 75.7] |
| D | W_mass | 0.282 | [0.227, 0.417] |
| D | W_peak_ms | 0 | [0, 0] |
| D | W_mean_ms | 71.2 | [42.3, 110] |
| D | T_mass | 0.203 | [0.177, 0.243] |
| D | T_peak_ms | 29.3 | [25, 40.2] |
| D | T_mean_ms | 58.7 | [50, 80.4] |
| E | W_mass | 0.34 | [0.283, 0.401] |
| E | W_peak_ms | 0 | [0, 0] |
| E | W_mean_ms | 75.1 | [62.9, 98.7] |
| E | T_mass | 0.17 | [0.151, 0.195] |
| E | T_peak_ms | 23.3 | [20.4, 26.7] |
| E | T_mean_ms | 46.6 | [40.8, 53.5] |
| E | S_mass | 0.561 | [0.459, 0.659] |
| E | S_peak_ms | 387 | [320, 474] |
| E | S_mean_ms | 775 | [641, 949] |
| F | W_mass | 0.439 | [0.323, 0.544] |
| F | W_peak_ms | 11.3 | [1.86e-13, 33.1] |
| F | W_mean_ms | 47.4 | [40.4, 58.7] |
| F | W_k | 1.31 | [1, 2.27] |
| F | T_mass | 1.55 | [0.571, 2.41] |
| F | T_peak_ms | 9.72e-13 | [2.98e-13, 1.13e+03] |
| F | T_mean_ms | 4.38e+03 | [1.34e+03, 5.97e+03] |
| F | T_k | 1 | [1, 1.23] |
| F | S_mass | 0.12 | [0.102, 0.136] |
| F | S_peak_ms | 40.8 | [38.7, 42.2] |
| F | S_mean_ms | 46.6 | [44.2, 48.4] |
| F | S_k | 8 | [6.49, 8] |
| G | W_mass | 0.332 | [0.268, 0.376] |
| G | W_peak_ms | 0 | [0, 0] |
| G | W_mean_ms | 65.5 | [58, 75.4] |
| G | W2_mass | 3 | [0.706, 3] |
| G | W2_peak_ms | 2.9e+03 | [964, 3.92e+03] |
| G | W2_mean_ms | 5.8e+03 | [1.93e+03, 7.84e+03] |
| G | T_mass | 0.17 | [0.152, 0.19] |
| G | T_peak_ms | 23.7 | [20.7, 26.8] |
| G | T_mean_ms | 47.4 | [41.4, 53.6] |
| G | S_mass | 0.562 | [0.452, 0.671] |
| G | S_peak_ms | 390 | [334, 483] |
| G | S_mean_ms | 780 | [668, 966] |
| H | W_mass | 0.552 | [0.491, 0.611] |
| H | W_peak_ms | 0 | [0, 0] |
| H | W_mean_ms | 53.8 | [48.2, 58.9] |
| H | W2_mass | 3 | [0.807, 3] |
| H | W2_peak_ms | 2.89e+03 | [1.07e+03, 3.78e+03] |
| H | W2_mean_ms | 5.78e+03 | [2.14e+03, 7.57e+03] |
| H | S_mass | 0.204 | [0.176, 0.247] |
| H | S_peak_ms | 29.4 | [23.5, 37] |
| H | S_mean_ms | 58.8 | [46.9, 73.9] |
| I | W_mass | 0.34 | [0.287, 0.386] |
| I | W_peak_ms | 0 | [0, 0] |
| I | W_mean_ms | 65.5 | [56.9, 74.4] |
| I | T_mass | 3 | [0.645, 3] |
| I | T_peak_ms | 2.91e+03 | [947, 3.59e+03] |
| I | T_mean_ms | 5.82e+03 | [1.89e+03, 7.18e+03] |
| I | T2_mass | 0.166 | [0.147, 0.19] |
| I | T2_peak_ms | 23.1 | [20.7, 26] |
| I | T2_mean_ms | 46.1 | [41.4, 52] |
| I | S_mass | 0.309 | [0.273, 0.347] |
| I | S_peak_ms | 267 | [232, 346] |
| I | S_mean_ms | 533 | [463, 693] |
