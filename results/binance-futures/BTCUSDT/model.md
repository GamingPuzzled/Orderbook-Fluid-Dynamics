# Two-phase refill model (transport + withdrawal + delayed source)

Excess vs state-matched placebo, fractions of pre-shock swept-side depth. Per window: transport = deep depletion matched by near (d ≤ 5) build-up; withdrawal = unmatched deep depletion; source = near build-up beyond deep depletion. Nonparametric over observed windows 20–1000 ms (0–20 ms sweep absorption excluded); 95% day-cluster bootstrap CIs. Centroid = mass-weighted mean time; switch = start of first window from which source > transport in all later windows.

## Deep zones: 6-10, 11-20, 21-50, 51+

| stat | value | 95% CI |
|---|---|---|
| transport | 0.133 | [0.051, 0.226] |
| withdrawal | 0.129 | [0.058, 0.198] |
| source | 0.269 | [0.136, 0.411] |
| transport_<250ms | 0.049 | [0.009, 0.095] |
| withdrawal_<250ms | 0.129 | [0.058, 0.198] |
| source_<250ms | 0.014 | [0.000, 0.039] |
| source_>250ms | 0.256 | [0.130, 0.385] |
| transport_centroid_ms | 422.090 | [211.404, 566.189] |
| withdrawal_centroid_ms | 88.291 | [71.010, 104.139] |
| source_centroid_ms | 472.726 | [416.451, 514.294] |
| t_switch_ms | 140.000 | [140.000, 650.000] |
| transport_share_<250ms | 0.783 | [0.364, 1.000] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | -0.0166 | 0.0001 | 0.0000 | 0.0001 | 0.0000 |
| 40-60 | 0.0059 | 0.0253 | 0.0059 | 0.0194 | 0.0000 |
| 60-80 | 0.0277 | 0.0772 | 0.0277 | 0.0495 | 0.0000 |
| 80-100 | -0.0006 | 0.0078 | 0.0000 | 0.0078 | 0.0000 |
| 100-140 | 0.0063 | 0.0581 | 0.0063 | 0.0518 | 0.0000 |
| 140-200 | 0.0223 | 0.0087 | 0.0087 | 0.0000 | 0.0135 |
| 200-300 | 0.0633 | 0.0002 | 0.0002 | 0.0000 | 0.0631 |
| 300-450 | 0.0904 | 0.0148 | 0.0148 | 0.0000 | 0.0755 |
| 450-650 | 0.0971 | 0.0399 | 0.0399 | 0.0000 | 0.0572 |
| 650-1000 | 0.0889 | 0.0290 | 0.0290 | 0.0000 | 0.0599 |

## Deep zones: 6-10, 11-20, 21-50

| stat | value | 95% CI |
|---|---|---|
| transport | 0.113 | [0.037, 0.199] |
| withdrawal | 0.036 | [0.008, 0.079] |
| source | 0.289 | [0.148, 0.442] |
| transport_<250ms | 0.043 | [0.008, 0.086] |
| withdrawal_<250ms | 0.036 | [0.008, 0.079] |
| source_<250ms | 0.019 | [0.001, 0.051] |
| source_>250ms | 0.270 | [0.132, 0.407] |
| transport_centroid_ms | 421.091 | [200.411, 587.658] |
| withdrawal_centroid_ms | 100.242 | [59.882, 120.000] |
| source_centroid_ms | 469.714 | [413.845, 498.373] |
| t_switch_ms | 140.000 | [140.000, 650.000] |
| transport_share_<250ms | 0.699 | [0.283, 0.986] |

| window (ms) | near build | deep depletion | transport | withdrawal | source |
|---|---|---|---|---|---|
| 20-40 | -0.0166 | -0.0016 | 0.0000 | 0.0000 | 0.0000 |
| 40-60 | 0.0059 | 0.0059 | 0.0059 | 0.0000 | 0.0000 |
| 60-80 | 0.0277 | 0.0408 | 0.0277 | 0.0131 | 0.0000 |
| 80-100 | -0.0006 | 0.0016 | 0.0000 | 0.0016 | 0.0000 |
| 100-140 | 0.0063 | 0.0272 | 0.0063 | 0.0209 | 0.0000 |
| 140-200 | 0.0223 | 0.0035 | 0.0035 | 0.0000 | 0.0187 |
| 200-300 | 0.0633 | -0.0021 | 0.0000 | 0.0000 | 0.0633 |
| 300-450 | 0.0904 | 0.0113 | 0.0113 | 0.0000 | 0.0791 |
| 450-650 | 0.0971 | 0.0306 | 0.0306 | 0.0000 | 0.0665 |
| 650-1000 | 0.0889 | 0.0279 | 0.0279 | 0.0000 | 0.0610 |
