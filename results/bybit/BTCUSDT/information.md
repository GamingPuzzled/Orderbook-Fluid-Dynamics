# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [4 s, 6 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 8295 | -158.0 | 0.75 [0.70, 0.83] | 0.88 [0.83, 0.93] | 1.13 [1.12, 1.15] | 0.206 [0.161, 0.242] | 0.182 [0.155, 0.212] | 0.291 [0.249, 0.328] | 0.910 [0.853, 0.973] | 140 [140, 200] |
| reversal | placebo, same drift tercile | 8295 | -158.0 | 0.75 [0.70, 0.83] | 0.88 [0.83, 0.93] | 1.13 [1.12, 1.15] | 0.210 [0.165, 0.246] | 0.180 [0.149, 0.210] | 0.192 [0.151, 0.228] | 0.927 [0.868, 0.995] | – |
| flat | all placebo times | 8308 | +0.5 | 0.74 [0.69, 0.82] | 0.86 [0.81, 0.91] | 1.12 [1.10, 1.14] | 0.214 [0.174, 0.255] | 0.157 [0.130, 0.184] | 0.139 [0.105, 0.169] | 0.922 [0.874, 0.983] | 140 [140, 200] |
| flat | placebo, same drift tercile | 8308 | +0.5 | 0.74 [0.69, 0.82] | 0.86 [0.81, 0.91] | 1.12 [1.10, 1.14] | 0.219 [0.177, 0.258] | 0.173 [0.148, 0.199] | 0.178 [0.152, 0.202] | 0.912 [0.856, 0.957] | – |
| continuation | all placebo times | 8317 | +185.8 | 0.71 [0.66, 0.77] | 0.86 [0.82, 0.91] | 1.07 [1.05, 1.08] | 0.239 [0.197, 0.278] | 0.165 [0.137, 0.197] | 0.118 [0.082, 0.146] | 0.960 [0.903, 1.000] | – |
| continuation | placebo, same drift tercile | 8317 | +185.8 | 0.71 [0.66, 0.77] | 0.86 [0.82, 0.91] | 1.07 [1.05, 1.08] | 0.231 [0.190, 0.265] | 0.174 [0.143, 0.206] | 0.207 [0.167, 0.228] | 0.938 [0.884, 0.988] | – |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | -0.042 | [-0.081, -0.005] |
| all placebo times | withdrawal_<250ms | +0.033 | [+0.010, +0.052] |
| all placebo times | transport_<250ms | -0.017 | [-0.041, +0.006] |
| all placebo times | source_>250ms | -0.173 | [-0.215, -0.130] |
| placebo, same drift tercile | kappa_20-40 | -0.042 | [-0.081, -0.009] |
| placebo, same drift tercile | withdrawal_<250ms | +0.021 | [-0.000, +0.045] |
| placebo, same drift tercile | transport_<250ms | -0.006 | [-0.043, +0.021] |
| placebo, same drift tercile | source_>250ms | +0.015 | [-0.028, +0.063] |
