# Two-phase refill model (transport + withdrawal + delayed source)

Excess vs state-matched placebo, fractions of pre-shock swept-side depth. Per window: transport = deep depletion matched by near (d ≤ 5) build-up; withdrawal = unmatched deep depletion; source = near build-up beyond deep depletion. Nonparametric over observed windows 20–1000 ms (0–20 ms sweep absorption excluded); 95% day-cluster bootstrap CIs. Centroid = mass-weighted mean time; switch = start of first window from which source > transport in all later windows.

## Deep zones: 6-10, 11-20, 21-50, 51+

| stat | value | 95% CI |
|---|---|---|
| transport | 0.336 | [0.260, 0.410] |
| withdrawal | 0.215 | [0.175, 0.251] |
| source | 0.219 | [0.187, 0.250] |
| transport_<250ms | 0.187 | [0.159, 0.212] |
| withdrawal_<250ms | 0.215 | [0.175, 0.251] |
| source_<250ms | 0.014 | [0.005, 0.024] |
| source_>250ms | 0.205 | [0.174, 0.232] |
| transport_centroid_ms | 321.795 | [253.183, 365.684] |
| withdrawal_centroid_ms | 68.921 | [65.363, 72.452] |
| source_centroid_ms | 506.732 | [473.749, 544.454] |
| t_switch_ms | nan | [140.000, 200.000] |
| transport_share_<250ms | 0.932 | [0.889, 0.972] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | 0.0499 | 0.1385 | 0.0499 | 0.0885 | 0.0000 |
| 40-60 | 0.0593 | 0.0663 | 0.0593 | 0.0070 | 0.0000 |
| 60-80 | 0.0244 | 0.0501 | 0.0244 | 0.0257 | 0.0000 |
| 80-100 | 0.0123 | 0.0541 | 0.0123 | 0.0418 | 0.0000 |
| 100-140 | 0.0175 | 0.0697 | 0.0175 | 0.0523 | 0.0000 |
| 140-200 | 0.0368 | 0.0232 | 0.0232 | 0.0000 | 0.0136 |
| 200-300 | 0.0535 | 0.0162 | 0.0162 | 0.0000 | 0.0374 |
| 300-450 | 0.0710 | 0.0250 | 0.0250 | 0.0000 | 0.0460 |
| 450-650 | 0.0954 | 0.0279 | 0.0279 | 0.0000 | 0.0675 |
| 650-1000 | 0.1342 | 0.0799 | 0.0799 | 0.0000 | 0.0543 |

## Deep zones: 6-10, 11-20, 21-50

| stat | value | 95% CI |
|---|---|---|
| transport | 0.332 | [0.269, 0.391] |
| withdrawal | 0.035 | [0.022, 0.050] |
| source | 0.223 | [0.196, 0.250] |
| transport_<250ms | 0.149 | [0.124, 0.170] |
| withdrawal_<250ms | 0.035 | [0.022, 0.050] |
| source_<250ms | 0.051 | [0.032, 0.073] |
| source_>250ms | 0.171 | [0.148, 0.193] |
| transport_centroid_ms | 356.812 | [313.876, 390.395] |
| withdrawal_centroid_ms | 108.876 | [101.196, 113.376] |
| source_centroid_ms | 451.285 | [403.872, 496.929] |
| t_switch_ms | nan | [200.000, 300.000] |
| transport_share_<250ms | 0.743 | [0.658, 0.827] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | 0.0499 | 0.0376 | 0.0376 | 0.0000 | 0.0123 |
| 40-60 | 0.0593 | 0.0336 | 0.0336 | 0.0000 | 0.0257 |
| 60-80 | 0.0244 | 0.0246 | 0.0244 | 0.0002 | 0.0000 |
| 80-100 | 0.0123 | 0.0250 | 0.0123 | 0.0128 | 0.0000 |
| 100-140 | 0.0175 | 0.0398 | 0.0175 | 0.0223 | 0.0000 |
| 140-200 | 0.0368 | 0.0235 | 0.0235 | 0.0000 | 0.0133 |
| 200-300 | 0.0535 | 0.0292 | 0.0292 | 0.0000 | 0.0244 |
| 300-450 | 0.0710 | 0.0344 | 0.0344 | 0.0000 | 0.0366 |
| 450-650 | 0.0954 | 0.0433 | 0.0433 | 0.0000 | 0.0521 |
| 650-1000 | 0.1342 | 0.0758 | 0.0758 | 0.0000 | 0.0584 |
