# Local vs non-local continuum models: out-of-sample fit

Days: 12; 5-fold cross-validation by day. One-step prediction of the change in the swept-side profile ρ(d), d = 1..50, between post-sweep times. R² relative to 'no change'. Parameters per step: common 2, local +3 (D, drift ±), non-local +1 (κ) plus global shapes.

| model | R² (pooled) | fold range |
|---|---|---|
| common | 0.467 | [0.267, 0.674] |
| local | 0.494 | [0.287, 0.711] |
| nonlocal | 0.467 | [0.267, 0.672] |
| both | 0.493 | [0.287, 0.708] |

| step (ms) | common | local | nonlocal | both |
|---|---|---|---|---|
| 20→40 | 0.694 | 0.742 | 0.693 | 0.742 |
| 40→60 | -0.038 | -0.014 | -0.043 | -0.029 |
| 60→100 | 0.215 | 0.204 | 0.215 | 0.204 |
| 100→250 | 0.173 | 0.178 | 0.173 | 0.178 |
| 250→500 | 0.464 | 0.468 | 0.462 | 0.465 |
| 500→1000 | 0.270 | 0.233 | 0.249 | 0.218 |

## Full-sample coefficients, model `both` (per step)

| step (ms) | ν | s | D | drift + | drift − | κ | ℓ | λ | m |
|---|---|---|---|---|---|---|---|---|---|
| 20→40 | 0.000 | 0.333 | 0.000 | 0.497 | 0.000 | 0.000 | 1 | 1 | 6 |
| 40→60 | 0.000 | 0.012 | 0.000 | 0.035 | 0.000 | 0.012 | 1 | 1 | 6 |
| 60→100 | 0.000 | 0.037 | 0.000 | 0.001 | 0.000 | 0.000 | 1 | 1 | 6 |
| 100→250 | 0.000 | 0.138 | 0.000 | 0.100 | 0.000 | 0.000 | 1 | 1 | 6 |
| 250→500 | 0.000 | 0.072 | 0.000 | 0.032 | 0.000 | 0.006 | 1 | 1 | 6 |
| 500→1000 | 0.000 | 0.022 | 0.000 | 0.000 | 0.004 | 0.023 | 1 | 1 | 6 |
