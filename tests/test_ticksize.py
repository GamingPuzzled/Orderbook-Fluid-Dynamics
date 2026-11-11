import numpy as np
import polars as pl

from lobflow.ticksize import fit, wls


def test_wls_recovers_slope() -> None:
    rng = np.random.default_rng(0)
    x = np.column_stack([rng.normal(size=500), np.ones(500)])
    y = 2.0 * x[:, 0] + 1.0 + rng.normal(scale=0.1, size=500)
    beta, se = wls(x, y, np.ones(500))
    assert abs(beta[0] - 2.0) < 0.02
    assert 0 < se[0] < 0.01


def test_fit_uses_within_asset_variation() -> None:
    """Asset levels differ wildly, but the within-asset slope on log10 tick is -0.05."""
    rng = np.random.default_rng(1)
    rows = []
    for asset, level in (("A", 1.0), ("B", -3.0)):
        for _ in range(60):
            t = 10 ** rng.uniform(-2, 0)
            rows.append(
                {
                    "asset": asset,
                    "tick_bp": t,
                    "n_sweeps": 50,
                    "depth_quote": 1e6,
                    "y": level - 0.05 * np.log10(t) + rng.normal(scale=0.005),
                }
            )
    f = fit(pl.DataFrame(rows), "y", n_boot=50)
    assert abs(f.beta + 0.05) < 0.005
    assert f.lo < -0.05 < f.hi
