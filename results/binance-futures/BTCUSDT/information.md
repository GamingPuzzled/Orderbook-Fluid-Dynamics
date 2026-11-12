# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [4 s, 6 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 1979 | -125.6 | 0.57 [0.38, 0.86] | 0.84 [0.70, 1.02] | 1.23 [1.19, 1.27] | 0.120 [0.052, 0.191] | 0.038 [0.006, 0.084] | 0.372 [0.246, 0.552] | 0.869 [0.435, 1.000] | 140 [140, 650] |
| reversal | placebo, same drift tercile | 1979 | -125.6 | 0.57 [0.38, 0.86] | 0.84 [0.70, 1.02] | 1.23 [1.19, 1.27] | 0.121 [0.057, 0.197] | 0.044 [0.002, 0.095] | 0.283 [0.153, 0.424] | 0.935 [0.504, 1.000] | 200 [140, 650] |
| flat | all placebo times | 1984 | +0.4 | 0.79 [0.49, 1.09] | 0.79 [0.68, 1.00] | 1.20 [1.15, 1.26] | 0.136 [0.062, 0.184] | 0.067 [0.018, 0.112] | 0.187 [0.079, 0.280] | 0.909 [0.531, 1.000] | 200 [140, 200] |
| flat | placebo, same drift tercile | 1984 | +0.4 | 0.79 [0.49, 1.09] | 0.79 [0.68, 1.00] | 1.20 [1.15, 1.26] | 0.135 [0.062, 0.190] | 0.085 [0.030, 0.121] | 0.257 [0.143, 0.399] | 0.911 [0.643, 1.000] | 200 [140, 650] |
| continuation | all placebo times | 1989 | +149.2 | 0.79 [0.62, 0.89] | 0.76 [0.67, 0.91] | 1.12 [1.10, 1.16] | 0.135 [0.065, 0.197] | 0.021 [0.000, 0.066] | 0.148 [0.069, 0.231] | 1.000 [0.620, 1.000] | – |
| continuation | placebo, same drift tercile | 1989 | +149.2 | 0.79 [0.62, 0.89] | 0.76 [0.67, 0.91] | 1.12 [1.10, 1.16] | 0.130 [0.065, 0.184] | 0.025 [0.001, 0.069] | 0.187 [0.102, 0.327] | 1.000 [0.242, 1.000] | – |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | +0.219 | [-0.117, +0.408] |
| all placebo times | withdrawal_<250ms | +0.016 | [-0.022, +0.057] |
| all placebo times | transport_<250ms | -0.017 | [-0.046, +0.013] |
| all placebo times | source_>250ms | -0.225 | [-0.332, -0.131] |
| placebo, same drift tercile | kappa_20-40 | +0.219 | [-0.141, +0.370] |
| placebo, same drift tercile | withdrawal_<250ms | +0.009 | [-0.029, +0.047] |
| placebo, same drift tercile | transport_<250ms | -0.019 | [-0.052, +0.026] |
| placebo, same drift tercile | source_>250ms | -0.095 | [-0.180, +0.008] |
