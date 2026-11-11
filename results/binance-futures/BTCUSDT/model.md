# Two-phase refill model (transport + withdrawal + delayed source)

Excess vs state-matched placebo, fractions of pre-shock swept-side depth. Per window: transport = deep depletion matched by near (d ≤ 5) build-up; withdrawal = unmatched deep depletion; source = near build-up beyond deep depletion. Nonparametric over observed windows 20–1000 ms (0–20 ms sweep absorption excluded); 95% day-cluster bootstrap CIs. Centroid = mass-weighted mean time; switch = start of first window from which source > transport in all later windows.

## Deep zones: 6-10, 11-20, 21-50, 51+

| stat | value | 95% CI |
|---|---|---|
| transport | 0.140 | [0.109, 0.233] |
| withdrawal | 0.215 | [0.095, 0.360] |
| source | 0.083 | [0.032, 0.130] |
| transport_<250ms | 0.091 | [0.068, 0.126] |
| withdrawal_<250ms | 0.215 | [0.087, 0.360] |
| source_<250ms | 0.000 | [0.000, 0.007] |
| source_>250ms | 0.083 | [0.032, 0.128] |
| transport_centroid_ms | 237.618 | [141.572, 428.500] |
| withdrawal_centroid_ms | 98.042 | [87.480, 137.254] |
| source_centroid_ms | 503.052 | [355.959, 559.597] |
| t_switch_ms | 200.000 | [200.000, 650.000] |
| transport_share_<250ms | 1.000 | [0.926, 1.000] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | -0.0156 | -0.0012 | 0.0000 | 0.0000 | 0.0000 |
| 40-60 | -0.0053 | 0.0352 | 0.0000 | 0.0352 | 0.0000 |
| 60-80 | 0.0484 | 0.1146 | 0.0484 | 0.0662 | 0.0000 |
| 80-100 | 0.0104 | 0.0174 | 0.0104 | 0.0070 | 0.0000 |
| 100-140 | 0.0185 | 0.0997 | 0.0185 | 0.0812 | 0.0000 |
| 140-200 | 0.0142 | 0.0395 | 0.0142 | 0.0253 | 0.0000 |
| 200-300 | 0.0182 | 0.0045 | 0.0045 | 0.0000 | 0.0137 |
| 300-450 | 0.0462 | 0.0170 | 0.0170 | 0.0000 | 0.0292 |
| 450-650 | 0.0410 | 0.0204 | 0.0204 | 0.0000 | 0.0206 |
| 650-1000 | 0.0262 | 0.0068 | 0.0068 | 0.0000 | 0.0194 |

## Deep zones: 6-10, 11-20, 21-50

| stat | value | 95% CI |
|---|---|---|
| transport | 0.113 | [0.053, 0.172] |
| withdrawal | 0.072 | [0.027, 0.177] |
| source | 0.110 | [0.039, 0.203] |
| transport_<250ms | 0.086 | [0.036, 0.126] |
| withdrawal_<250ms | 0.072 | [0.027, 0.177] |
| source_<250ms | 0.006 | [0.000, 0.031] |
| source_>250ms | 0.104 | [0.039, 0.184] |
| transport_centroid_ms | 207.765 | [138.619, 442.665] |
| withdrawal_centroid_ms | 110.929 | [94.748, 146.327] |
| source_centroid_ms | 469.324 | [316.081, 470.232] |
| t_switch_ms | 200.000 | [200.000, 300.000] |
| transport_share_<250ms | 0.937 | [0.536, 1.000] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | -0.0156 | -0.0022 | 0.0000 | 0.0000 | 0.0000 |
| 40-60 | -0.0053 | 0.0117 | 0.0000 | 0.0117 | 0.0000 |
| 60-80 | 0.0484 | 0.0575 | 0.0484 | 0.0091 | 0.0000 |
| 80-100 | 0.0104 | 0.0047 | 0.0047 | 0.0000 | 0.0057 |
| 100-140 | 0.0185 | 0.0567 | 0.0185 | 0.0382 | 0.0000 |
| 140-200 | 0.0142 | 0.0267 | 0.0142 | 0.0125 | 0.0000 |
| 200-300 | 0.0182 | -0.0017 | 0.0000 | 0.0000 | 0.0182 |
| 300-450 | 0.0462 | 0.0100 | 0.0100 | 0.0000 | 0.0363 |
| 450-650 | 0.0410 | 0.0119 | 0.0119 | 0.0000 | 0.0291 |
| 650-1000 | 0.0262 | 0.0059 | 0.0059 | 0.0000 | 0.0203 |
