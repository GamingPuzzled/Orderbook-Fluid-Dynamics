# Two-phase refill model (transport + withdrawal + delayed source)

Excess vs state-matched placebo, fractions of pre-shock swept-side depth. Per window: transport = deep depletion matched by near (d ≤ 5) build-up; withdrawal = unmatched deep depletion; source = near build-up beyond deep depletion. Nonparametric over observed windows 20–1000 ms (0–20 ms sweep absorption excluded); 95% day-cluster bootstrap CIs. Centroid = mass-weighted mean time; switch = start of first window from which source > transport in all later windows.

## Deep zones: 6-10, 11-20, 21-50, 51+

| stat | value | 95% CI |
|---|---|---|
| transport | 0.112 | [0.098, 0.223] |
| withdrawal | 0.211 | [0.095, 0.359] |
| source | 0.082 | [0.032, 0.130] |
| transport_<250ms | 0.077 | [0.068, 0.089] |
| withdrawal_<250ms | 0.211 | [0.087, 0.359] |
| source_<250ms | 0.000 | [0.000, 0.007] |
| source_>250ms | 0.082 | [0.032, 0.128] |
| transport_centroid_ms | 206.896 | [151.736, 423.858] |
| withdrawal_centroid_ms | 98.939 | [87.558, 137.254] |
| source_centroid_ms | 501.394 | [339.532, 559.597] |
| t_switch_ms | 200.000 | [200.000, 650.000] |
| transport_share_<250ms | 1.000 | [0.909, 1.000] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | -0.0160 | -0.0016 | 0.0000 | 0.0000 | 0.0000 |
| 40-60 | -0.0092 | 0.0313 | 0.0000 | 0.0313 | 0.0000 |
| 60-80 | 0.0373 | 0.1035 | 0.0373 | 0.0662 | 0.0000 |
| 80-100 | 0.0086 | 0.0157 | 0.0086 | 0.0070 | 0.0000 |
| 100-140 | 0.0146 | 0.0958 | 0.0146 | 0.0812 | 0.0000 |
| 140-200 | 0.0164 | 0.0417 | 0.0164 | 0.0253 | 0.0000 |
| 200-300 | 0.0196 | 0.0059 | 0.0059 | 0.0000 | 0.0137 |
| 300-450 | 0.0426 | 0.0134 | 0.0134 | 0.0000 | 0.0292 |
| 450-650 | 0.0366 | 0.0160 | 0.0160 | 0.0000 | 0.0206 |
| 650-1000 | 0.0190 | -0.0004 | 0.0000 | 0.0000 | 0.0190 |

## Deep zones: 6-10, 11-20, 21-50

| stat | value | 95% CI |
|---|---|---|
| transport | 0.050 | [0.011, 0.144] |
| withdrawal | 0.001 | [0.000, 0.034] |
| source | 0.145 | [0.098, 0.208] |
| transport_<250ms | 0.033 | [0.007, 0.054] |
| withdrawal_<250ms | 0.001 | [0.000, 0.034] |
| source_<250ms | 0.044 | [0.024, 0.079] |
| source_>250ms | 0.100 | [0.049, 0.164] |
| transport_centroid_ms | 282.038 | [191.681, 475.048] |
| withdrawal_centroid_ms | 120.000 | [90.000, 170.000] |
| source_centroid_ms | 348.828 | [219.211, 454.667] |
| t_switch_ms | 200.000 | [60.000, 450.000] |
| transport_share_<250ms | 0.425 | [0.081, 0.654] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | -0.0160 | -0.0019 | 0.0000 | 0.0000 | 0.0000 |
| 40-60 | -0.0092 | -0.0062 | 0.0000 | 0.0000 | 0.0000 |
| 60-80 | 0.0373 | -0.0071 | 0.0000 | 0.0000 | 0.0373 |
| 80-100 | 0.0086 | 0.0025 | 0.0025 | 0.0000 | 0.0062 |
| 100-140 | 0.0146 | 0.0158 | 0.0146 | 0.0012 | 0.0000 |
| 140-200 | 0.0164 | 0.0156 | 0.0156 | 0.0000 | 0.0008 |
| 200-300 | 0.0196 | -0.0023 | 0.0000 | 0.0000 | 0.0196 |
| 300-450 | 0.0426 | 0.0047 | 0.0047 | 0.0000 | 0.0379 |
| 450-650 | 0.0366 | 0.0096 | 0.0096 | 0.0000 | 0.0270 |
| 650-1000 | 0.0190 | 0.0029 | 0.0029 | 0.0000 | 0.0161 |
