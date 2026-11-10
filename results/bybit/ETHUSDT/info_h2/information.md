# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [1 s, 3 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 5287 | -80.9 | 0.64 [0.59, 0.68] | 0.84 [0.81, 0.88] | 1.11 [1.09, 1.14] | 0.199 [0.162, 0.236] | 0.076 [0.061, 0.092] | 0.132 [0.108, 0.153] | 0.788 [0.715, 0.854] | 140 [100, 140] |
| reversal | placebo, same drift tercile | 5287 | -80.9 | 0.64 [0.59, 0.68] | 0.84 [0.81, 0.88] | 1.11 [1.09, 1.14] | 0.204 [0.166, 0.241] | 0.073 [0.059, 0.090] | 0.076 [0.058, 0.105] | 0.791 [0.704, 0.865] | – |
| flat | all placebo times | 5304 | +0.5 | 0.61 [0.54, 0.67] | 0.88 [0.83, 0.92] | 1.09 [1.07, 1.11] | 0.189 [0.161, 0.225] | 0.094 [0.066, 0.112] | 0.058 [0.040, 0.085] | 0.856 [0.727, 0.901] | – |
| flat | placebo, same drift tercile | 5304 | +0.5 | 0.61 [0.54, 0.67] | 0.88 [0.83, 0.92] | 1.09 [1.07, 1.11] | 0.189 [0.161, 0.224] | 0.100 [0.071, 0.120] | 0.107 [0.081, 0.128] | 0.858 [0.722, 0.897] | 140 [100, 140] |
| continuation | all placebo times | 5322 | +99.1 | 0.59 [0.54, 0.65] | 0.84 [0.80, 0.87] | 1.04 [1.03, 1.06] | 0.226 [0.188, 0.267] | 0.100 [0.074, 0.121] | 0.072 [0.053, 0.092] | 0.816 [0.716, 0.863] | – |
| continuation | placebo, same drift tercile | 5322 | +99.1 | 0.59 [0.54, 0.65] | 0.84 [0.80, 0.87] | 1.04 [1.03, 1.06] | 0.221 [0.181, 0.261] | 0.100 [0.074, 0.121] | 0.136 [0.107, 0.162] | 0.808 [0.702, 0.878] | 140 [100, 140] |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | -0.046 | [-0.080, -0.014] |
| all placebo times | withdrawal_<250ms | +0.026 | [+0.003, +0.051] |
| all placebo times | transport_<250ms | +0.024 | [+0.002, +0.052] |
| all placebo times | source_>250ms | -0.059 | [-0.077, -0.037] |
| placebo, same drift tercile | kappa_20-40 | -0.046 | [-0.081, -0.011] |
| placebo, same drift tercile | withdrawal_<250ms | +0.017 | [-0.019, +0.042] |
| placebo, same drift tercile | transport_<250ms | +0.028 | [+0.008, +0.053] |
| placebo, same drift tercile | source_>250ms | +0.060 | [+0.022, +0.096] |
