# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [4 s, 6 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 199 | -5.5 | 0.54 [0.47, 0.65] | 1.08 [0.99, 1.26] | 1.19 [1.12, 1.27] | 0.115 [0.078, 0.155] | 0.000 [0.000, 0.002] | 0.011 [0.006, 0.016] | 0.000 [0.000, 0.290] | 100 [100, 484] |
| reversal | placebo, same drift tercile | 199 | -5.5 | 0.54 [0.47, 0.65] | 1.08 [0.99, 1.26] | 1.19 [1.12, 1.27] | 0.115 [0.077, 0.154] | 0.000 [0.000, 0.001] | 0.008 [0.004, 0.014] | 0.000 [0.000, 0.223] | 100 [100, 300] |
| flat | all placebo times | 209 | +0.4 | 0.57 [0.50, 0.66] | 1.06 [0.97, 1.22] | 1.21 [1.15, 1.29] | 0.093 [0.066, 0.128] | 0.003 [0.000, 0.005] | 0.009 [0.006, 0.015] | 0.320 [0.000, 0.510] | 650 [100, 650] |
| flat | placebo, same drift tercile | 209 | +0.4 | 0.57 [0.50, 0.66] | 1.06 [0.97, 1.22] | 1.21 [1.15, 1.29] | 0.093 [0.066, 0.126] | 0.003 [0.000, 0.005] | 0.010 [0.006, 0.015] | 0.329 [0.000, 0.496] | 650 [100, 650] |
| continuation | all placebo times | 220 | +6.5 | 0.59 [0.51, 0.66] | 1.13 [0.96, 1.47] | 1.14 [1.11, 1.20] | 0.099 [0.079, 0.135] | 0.000 [0.000, 0.005] | 0.008 [0.005, 0.012] | 0.000 [0.000, 0.497] | 40 [40, 650] |
| continuation | placebo, same drift tercile | 220 | +6.5 | 0.59 [0.51, 0.66] | 1.13 [0.96, 1.47] | 1.14 [1.11, 1.20] | 0.100 [0.079, 0.136] | 0.000 [0.000, 0.005] | 0.009 [0.006, 0.013] | 0.000 [0.000, 0.480] | 40 [40, 650] |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | +0.049 | [-0.104, +0.144] |
| all placebo times | withdrawal_<250ms | -0.013 | [-0.035, +0.028] |
| all placebo times | transport_<250ms | +0.000 | [-0.001, +0.005] |
| all placebo times | source_>250ms | -0.003 | [-0.008, +0.003] |
| placebo, same drift tercile | kappa_20-40 | +0.049 | [-0.054, +0.141] |
| placebo, same drift tercile | withdrawal_<250ms | -0.012 | [-0.041, +0.026] |
| placebo, same drift tercile | transport_<250ms | +0.000 | [-0.001, +0.004] |
| placebo, same drift tercile | source_>250ms | -0.000 | [-0.006, +0.004] |
