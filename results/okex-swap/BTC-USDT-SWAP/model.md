# Two-phase refill model (transport + withdrawal + delayed source)

Excess vs state-matched placebo, fractions of pre-shock swept-side depth. Per window: transport = deep depletion matched by near (d ≤ 5) build-up; withdrawal = unmatched deep depletion; source = near build-up beyond deep depletion. Nonparametric over observed windows 20–1000 ms (0–20 ms sweep absorption excluded); 95% day-cluster bootstrap CIs. Centroid = mass-weighted mean time; switch = start of first window from which source > transport in all later windows.

## Deep zones: 6-10, 11-20, 21-50, 51+

| stat | value | 95% CI |
|---|---|---|
| transport | 0.480 | [0.265, 0.758] |
| withdrawal | 0.140 | [0.078, 0.219] |
| source | 0.345 | [0.229, 0.502] |
| transport_<250ms | 0.192 | [0.155, 0.229] |
| withdrawal_<250ms | 0.140 | [0.078, 0.219] |
| source_<250ms | 0.089 | [0.044, 0.153] |
| source_>250ms | 0.256 | [0.174, 0.352] |
| transport_centroid_ms | 371.544 | [230.442, 448.316] |
| withdrawal_centroid_ms | 52.435 | [45.429, 59.608] |
| source_centroid_ms | 397.261 | [358.552, 445.234] |
| t_switch_ms | nan | [80.000, 650.000] |
| transport_share_<250ms | 0.683 | [0.553, 0.800] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | 0.1043 | 0.1428 | 0.1043 | 0.0385 | 0.0000 |
| 40-60 | 0.0256 | 0.0720 | 0.0256 | 0.0464 | 0.0000 |
| 60-80 | 0.0131 | 0.0687 | 0.0131 | 0.0556 | 0.0000 |
| 80-100 | 0.0228 | 0.0177 | 0.0177 | 0.0000 | 0.0051 |
| 100-140 | 0.0515 | 0.0077 | 0.0077 | 0.0000 | 0.0439 |
| 140-200 | 0.0642 | 0.0240 | 0.0240 | 0.0000 | 0.0402 |
| 200-300 | 0.1022 | 0.0351 | 0.0351 | 0.0000 | 0.0671 |
| 300-450 | 0.1246 | 0.0611 | 0.0611 | 0.0000 | 0.0635 |
| 450-650 | 0.1554 | 0.0846 | 0.0846 | 0.0000 | 0.0708 |
| 650-1000 | 0.1616 | 0.1070 | 0.1070 | 0.0000 | 0.0546 |

## Deep zones: 6-10, 11-20, 21-50

| stat | value | 95% CI |
|---|---|---|
| transport | 0.392 | [0.260, 0.550] |
| withdrawal | 0.027 | [0.005, 0.051] |
| source | 0.433 | [0.226, 0.682] |
| transport_<250ms | 0.146 | [0.114, 0.177] |
| withdrawal_<250ms | 0.027 | [0.005, 0.051] |
| source_<250ms | 0.136 | [0.072, 0.211] |
| source_>250ms | 0.298 | [0.151, 0.485] |
| transport_centroid_ms | 377.241 | [264.550, 445.089] |
| withdrawal_centroid_ms | 61.297 | [50.000, 70.000] |
| source_centroid_ms | 386.868 | [342.700, 416.177] |
| t_switch_ms | nan | [80.000, 300.000] |
| transport_share_<250ms | 0.518 | [0.379, 0.670] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | 0.1043 | 0.0575 | 0.0575 | 0.0000 | 0.0468 |
| 40-60 | 0.0256 | 0.0375 | 0.0256 | 0.0119 | 0.0000 |
| 60-80 | 0.0131 | 0.0286 | 0.0131 | 0.0155 | 0.0000 |
| 80-100 | 0.0228 | 0.0096 | 0.0096 | 0.0000 | 0.0132 |
| 100-140 | 0.0515 | 0.0122 | 0.0122 | 0.0000 | 0.0393 |
| 140-200 | 0.0642 | 0.0278 | 0.0278 | 0.0000 | 0.0364 |
| 200-300 | 0.1022 | 0.0424 | 0.0424 | 0.0000 | 0.0598 |
| 300-450 | 0.1246 | 0.0505 | 0.0505 | 0.0000 | 0.0741 |
| 450-650 | 0.1554 | 0.0693 | 0.0693 | 0.0000 | 0.0861 |
| 650-1000 | 0.1616 | 0.0839 | 0.0839 | 0.0000 | 0.0777 |
