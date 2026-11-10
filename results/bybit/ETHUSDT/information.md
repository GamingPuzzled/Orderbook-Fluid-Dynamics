# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [4 s, 6 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 5282 | -116.6 | 0.62 [0.57, 0.66] | 0.85 [0.81, 0.88] | 1.10 [1.08, 1.12] | 0.209 [0.177, 0.241] | 0.078 [0.063, 0.096] | 0.118 [0.098, 0.138] | 0.784 [0.700, 0.859] | 140 [100, 140] |
| reversal | placebo, same drift tercile | 5282 | -116.6 | 0.62 [0.57, 0.66] | 0.85 [0.81, 0.88] | 1.10 [1.08, 1.12] | 0.212 [0.181, 0.243] | 0.076 [0.061, 0.093] | 0.093 [0.067, 0.114] | 0.793 [0.703, 0.848] | 140 [100, 140] |
| flat | all placebo times | 5294 | +0.5 | 0.62 [0.57, 0.67] | 0.86 [0.81, 0.91] | 1.09 [1.08, 1.11] | 0.187 [0.161, 0.220] | 0.086 [0.065, 0.105] | 0.068 [0.050, 0.091] | 0.816 [0.702, 0.903] | 100 [100, 140] |
| flat | placebo, same drift tercile | 5294 | +0.5 | 0.62 [0.57, 0.67] | 0.86 [0.81, 0.91] | 1.09 [1.08, 1.11] | 0.190 [0.164, 0.220] | 0.088 [0.066, 0.109] | 0.095 [0.077, 0.117] | 0.795 [0.684, 0.875] | 140 [100, 140] |
| continuation | all placebo times | 5308 | +124.1 | 0.60 [0.54, 0.66] | 0.85 [0.81, 0.89] | 1.05 [1.04, 1.07] | 0.222 [0.185, 0.272] | 0.101 [0.076, 0.123] | 0.076 [0.061, 0.094] | 0.823 [0.720, 0.846] | – |
| continuation | placebo, same drift tercile | 5308 | +124.1 | 0.60 [0.54, 0.66] | 0.85 [0.81, 0.89] | 1.05 [1.04, 1.07] | 0.217 [0.178, 0.267] | 0.105 [0.076, 0.128] | 0.123 [0.095, 0.150] | 0.821 [0.707, 0.862] | 140 [100, 140] |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | -0.019 | [-0.049, +0.013] |
| all placebo times | withdrawal_<250ms | +0.013 | [-0.010, +0.040] |
| all placebo times | transport_<250ms | +0.024 | [+0.002, +0.043] |
| all placebo times | source_>250ms | -0.042 | [-0.062, -0.020] |
| placebo, same drift tercile | kappa_20-40 | -0.019 | [-0.054, +0.017] |
| placebo, same drift tercile | withdrawal_<250ms | +0.005 | [-0.022, +0.032] |
| placebo, same drift tercile | transport_<250ms | +0.029 | [+0.011, +0.054] |
| placebo, same drift tercile | source_>250ms | +0.030 | [+0.001, +0.061] |
