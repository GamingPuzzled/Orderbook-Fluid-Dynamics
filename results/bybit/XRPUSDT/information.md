# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [4 s, 6 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 327 | -6.3 | 0.49 [0.41, 0.58] | 1.14 [0.92, 1.35] | 1.09 [1.05, 1.13] | 0.095 [0.069, 0.136] | 0.009 [0.001, 0.014] | 0.009 [0.005, 0.013] | 0.423 [0.033, 0.594] | 60 [40, 650] |
| reversal | placebo, same drift tercile | 327 | -6.3 | 0.49 [0.41, 0.58] | 1.14 [0.92, 1.35] | 1.09 [1.05, 1.13] | 0.096 [0.069, 0.136] | 0.008 [0.000, 0.014] | 0.008 [0.003, 0.012] | 0.407 [0.016, 0.610] | 60 [40, 650] |
| flat | all placebo times | 339 | +0.4 | 0.49 [0.41, 0.59] | 1.14 [0.93, 1.37] | 1.09 [1.02, 1.15] | 0.090 [0.069, 0.120] | 0.003 [0.000, 0.012] | 0.006 [0.000, 0.014] | 0.153 [0.000, 0.574] | 40 [40, 650] |
| flat | placebo, same drift tercile | 339 | +0.4 | 0.49 [0.41, 0.59] | 1.14 [0.93, 1.37] | 1.09 [1.02, 1.15] | 0.090 [0.069, 0.120] | 0.003 [0.000, 0.012] | 0.007 [0.000, 0.015] | 0.168 [0.000, 0.602] | 40 [40, 650] |
| continuation | all placebo times | 349 | +7.3 | 0.42 [0.33, 0.51] | 1.03 [0.82, 1.22] | 1.09 [1.04, 1.14] | 0.122 [0.085, 0.185] | 0.009 [0.001, 0.012] | 0.010 [0.004, 0.016] | 0.488 [0.077, 0.656] | – |
| continuation | placebo, same drift tercile | 349 | +7.3 | 0.42 [0.33, 0.51] | 1.03 [0.82, 1.22] | 1.09 [1.04, 1.14] | 0.122 [0.085, 0.185] | 0.009 [0.002, 0.012] | 0.015 [0.005, 0.023] | 0.491 [0.085, 0.623] | 100 [76, 196] |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | -0.059 | [-0.171, +0.021] |
| all placebo times | withdrawal_<250ms | +0.024 | [+0.001, +0.055] |
| all placebo times | transport_<250ms | +0.002 | [-0.010, +0.008] |
| all placebo times | source_>250ms | -0.001 | [-0.008, +0.007] |
| placebo, same drift tercile | kappa_20-40 | -0.059 | [-0.159, +0.021] |
| placebo, same drift tercile | withdrawal_<250ms | +0.024 | [-0.002, +0.063] |
| placebo, same drift tercile | transport_<250ms | +0.003 | [-0.008, +0.008] |
| placebo, same drift tercile | source_>250ms | +0.004 | [-0.003, +0.009] |
