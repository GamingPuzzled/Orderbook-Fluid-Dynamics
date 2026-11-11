# Local vs non-local continuum models: out-of-sample fit

Days: 33; 5-fold cross-validation by day. One-step prediction of the change in the swept-side profile ρ(d), d = 1..50, between post-sweep times. R² relative to 'no change'. Parameters per step: common 2, local +3 (D, drift ±), non-local +1 (κ) plus global shapes.

| model | R² (pooled) | fold range |
|---|---|---|
| common | 0.051 | [-0.060, 0.133] |
| local | 0.194 | [0.153, 0.213] |
| nonlocal | 0.051 | [-0.064, 0.135] |
| both | 0.194 | [0.151, 0.212] |

| step (ms) | common | local | nonlocal | both |
|---|---|---|---|---|
| 20→40 | 0.107 | 0.348 | 0.105 | 0.347 |
| 40→60 | 0.011 | 0.062 | 0.011 | 0.062 |
| 60→100 | 0.006 | 0.086 | 0.006 | 0.086 |
| 100→250 | 0.017 | 0.069 | 0.017 | 0.069 |
| 250→500 | 0.009 | 0.090 | 0.015 | 0.090 |
| 500→1000 | -0.002 | 0.083 | -0.001 | 0.083 |

## Full-sample coefficients, model `both` (per step)

| step (ms) | ν | s | D | drift + | drift − | κ | ℓ | λ | m |
|---|---|---|---|---|---|---|---|---|---|
| 20→40 | 0.092 | 0.005 | 0.290 | 0.000 | 0.125 | 0.015 | 8 | 8 | 21 |
| 40→60 | 0.010 | 0.003 | 0.127 | 0.000 | 0.007 | 0.000 | 8 | 1 | 6 |
| 60→100 | 0.001 | 0.003 | 0.120 | 0.000 | 0.070 | 0.000 | 8 | 1 | 6 |
| 100→250 | 0.000 | 0.022 | 0.088 | 0.007 | 0.000 | 0.000 | 8 | 1 | 6 |
| 250→500 | 0.000 | 0.014 | 0.118 | 0.013 | 0.000 | 0.000 | 8 | 1 | 6 |
| 500→1000 | 0.000 | 0.007 | 0.107 | 0.000 | 0.045 | 0.000 | 8 | 1 | 6 |
