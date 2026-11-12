# Local vs non-local continuum models: out-of-sample fit

Days: 12; 5-fold cross-validation by day. One-step prediction of the change in the swept-side profile ρ(d), d = 1..50, between post-sweep times. R² relative to 'no change'. Parameters per step: common 2, local +3 (D, drift ±), non-local +1 (κ) plus global shapes.

| model | R² (pooled) | fold range |
|---|---|---|
| common | -0.069 | [-1.641, 0.051] |
| local | -0.010 | [-1.827, 0.127] |
| nonlocal | 0.029 | [-0.388, 0.067] |
| both | 0.067 | [-0.895, 0.146] |

| step (ms) | common | local | nonlocal | both |
|---|---|---|---|---|
| 20→40 | -0.079 | -0.079 | -0.519 | -0.564 |
| 40→60 | -0.016 | 0.094 | 0.030 | 0.104 |
| 60→100 | 0.213 | 0.204 | -0.001 | -0.043 |
| 100→250 | 0.092 | 0.066 | 0.090 | 0.054 |
| 250→500 | -0.260 | -0.265 | 0.029 | 0.027 |
| 500→1000 | 0.148 | 0.102 | 0.238 | 0.218 |

## Full-sample coefficients, model `both` (per step)

| step (ms) | ν | s | D | drift + | drift − | κ | ℓ | λ | m |
|---|---|---|---|---|---|---|---|---|---|
| 20→40 | 0.000 | 0.009 | 0.000 | 0.004 | 0.000 | 0.024 | 3 | 2 | 21 |
| 40→60 | 0.000 | 0.373 | 0.355 | 0.887 | 0.000 | 0.167 | 1 | 8 | 21 |
| 60→100 | 0.000 | 0.061 | 0.000 | 0.017 | 0.000 | 0.044 | 1 | 1 | 6 |
| 100→250 | 0.023 | 0.127 | 0.000 | 0.051 | 0.000 | 0.000 | 1 | 1 | 6 |
| 250→500 | 0.012 | 0.018 | 0.005 | 0.026 | 0.000 | 0.775 | 1 | 8 | 21 |
| 500→1000 | 0.000 | 0.000 | 0.000 | 0.011 | 0.000 | 0.135 | 1 | 1 | 6 |
