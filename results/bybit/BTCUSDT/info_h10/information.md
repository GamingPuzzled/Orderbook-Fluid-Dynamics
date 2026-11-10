# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [9 s, 11 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 8264 | -229.5 | 0.74 [0.69, 0.81] | 0.88 [0.84, 0.93] | 1.12 [1.11, 1.13] | 0.210 [0.166, 0.247] | 0.186 [0.159, 0.218] | 0.256 [0.217, 0.288] | 0.925 [0.871, 0.984] | 200 [140, 362] |
| reversal | placebo, same drift tercile | 8264 | -229.5 | 0.74 [0.69, 0.81] | 0.88 [0.84, 0.93] | 1.12 [1.11, 1.13] | 0.211 [0.167, 0.249] | 0.188 [0.154, 0.218] | 0.185 [0.138, 0.214] | 0.939 [0.883, 1.000] | – |
| flat | all placebo times | 8277 | +0.5 | 0.76 [0.70, 0.83] | 0.86 [0.82, 0.92] | 1.12 [1.10, 1.13] | 0.205 [0.168, 0.240] | 0.150 [0.127, 0.179] | 0.169 [0.129, 0.199] | 0.924 [0.865, 0.971] | 200 [140, 200] |
| flat | placebo, same drift tercile | 8277 | +0.5 | 0.76 [0.70, 0.83] | 0.86 [0.82, 0.92] | 1.12 [1.10, 1.13] | 0.207 [0.168, 0.240] | 0.168 [0.142, 0.196] | 0.192 [0.156, 0.222] | 0.951 [0.887, 1.000] | – |
| continuation | all placebo times | 8294 | +249.0 | 0.72 [0.66, 0.78] | 0.86 [0.82, 0.91] | 1.08 [1.07, 1.10] | 0.245 [0.199, 0.286] | 0.170 [0.143, 0.202] | 0.139 [0.102, 0.166] | 0.951 [0.889, 1.000] | – |
| continuation | placebo, same drift tercile | 8294 | +249.0 | 0.72 [0.66, 0.78] | 0.86 [0.82, 0.91] | 1.08 [1.07, 1.10] | 0.237 [0.195, 0.276] | 0.181 [0.150, 0.216] | 0.210 [0.179, 0.229] | 0.929 [0.871, 0.975] | – |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | -0.022 | [-0.057, +0.011] |
| all placebo times | withdrawal_<250ms | +0.036 | [+0.009, +0.056] |
| all placebo times | transport_<250ms | -0.016 | [-0.042, +0.012] |
| all placebo times | source_>250ms | -0.117 | [-0.146, -0.081] |
| placebo, same drift tercile | kappa_20-40 | -0.022 | [-0.058, +0.008] |
| placebo, same drift tercile | withdrawal_<250ms | +0.026 | [-0.002, +0.052] |
| placebo, same drift tercile | transport_<250ms | -0.006 | [-0.049, +0.027] |
| placebo, same drift tercile | source_>250ms | +0.025 | [-0.017, +0.066] |
