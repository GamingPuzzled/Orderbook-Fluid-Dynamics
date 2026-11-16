# Refill by post-sweep price drift (information content of the sweep)

Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of trades in [4 s, 6 s], positive = continuation in the sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within day); pool (b) restricts placebo times to the same tercile of their own drift. 95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.

| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal | all placebo times | 3545 | -138.3 | 0.91 [0.80, 1.02] | 0.85 [0.77, 0.94] | 1.11 [1.09, 1.14] | 0.156 [0.094, 0.234] | 0.164 [0.136, 0.194] | 0.356 [0.208, 0.482] | 0.605 [0.499, 0.744] | 650 [80, 650] |
| reversal | placebo, same drift tercile | 3545 | -138.3 | 0.91 [0.80, 1.02] | 0.85 [0.77, 0.94] | 1.11 [1.09, 1.14] | 0.156 [0.096, 0.235] | 0.168 [0.139, 0.205] | 0.277 [0.093, 0.392] | 0.593 [0.491, 0.748] | 650 [86, 650] |
| flat | all placebo times | 3549 | +0.5 | 0.89 [0.79, 1.03] | 0.84 [0.75, 0.95] | 1.09 [1.08, 1.11] | 0.141 [0.079, 0.256] | 0.162 [0.130, 0.196] | 0.191 [0.121, 0.247] | 0.685 [0.586, 0.769] | 100 [80, 650] |
| flat | placebo, same drift tercile | 3549 | +0.5 | 0.89 [0.79, 1.03] | 0.84 [0.75, 0.95] | 1.09 [1.08, 1.11] | 0.136 [0.077, 0.247] | 0.198 [0.153, 0.251] | 0.199 [0.114, 0.273] | 0.716 [0.614, 0.798] | – |
| continuation | all placebo times | 3553 | +162.4 | 0.88 [0.80, 1.00] | 0.87 [0.79, 0.97] | 1.06 [1.04, 1.07] | 0.140 [0.073, 0.215] | 0.183 [0.133, 0.230] | 0.187 [0.133, 0.250] | 0.707 [0.560, 0.844] | – |
| continuation | placebo, same drift tercile | 3553 | +162.4 | 0.88 [0.80, 1.00] | 0.87 [0.79, 0.97] | 1.06 [1.04, 1.07] | 0.141 [0.076, 0.215] | 0.189 [0.138, 0.245] | 0.280 [0.212, 0.362] | 0.687 [0.550, 0.828] | – |

## Continuation − reversal (paired day bootstrap, 95% CI)

| placebo pool | statistic | difference | 95% CI |
|---|---|---|---|
| all placebo times | kappa_20-40 | -0.025 | [-0.072, +0.029] |
| all placebo times | withdrawal_<250ms | -0.016 | [-0.056, +0.011] |
| all placebo times | transport_<250ms | +0.019 | [-0.029, +0.068] |
| all placebo times | source_>250ms | -0.170 | [-0.246, -0.054] |
| placebo, same drift tercile | kappa_20-40 | -0.025 | [-0.082, +0.028] |
| placebo, same drift tercile | withdrawal_<250ms | -0.016 | [-0.040, +0.012] |
| placebo, same drift tercile | transport_<250ms | +0.021 | [-0.041, +0.063] |
| placebo, same drift tercile | source_>250ms | +0.003 | [-0.068, +0.132] |
