# Two-phase refill model (transport + withdrawal + delayed source)

Excess vs state-matched placebo, fractions of pre-shock swept-side depth. Per window: transport = deep depletion matched by near (d ≤ 5) build-up; withdrawal = unmatched deep depletion; source = near build-up beyond deep depletion. Nonparametric over observed windows 20–1000 ms (0–20 ms sweep absorption excluded); 95% day-cluster bootstrap CIs. Centroid = mass-weighted mean time; switch = start of first window from which source > transport in all later windows.

## Deep zones: 6-10, 11-20, 21-50, 51+

| stat | value | 95% CI |
|---|---|---|
| transport | 0.104 | [0.078, 0.137] |
| withdrawal | 0.203 | [0.166, 0.245] |
| source | 0.141 | [0.109, 0.169] |
| transport_<250ms | 0.094 | [0.074, 0.113] |
| withdrawal_<250ms | 0.203 | [0.166, 0.245] |
| source_<250ms | 0.022 | [0.015, 0.033] |
| source_>250ms | 0.119 | [0.094, 0.142] |
| transport_centroid_ms | 132.708 | [56.110, 206.157] |
| withdrawal_centroid_ms | 47.040 | [44.001, 51.277] |
| source_centroid_ms | 448.673 | [403.674, 485.996] |
| t_switch_ms | 140.000 | [100.000, 140.000] |
| transport_share_<250ms | 0.810 | [0.725, 0.857] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | 0.0280 | 0.1584 | 0.0280 | 0.1303 | 0.0000 |
| 40-60 | 0.0326 | 0.0439 | 0.0326 | 0.0113 | 0.0000 |
| 60-80 | 0.0167 | 0.0395 | 0.0167 | 0.0228 | 0.0000 |
| 80-100 | 0.0066 | 0.0454 | 0.0066 | 0.0388 | 0.0000 |
| 100-140 | 0.0115 | 0.0099 | 0.0099 | 0.0000 | 0.0016 |
| 140-200 | 0.0205 | -0.0178 | 0.0000 | 0.0000 | 0.0205 |
| 200-300 | 0.0292 | -0.0155 | 0.0000 | 0.0000 | 0.0292 |
| 300-450 | 0.0280 | -0.0056 | 0.0000 | 0.0000 | 0.0280 |
| 450-650 | 0.0329 | -0.0067 | 0.0000 | 0.0000 | 0.0329 |
| 650-1000 | 0.0388 | 0.0102 | 0.0102 | 0.0000 | 0.0286 |

## Deep zones: 6-10, 11-20, 21-50

| stat | value | 95% CI |
|---|---|---|
| transport | 0.115 | [0.087, 0.159] |
| withdrawal | 0.080 | [0.060, 0.099] |
| source | 0.130 | [0.101, 0.152] |
| transport_<250ms | 0.090 | [0.077, 0.104] |
| withdrawal_<250ms | 0.080 | [0.060, 0.099] |
| source_<250ms | 0.026 | [0.016, 0.036] |
| source_>250ms | 0.104 | [0.082, 0.120] |
| transport_centroid_ms | 201.796 | [113.887, 269.994] |
| withdrawal_centroid_ms | 58.375 | [50.045, 68.858] |
| source_centroid_ms | 414.736 | [375.285, 454.607] |
| t_switch_ms | 140.000 | [140.000, 140.000] |
| transport_share_<250ms | 0.778 | [0.731, 0.836] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | 0.0280 | 0.0696 | 0.0280 | 0.0415 | 0.0000 |
| 40-60 | 0.0326 | 0.0274 | 0.0274 | 0.0000 | 0.0053 |
| 60-80 | 0.0167 | 0.0260 | 0.0167 | 0.0093 | 0.0000 |
| 80-100 | 0.0066 | 0.0305 | 0.0066 | 0.0239 | 0.0000 |
| 100-140 | 0.0115 | 0.0167 | 0.0115 | 0.0051 | 0.0000 |
| 140-200 | 0.0205 | -0.0057 | 0.0000 | 0.0000 | 0.0205 |
| 200-300 | 0.0292 | -0.0030 | 0.0000 | 0.0000 | 0.0292 |
| 300-450 | 0.0280 | 0.0033 | 0.0033 | 0.0000 | 0.0247 |
| 450-650 | 0.0329 | 0.0048 | 0.0048 | 0.0000 | 0.0281 |
| 650-1000 | 0.0388 | 0.0170 | 0.0170 | 0.0000 | 0.0218 |
