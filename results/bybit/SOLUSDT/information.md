# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [4 s, 6 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 1311 | -31.2 | 0.48 [0.43, 0.54] | 0.88 [0.83, 0.97] | 1.13 [1.11, 1.16] | 0.136 [0.087, 0.174] | 0.006 [0.003, 0.008] | 0.023 [0.018, 0.029] | 0.346 [0.245, 0.448] | 100 [80, 100] |
| reversal | placebo, same drift tercile | 1311 | -31.2 | 0.48 [0.43, 0.54] | 0.88 [0.83, 0.97] | 1.13 [1.11, 1.16] | 0.136 [0.088, 0.173] | 0.005 [0.003, 0.008] | 0.021 [0.016, 0.026] | 0.328 [0.223, 0.437] | 100 [80, 100] |
| flat | all placebo times | 1324 | +0.1 | 0.47 [0.43, 0.53] | 0.89 [0.83, 0.98] | 1.15 [1.12, 1.20] | 0.128 [0.089, 0.161] | 0.003 [0.001, 0.006] | 0.017 [0.013, 0.021] | 0.331 [0.097, 0.450] | 100 [80, 100] |
| flat | placebo, same drift tercile | 1324 | +0.1 | 0.47 [0.43, 0.53] | 0.89 [0.83, 0.98] | 1.15 [1.12, 1.20] | 0.129 [0.090, 0.162] | 0.003 [0.001, 0.006] | 0.017 [0.013, 0.021] | 0.315 [0.086, 0.454] | 100 [80, 100] |
| continuation | all placebo times | 1335 | +31.3 | 0.46 [0.41, 0.52] | 0.84 [0.78, 0.92] | 1.11 [1.09, 1.14] | 0.152 [0.109, 0.191] | 0.003 [0.001, 0.006] | 0.014 [0.008, 0.021] | 0.280 [0.097, 0.473] | 100 [100, 100] |
| continuation | placebo, same drift tercile | 1335 | +31.3 | 0.46 [0.41, 0.52] | 0.84 [0.78, 0.92] | 1.11 [1.09, 1.14] | 0.151 [0.109, 0.189] | 0.003 [0.001, 0.006] | 0.019 [0.013, 0.026] | 0.303 [0.137, 0.509] | 100 [100, 100] |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | -0.022 | [-0.069, +0.028] |
| all placebo times | withdrawal_<250ms | +0.016 | [-0.000, +0.035] |
| all placebo times | transport_<250ms | -0.003 | [-0.005, -0.000] |
| all placebo times | source_>250ms | -0.009 | [-0.017, -0.003] |
| placebo, same drift tercile | kappa_20-40 | -0.022 | [-0.056, +0.019] |
| placebo, same drift tercile | withdrawal_<250ms | +0.016 | [-0.003, +0.033] |
| placebo, same drift tercile | transport_<250ms | -0.002 | [-0.004, +0.000] |
| placebo, same drift tercile | source_>250ms | -0.002 | [-0.009, +0.004] |
