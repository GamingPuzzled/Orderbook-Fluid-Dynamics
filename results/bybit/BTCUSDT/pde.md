# Local vs non-local continuum models: out-of-sample fit

Days: 42; 5-fold cross-validation by day. One-step prediction of the change in the swept-side profile ρ(d), d = 1..50, between post-sweep times. R² relative to 'no change'. Parameters per step: common 2, local +3 (D, drift ±), non-local +1 (κ) plus global shapes.

| model | R² (pooled) | fold range |
|---|---|---|
| common | 0.653 | [0.614, 0.717] |
| local | 0.643 | [0.559, 0.725] |
| nonlocal | 0.652 | [0.610, 0.721] |
| both | 0.640 | [0.566, 0.728] |

| step (ms) | common | local | nonlocal | both |
|---|---|---|---|---|
| 20→40 | 0.743 | 0.720 | 0.743 | 0.720 |
| 40→60 | 0.582 | 0.609 | 0.578 | 0.591 |
| 60→100 | 0.385 | 0.426 | 0.375 | 0.416 |
| 100→250 | 0.296 | 0.289 | 0.296 | 0.289 |
| 250→500 | 0.431 | 0.438 | 0.431 | 0.438 |
| 500→1000 | 0.317 | 0.320 | 0.317 | 0.320 |

## Full-sample coefficients, model `both` (per step)

| step (ms) | ν | s | D | drift + | drift − | κ | ℓ | λ | m |
|---|---|---|---|---|---|---|---|---|---|
| 20→40 | 0.000 | 0.314 | 0.000 | 0.005 | 0.000 | 0.000 | 1 | 1 | 6 |
| 40→60 | 0.000 | 0.108 | 0.000 | 0.126 | 0.000 | 0.094 | 1 | 1 | 6 |
| 60→100 | 0.000 | 0.071 | 0.000 | 0.067 | 0.000 | 0.008 | 1 | 1 | 6 |
| 100→250 | 0.000 | 0.071 | 0.000 | 0.031 | 0.000 | 0.000 | 1 | 1 | 6 |
| 250→500 | 0.000 | 0.074 | 0.000 | 0.034 | 0.000 | 0.000 | 1 | 1 | 6 |
| 500→1000 | 0.000 | 0.058 | 0.000 | 0.021 | 0.000 | 0.000 | 1 | 1 | 6 |
