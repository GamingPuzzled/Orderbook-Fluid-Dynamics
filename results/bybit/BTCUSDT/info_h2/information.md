# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [1 s, 3 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 8296 | -69.2 | 0.75 [0.70, 0.83] | 0.87 [0.83, 0.92] | 1.15 [1.13, 1.17] | 0.207 [0.162, 0.240] | 0.178 [0.151, 0.207] | 0.336 [0.290, 0.380] | 0.900 [0.837, 0.973] | 140 [140, 200] |
| reversal | placebo, same drift tercile | 8296 | -69.2 | 0.75 [0.70, 0.83] | 0.87 [0.83, 0.92] | 1.15 [1.13, 1.17] | 0.213 [0.166, 0.248] | 0.173 [0.145, 0.202] | 0.181 [0.134, 0.220] | 0.932 [0.878, 1.000] | – |
| flat | all placebo times | 8311 | +0.4 | 0.75 [0.69, 0.82] | 0.88 [0.82, 0.94] | 1.11 [1.09, 1.13] | 0.204 [0.166, 0.245] | 0.168 [0.140, 0.193] | 0.133 [0.096, 0.167] | 0.941 [0.862, 0.997] | 200 [140, 200] |
| flat | placebo, same drift tercile | 8311 | +0.4 | 0.75 [0.69, 0.82] | 0.88 [0.82, 0.94] | 1.11 [1.09, 1.13] | 0.206 [0.167, 0.247] | 0.185 [0.155, 0.206] | 0.171 [0.144, 0.193] | 0.952 [0.874, 0.999] | – |
| continuation | all placebo times | 8323 | +101.1 | 0.71 [0.66, 0.79] | 0.85 [0.81, 0.90] | 1.05 [1.04, 1.07] | 0.247 [0.206, 0.281] | 0.162 [0.141, 0.186] | 0.101 [0.067, 0.128] | 0.961 [0.909, 1.000] | – |
| continuation | placebo, same drift tercile | 8323 | +101.1 | 0.71 [0.66, 0.79] | 0.85 [0.81, 0.90] | 1.05 [1.04, 1.07] | 0.237 [0.197, 0.267] | 0.170 [0.145, 0.201] | 0.227 [0.190, 0.266] | 0.912 [0.862, 0.963] | – |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | -0.039 | [-0.078, -0.001] |
| all placebo times | withdrawal_<250ms | +0.040 | [+0.016, +0.065] |
| all placebo times | transport_<250ms | -0.016 | [-0.033, +0.005] |
| all placebo times | source_>250ms | -0.235 | [-0.286, -0.188] |
| placebo, same drift tercile | kappa_20-40 | -0.039 | [-0.082, -0.005] |
| placebo, same drift tercile | withdrawal_<250ms | +0.024 | [+0.000, +0.049] |
| placebo, same drift tercile | transport_<250ms | -0.003 | [-0.028, +0.023] |
| placebo, same drift tercile | source_>250ms | +0.047 | [-0.010, +0.091] |
