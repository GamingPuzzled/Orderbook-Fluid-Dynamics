# Repositioning and the relative tick size within assets

Day-level excess statistics (NN placebo, near zone d ≤ 5 ticks) regressed on log10 median tick (bp of mid), with asset fixed effects; days with ≥ 10 sweeps, weighted by sweeps. β = change per tenfold increase in the relative tick. HC1 SE and 95% day bootstrap (stratified by asset).

Assets: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, LINKUSDT; days: 156.

| sample | statistic | specification | β (per 10× tick) | HC1 SE | 95% bootstrap | days |
|---|---|---|---|---|---|---|
| all assets | transport_<250ms | asset FE | -0.039 | 0.026 | [-0.100, +0.010] | 156 |
| all assets | transport_<250ms | asset FE + depth | -0.030 | 0.044 | [-0.115, +0.042] | 156 |
| all assets | withdrawal_<250ms | asset FE | -0.034 | 0.055 | [-0.148, +0.079] | 156 |
| all assets | withdrawal_<250ms | asset FE + depth | +0.004 | 0.075 | [-0.143, +0.144] | 156 |
| all assets | source_>250ms | asset FE | +0.001 | 0.028 | [-0.056, +0.062] | 156 |
| all assets | source_>250ms | asset FE + depth | +0.053 | 0.042 | [-0.031, +0.143] | 156 |
| all assets | kappa_20-40 | asset FE | -0.196 | 0.084 | [-0.364, -0.023] | 156 |
| all assets | kappa_20-40 | asset FE + depth | -0.082 | 0.104 | [-0.322, +0.119] | 156 |
| BTC + ETH | transport_<250ms | asset FE | -0.064 | 0.045 | [-0.155, +0.019] | 85 |
| BTC + ETH | transport_<250ms | asset FE + depth | -0.054 | 0.049 | [-0.140, +0.037] | 85 |
| BTC + ETH | withdrawal_<250ms | asset FE | +0.063 | 0.087 | [-0.114, +0.213] | 85 |
| BTC + ETH | withdrawal_<250ms | asset FE + depth | +0.057 | 0.089 | [-0.106, +0.231] | 85 |
| BTC + ETH | source_>250ms | asset FE | +0.021 | 0.046 | [-0.075, +0.108] | 85 |
| BTC + ETH | source_>250ms | asset FE + depth | +0.048 | 0.050 | [-0.050, +0.153] | 85 |
| BTC + ETH | kappa_20-40 | asset FE | -0.393 | 0.127 | [-0.629, -0.137] | 85 |
| BTC + ETH | kappa_20-40 | asset FE + depth | -0.287 | 0.114 | [-0.515, -0.051] | 85 |

## By exchange tick (sweep-weighted repositioning < 250 ms)

| asset | tick | days | median tick (bp) | repositioning |
|---|---|---|---|---|
| BTCUSDT | 0.1 | 42 | 0.014 | 0.156 |
| ETHUSDT | 0.01 | 43 | 0.041 | 0.084 |
| LINKUSDT | 0.001 | 22 | 0.688 | 0.002 |
| SOLUSDT | 0.001 | 10 | 0.209 | 0.009 |
| SOLUSDT | 0.01 | 20 | 0.624 | 0.003 |
| XRPUSDT | 0.0001 | 19 | 0.463 | 0.008 |
