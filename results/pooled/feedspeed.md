# Feed-speed emulation

Excess (sweep − NN placebo) masses, fractions of pre-sweep swept depth, 95% day bootstrap (200). Emulated feeds: Bybit messages netted into fixed-clock buckets.

## Repositioning by levels cleared

| feed | levels cleared | sweeps | repositioning <250 | withdrawal <250 | new liq. >250 |
|---|---|---|---|---|---|
| Bybit, 20 ms feed | all | 25406 | 0.173 [0.148, 0.198] | 0.218 [0.176, 0.254] | 0.193 [0.161, 0.215] |
| Bybit, 20 ms feed | 3-40 | 7243 | 0.072 [0.057, 0.098] | 0.176 [0.132, 0.215] | 0.174 [0.134, 0.198] |
| Bybit, 20 ms feed | 40-80 | 6356 | 0.131 [0.101, 0.151] | 0.211 [0.169, 0.245] | 0.164 [0.135, 0.190] |
| Bybit, 20 ms feed | 80-+ | 11796 | 0.284 [0.232, 0.333] | 0.272 [0.210, 0.319] | 0.198 [0.144, 0.240] |
| Bybit, emulated 52 ms | all | 25406 | 0.065 [0.052, 0.078] | 0.179 [0.143, 0.212] | 0.162 [0.138, 0.184] |
| Bybit, emulated 52 ms | 3-40 | 7243 | 0.028 [0.015, 0.041] | 0.218 [0.179, 0.250] | 0.138 [0.110, 0.160] |
| Bybit, emulated 52 ms | 40-80 | 6356 | 0.058 [0.043, 0.070] | 0.172 [0.127, 0.214] | 0.127 [0.100, 0.157] |
| Bybit, emulated 52 ms | 80-+ | 11796 | 0.097 [0.076, 0.123] | 0.217 [0.177, 0.249] | 0.179 [0.130, 0.214] |
| Binance, 52 ms feed | all | 5958 | 0.038 [0.008, 0.089] | 0.134 [0.062, 0.195] | 0.238 [0.131, 0.346] |
| Binance, 52 ms feed | 3-40 | 2362 | 0.002 [0.000, 0.027] | 0.100 [0.061, 0.139] | 0.174 [0.101, 0.241] |
| Binance, 52 ms feed | 40-80 | 1756 | 0.043 [0.010, 0.099] | 0.150 [0.052, 0.255] | 0.159 [0.072, 0.291] |
| Binance, 52 ms feed | 80-+ | 1838 | 0.113 [0.044, 0.214] | 0.167 [0.105, 0.278] | 0.362 [0.178, 0.574] |

## Feed-speed curve (Bybit BTCUSDT, all sweeps)

| netting (ms) | placebo add/cancel | repositioning <250 | repositioning total | share of 20 ms (<250) | share of 20 ms (total) |
|---|---|---|---|---|---|
| 20 | 1.029 | 0.173 [0.148, 0.198] | 0.267 [0.223, 0.333] | 1.00 | 1.00 |
| 52 | 1.043 | 0.065 [0.052, 0.078] | 0.084 [0.072, 0.099] | 0.38 | 0.31 |
| 100 | 1.053 | 0.011 [0.005, 0.017] | 0.019 [0.009, 0.035] | 0.06 | 0.07 |
| 200 | 1.057 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.003] | 0.00 | 0.00 |

Exponential fit on positive points (20, 52, 100 ms): measured repositioning <250 falls by a factor e every 29 ms of netting; extrapolated to no netting: 0.365 (20 ms observed 0.173). Extrapolation is indicative only.
