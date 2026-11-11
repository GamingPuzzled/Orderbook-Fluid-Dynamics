# Local vs non-local continuum models: out-of-sample fit

Days: 34; 5-fold cross-validation by day. One-step prediction of the change in the swept-side profile ρ(d), d = 1..50, between post-sweep times. R² relative to 'no change'. Parameters per step: common 2, local +3 (D, drift ±), non-local +1 (κ) plus global shapes.

| model | R² (pooled) | fold range |
|---|---|---|
| common | 0.057 | [0.018, 0.078] |
| local | 0.222 | [0.143, 0.294] |
| nonlocal | 0.057 | [0.019, 0.078] |
| both | 0.222 | [0.143, 0.294] |

| step (ms) | common | local | nonlocal | both |
|---|---|---|---|---|
| 20→40 | 0.114 | 0.370 | 0.114 | 0.370 |
| 40→60 | 0.053 | 0.183 | 0.053 | 0.183 |
| 60→100 | 0.033 | 0.259 | 0.032 | 0.259 |
| 100→250 | 0.010 | 0.033 | 0.010 | 0.033 |
| 250→500 | 0.008 | 0.040 | 0.012 | 0.040 |
| 500→1000 | 0.000 | 0.026 | -0.000 | 0.025 |

## Full-sample coefficients, model `both` (per step)

| step (ms) | ν | s | D | drift + | drift − | κ | ℓ | λ | m |
|---|---|---|---|---|---|---|---|---|---|
| 20→40 | 0.084 | 0.012 | 0.286 | 0.000 | 0.106 | 0.000 | 8 | 3 | 11 |
| 40→60 | 0.042 | 0.013 | 0.170 | 0.000 | 0.114 | 0.000 | 8 | 2 | 11 |
| 60→100 | 0.012 | 0.011 | 0.225 | 0.000 | 0.326 | 0.000 | 8 | 1 | 6 |
| 100→250 | 0.000 | 0.020 | 0.080 | 0.000 | 0.022 | 0.000 | 8 | 1 | 6 |
| 250→500 | 0.000 | 0.012 | 0.075 | 0.002 | 0.000 | 0.000 | 8 | 1 | 6 |
| 500→1000 | 0.000 | 0.004 | 0.045 | 0.000 | 0.009 | 0.003 | 8 | 8 | 11 |
