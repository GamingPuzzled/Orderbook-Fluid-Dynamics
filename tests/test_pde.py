import numpy as np
import pytest

from lobflow.pde import D_MAX, _lap, features, fit_step, phi


def test_lap_conserves_mass() -> None:
    r = np.random.default_rng(0).random(D_MAX)
    assert _lap(r).sum() == pytest.approx(0.0, abs=1e-12)


def test_nonlocal_jump_conserves_mass() -> None:
    r = np.random.default_rng(1).random(D_MAX)
    col = features("nonlocal", r, 2.0, 1.0, 11)[:, -1]
    assert col.sum() == pytest.approx(0.0, abs=1e-12)


def test_fit_recovers_diffusion() -> None:
    rng = np.random.default_rng(2)
    profs = []
    for _ in range(6):
        r0 = rng.random(D_MAX) + phi(3.0)
        r1 = r0 + 0.2 * _lap(r0)
        profs.append(np.vstack([r0, r1]))
    coef, _ = fit_step(profs, 0, "local")
    assert coef[2] == pytest.approx(0.2, rel=1e-6)  # D
