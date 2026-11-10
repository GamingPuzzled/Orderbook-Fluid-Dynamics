# Local vs non-local continuum models: out-of-sample fit

Days: 43; 5-fold cross-validation by day. One-step prediction of the change in the swept-side profile ρ(d), d = 1..50, between post-sweep times. R² relative to 'no change'. Parameters per step: common 2, local +3 (D, drift ±), non-local +1 (κ) plus global shapes.

| model | R² (pooled) | fold range |
|---|---|---|
| common | 0.389 | [0.341, 0.477] |
| local | 0.388 | [0.338, 0.477] |
| nonlocal | 0.410 | [0.328, 0.479] |
| both | 0.408 | [0.322, 0.481] |

| step (ms) | common | local | nonlocal | both |
|---|---|---|---|---|
| 20→40 | 0.573 | 0.566 | 0.573 | 0.566 |
| 40→60 | 0.362 | 0.350 | 0.427 | 0.412 |
| 60→100 | 0.121 | 0.120 | 0.214 | 0.212 |
| 100→250 | 0.025 | 0.052 | 0.025 | 0.052 |
| 250→500 | 0.057 | 0.061 | 0.057 | 0.061 |
| 500→1000 | -0.002 | 0.036 | -0.002 | 0.036 |

## Full-sample coefficients, model `both` (per step)

| step (ms) | ν | s | D | drift + | drift − | κ | ℓ | λ | m |
|---|---|---|---|---|---|---|---|---|---|
| 20→40 | 0.000 | 0.122 | 0.031 | 0.111 | 0.000 | 0.000 | 1 | 1 | 6 |
| 40→60 | 0.000 | 0.000 | 0.000 | 0.030 | 0.000 | 0.073 | 1 | 1 | 6 |
| 60→100 | 0.013 | 0.000 | 0.000 | 0.039 | 0.000 | 0.046 | 1 | 1 | 6 |
| 100→250 | 0.000 | 0.027 | 0.006 | 0.078 | 0.000 | 0.000 | 1 | 1 | 6 |
| 250→500 | 0.000 | 0.017 | 0.000 | 0.029 | 0.000 | 0.000 | 1 | 1 | 6 |
| 500→1000 | 0.000 | 0.018 | 0.027 | 0.069 | 0.000 | 0.000 | 1 | 1 | 6 |
