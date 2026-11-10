"""Tests for the parametric refill-model comparison."""

from __future__ import annotations

import numpy as np

from lobflow.fitmodels import MODELS, describe, fit, predict

EDGES = np.array([20, 40, 60, 80, 100, 140, 200, 300, 450, 650, 1000], dtype=np.float64)
BY_NAME = {m.name: m for m in MODELS}


def _truth() -> tuple[np.ndarray, np.ndarray]:
    # withdrawal 0.2 (mean 60 ms), transfer 0.15 (peak 150 ms), source 0.25 (peak 450 ms)
    x = np.array([0.2, np.log(60.0), 0.15, np.log(150.0), 0.25, np.log(450.0)])
    return predict(BY_NAME["E"], x, EDGES)


def test_predict_masses_add_up() -> None:
    n, j = _truth()
    # windows cover 20–1000 ms only, so totals are below the full masses
    assert 0.0 < n.sum() < 0.15 + 0.25
    assert 0.0 < j.sum() < 0.2 + 0.15


def test_three_phase_recovered_and_preferred_on_synthetic_data() -> None:
    rng = np.random.default_rng(1)
    n, j = _truth()
    sig = np.full(n.size, 0.002)
    n_obs, j_obs = n + rng.normal(0, 0.002, n.size), j + rng.normal(0, 0.002, j.size)
    chi = {}
    for name in ("C", "D", "E"):
        x, c = fit(BY_NAME[name], EDGES, n_obs, j_obs, sig, sig)
        chi[name] = c
        if name == "E":
            d = describe(BY_NAME["E"], x)
    assert chi["E"] < chi["C"] and chi["E"] < chi["D"]
    assert abs(d["T_peak_ms"] - 150) < 40 and abs(d["S_peak_ms"] - 450) < 120
    assert abs(d["W_mass"] - 0.2) < 0.05


def test_hawkes_mode_recovers_exponential_response() -> None:
    # one exponential mode loading +0.3 on N and +0.2 on J with τ = 80 ms: K must fit it
    x_true = np.array([0.3, 0.2, np.log(80.0), 0.0, 0.0, np.log(500.0)])
    n, j = predict(BY_NAME["K"], x_true, EDGES)
    sig = np.full(n.size, 0.002)
    x, chi2 = fit(BY_NAME["K"], EDGES, n, j, sig, sig)
    assert chi2 < 1e-3
    d = describe(BY_NAME["K"], x)
    big = max(("H1", "H2"), key=lambda h: abs(d[f"{h}_aN"]))
    assert abs(d[f"{big}_tau_ms"] - 80) < 10


def test_power_law_mass_conserved() -> None:
    edges = np.array([0.0, 1e9])
    x = np.array([0.4, np.log(50.0), 1.0, -0.1, np.log(50.0), 1.0])
    n, j = predict(BY_NAME["P"], x, edges)
    assert abs(n[0] - 0.4) < 1e-6 and abs(j[0] + 0.1) < 1e-6
