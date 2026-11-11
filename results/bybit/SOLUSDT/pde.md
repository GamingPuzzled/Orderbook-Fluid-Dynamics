# Local vs non-local continuum models: out-of-sample fit

Days: 39; 5-fold cross-validation by day. One-step prediction of the change in the swept-side profile ρ(d), d = 1..50, between post-sweep times. R² relative to 'no change'. Parameters per step: common 2, local +3 (D, drift ±), non-local +1 (κ) plus global shapes.

| model | R² (pooled) | fold range |
|---|---|---|
| common | 0.031 | [-0.025, 0.055] |
| local | 0.258 | [0.172, 0.285] |
| nonlocal | 0.030 | [-0.024, 0.055] |
| both | 0.258 | [0.172, 0.285] |

| step (ms) | common | local | nonlocal | both |
|---|---|---|---|---|
| 20→40 | 0.045 | 0.243 | 0.044 | 0.243 |
| 40→60 | 0.057 | 0.337 | 0.055 | 0.337 |
| 60→100 | 0.036 | 0.313 | 0.036 | 0.313 |
| 100→250 | 0.010 | 0.335 | 0.009 | 0.335 |
| 250→500 | 0.005 | 0.216 | 0.007 | 0.216 |
| 500→1000 | 0.002 | -0.055 | 0.001 | -0.055 |

## Full-sample coefficients, model `both` (per step)

| step (ms) | ν | s | D | drift + | drift − | κ | ℓ | λ | m |
|---|---|---|---|---|---|---|---|---|---|
| 20→40 | 0.055 | 0.010 | 0.258 | 0.000 | 0.113 | 0.000 | 8 | 1 | 6 |
| 40→60 | 0.042 | 0.005 | 0.237 | 0.059 | 0.000 | 0.000 | 8 | 1 | 6 |
| 60→100 | 0.029 | 0.000 | 0.314 | 0.000 | 0.255 | 0.007 | 1 | 8 | 21 |
| 100→250 | 0.000 | 0.028 | 0.314 | 0.000 | 0.168 | 0.000 | 8 | 1 | 6 |
| 250→500 | 0.000 | 0.012 | 0.202 | 0.117 | 0.000 | 0.000 | 8 | 1 | 6 |
| 500→1000 | 0.000 | 0.009 | 0.103 | 0.019 | 0.000 | 0.000 | 8 | 1 | 6 |
