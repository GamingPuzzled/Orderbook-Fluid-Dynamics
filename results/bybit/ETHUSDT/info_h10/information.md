# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [9 s, 11 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 5252 | -146.6 | 0.63 [0.59, 0.67] | 0.85 [0.81, 0.89] | 1.09 [1.08, 1.11] | 0.205 [0.173, 0.240] | 0.080 [0.067, 0.095] | 0.114 [0.093, 0.135] | 0.808 [0.727, 0.880] | 140 [100, 140] |
| reversal | placebo, same drift tercile | 5252 | -146.6 | 0.63 [0.59, 0.67] | 0.85 [0.81, 0.89] | 1.09 [1.08, 1.11] | 0.206 [0.174, 0.242] | 0.079 [0.065, 0.095] | 0.106 [0.078, 0.127] | 0.807 [0.720, 0.861] | 140 [100, 140] |
| flat | all placebo times | 5270 | -0.1 | 0.62 [0.56, 0.67] | 0.85 [0.81, 0.89] | 1.09 [1.08, 1.11] | 0.192 [0.164, 0.223] | 0.082 [0.061, 0.100] | 0.065 [0.045, 0.093] | 0.799 [0.709, 0.891] | 100 [100, 140] |
| flat | placebo, same drift tercile | 5270 | -0.1 | 0.62 [0.56, 0.67] | 0.85 [0.81, 0.89] | 1.09 [1.08, 1.11] | 0.192 [0.167, 0.223] | 0.086 [0.063, 0.103] | 0.093 [0.070, 0.119] | 0.788 [0.690, 0.876] | 100 [100, 140] |
| continuation | all placebo times | 5288 | +152.7 | 0.59 [0.54, 0.64] | 0.85 [0.80, 0.88] | 1.06 [1.05, 1.08] | 0.222 [0.188, 0.269] | 0.101 [0.077, 0.121] | 0.090 [0.072, 0.109] | 0.826 [0.728, 0.863] | – |
| continuation | placebo, same drift tercile | 5288 | +152.7 | 0.59 [0.54, 0.64] | 0.85 [0.80, 0.88] | 1.06 [1.05, 1.08] | 0.217 [0.182, 0.265] | 0.104 [0.079, 0.128] | 0.108 [0.086, 0.129] | 0.829 [0.740, 0.859] | 140 [140, 140] |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | -0.033 | [-0.062, -0.003] |
| all placebo times | withdrawal_<250ms | +0.017 | [-0.002, +0.040] |
| all placebo times | transport_<250ms | +0.021 | [+0.005, +0.040] |
| all placebo times | source_>250ms | -0.025 | [-0.045, +0.003] |
| placebo, same drift tercile | kappa_20-40 | -0.033 | [-0.063, -0.001] |
| placebo, same drift tercile | withdrawal_<250ms | +0.011 | [-0.013, +0.031] |
| placebo, same drift tercile | transport_<250ms | +0.025 | [+0.006, +0.047] |
| placebo, same drift tercile | source_>250ms | +0.002 | [-0.018, +0.022] |
