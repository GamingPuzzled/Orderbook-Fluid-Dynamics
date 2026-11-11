# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [4 s, 6 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 412 | -162.4 | 0.46 [0.18, 1.06] | 0.64 [0.47, 0.99] | 1.16 [1.14, 1.19] | 0.248 [0.092, 0.379] | 0.055 [0.035, 0.083] | 0.112 [0.061, 0.188] | 1.000 [0.748, 1.000] | 650 [200, 650] |
| reversal | placebo, same drift tercile | 412 | -162.4 | 0.46 [0.18, 1.06] | 0.64 [0.47, 0.99] | 1.16 [1.14, 1.19] | 0.270 [0.115, 0.390] | 0.043 [0.022, 0.071] | 0.056 [0.024, 0.119] | 1.000 [0.746, 1.000] | – |
| flat | all placebo times | 414 | +0.3 | 0.62 [0.02, 1.17] | 0.77 [0.56, 1.17] | 1.10 [1.09, 1.14] | 0.178 [0.083, 0.314] | 0.134 [0.063, 0.195] | 0.099 [0.049, 0.143] | 0.998 [0.629, 1.000] | 200 [200, 650] |
| flat | placebo, same drift tercile | 414 | +0.3 | 0.62 [0.02, 1.17] | 0.77 [0.56, 1.17] | 1.10 [1.09, 1.14] | 0.177 [0.081, 0.321] | 0.146 [0.085, 0.201] | 0.086 [0.030, 0.251] | 0.950 [0.631, 0.982] | – |
| continuation | all placebo times | 415 | +213.9 | 0.70 [0.07, 0.86] | 0.65 [0.53, 0.94] | 1.07 [1.06, 1.08] | 0.208 [0.067, 0.376] | 0.071 [0.034, 0.109] | 0.040 [0.004, 0.078] | 1.000 [0.690, 1.000] | – |
| continuation | placebo, same drift tercile | 415 | +213.9 | 0.70 [0.07, 0.86] | 0.65 [0.53, 0.94] | 1.07 [1.06, 1.08] | 0.202 [0.063, 0.357] | 0.070 [0.038, 0.113] | 0.060 [0.044, 0.091] | 1.000 [0.769, 1.000] | 300 [300, 650] |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | +0.236 | [-0.367, +0.602] |
| all placebo times | withdrawal_<250ms | -0.039 | [-0.084, +0.004] |
| all placebo times | transport_<250ms | +0.016 | [-0.042, +0.058] |
| all placebo times | source_>250ms | -0.073 | [-0.180, -0.008] |
| placebo, same drift tercile | kappa_20-40 | +0.236 | [-0.330, +0.556] |
| placebo, same drift tercile | withdrawal_<250ms | -0.067 | [-0.095, -0.034] |
| placebo, same drift tercile | transport_<250ms | +0.027 | [-0.022, +0.076] |
| placebo, same drift tercile | source_>250ms | +0.003 | [-0.037, +0.033] |
