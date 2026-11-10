"""Parametric models of post-sweep refill, compared out of sample.

Data: per post-sweep window w (20–1000 ms), the excess (sweep − matched placebo, fractions of
pre-sweep swept-side depth) near net build-up N(w) and deep net depletion J(w) (``model.py``).

Each model is a set of non-negative rate functions of time since the sweep, each a gamma
density times a mass, r(t) = m · Gamma(t; k, θ):

- W  withdrawal: deep depth leaves the book            (adds to J; W2 = a second, later one)
- T  transfer:   deep depth re-posted near the touch    (adds to J and N: mass-conserving;
                  T2 = a second, later one)
- S  source:     new depth posted near the touch        (adds to N)

so that  N(w) = ∫_w (r_T + r_S),   J(w) = ∫_w (r_W + r_T).

Shape k = 1 is an exponential decay starting at the sweep; k = 2 is a delayed hump peaking at
θ. Models are fitted by weighted least squares (weights: day-bootstrap standard errors of each
window's N and J) with many starting points, and compared by 5-fold cross-validation over days
(out-of-sample weighted error), AIC/BIC, and bootstrap stability of their parameters.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl
from scipy import optimize, stats

F64 = npt.NDArray[np.float64]

THETA_BOUNDS = (2.0, 5000.0)  # ms
K_BOUNDS = (1.0, 8.0)
M_MAX = 3.0
THETA_STARTS = (30.0, 100.0, 300.0, 1000.0)


@dataclass(frozen=True)
class Component:
    kind: str  # "W", "T" or "S"
    k: float | None  # fixed gamma shape, or None = free


@dataclass(frozen=True)
class Model:
    name: str
    label: str
    comps: tuple[Component, ...]

    @property
    def n_params(self) -> int:
        return sum(3 if c.k is None else 2 for c in self.comps)


MODELS: tuple[Model, ...] = (
    Model("A", "exponential recovery (near inflow only)", (Component("S", 1.0),)),
    Model("B", "replenish + cancel (two exponentials)", (Component("W", 1.0), Component("S", 1.0))),
    Model("C", "withdrawal + delayed source (no move)", (Component("W", 1.0), Component("S", 2.0))),
    Model("D", "withdrawal + move (no new liquidity)", (Component("W", 1.0), Component("T", 2.0))),
    Model(
        "E",
        "three-phase: withdrawal + move + delayed source",
        (Component("W", 1.0), Component("T", 2.0), Component("S", 2.0)),
    ),
    Model(
        "F",
        "three-phase, free shapes",
        (Component("W", None), Component("T", None), Component("S", None)),
    ),
    Model(
        "G",
        "three-phase + late withdrawal",
        (Component("W", 1.0), Component("W2", 2.0), Component("T", 2.0), Component("S", 2.0)),
    ),
    Model(
        "H",
        "early + late withdrawal + delayed source (no move)",
        (Component("W", 1.0), Component("W2", 2.0), Component("S", 2.0)),
    ),
    Model(
        "I",
        "three-phase + late move",
        (Component("W", 1.0), Component("T", 2.0), Component("T2", 2.0), Component("S", 2.0)),
    ),
)


def unpack(model: Model, x: F64) -> list[tuple[str, float, float, float]]:
    """Parameter vector -> [(kind, mass, k, theta)]."""
    out, i = [], 0
    for c in model.comps:
        m, th = float(x[i]), float(np.exp(x[i + 1]))
        i += 2
        if c.k is None:
            k = float(x[i])
            i += 1
        else:
            k = c.k
        out.append((c.kind, m, k, th))
    return out


def predict(model: Model, x: F64, edges: F64) -> tuple[F64, F64]:
    """Window integrals (N, J) for windows between consecutive ``edges`` (ms)."""
    n = np.zeros(len(edges) - 1)
    j = np.zeros(len(edges) - 1)
    for kind, m, k, th in unpack(model, x):
        mass = m * np.diff(stats.gamma.cdf(edges, k, scale=th))
        if kind in ("T", "T2", "S"):
            n += mass
        if kind in ("W", "W2", "T", "T2"):
            j += mass
    return n, j


def _starts(model: Model) -> list[F64]:
    starts = []
    for ths in itertools.product(THETA_STARTS, repeat=len(model.comps)):
        x: list[float] = []
        for c, th in zip(model.comps, ths, strict=True):
            x += [0.1, float(np.log(th))]
            if c.k is None:
                x.append(2.0)
        starts.append(np.array(x))
    return starts


def _bounds(model: Model) -> tuple[list[float], list[float]]:
    lo, hi = [], []
    for c in model.comps:
        lo += [0.0, float(np.log(THETA_BOUNDS[0]))]
        hi += [M_MAX, float(np.log(THETA_BOUNDS[1]))]
        if c.k is None:
            lo.append(K_BOUNDS[0])
            hi.append(K_BOUNDS[1])
    return lo, hi


def fit(
    model: Model,
    edges: F64,
    n_obs: F64,
    j_obs: F64,
    sig_n: F64,
    sig_j: F64,
    *,
    starts: Sequence[F64] | None = None,
) -> tuple[F64, float]:
    """Weighted least squares; returns (parameters, chi² = Σ residual²)."""
    obs = np.concatenate([n_obs, j_obs])
    sig = np.concatenate([sig_n, sig_j])

    def resid(x: F64) -> F64:
        n, j = predict(model, x, edges)
        return np.asarray((np.concatenate([n, j]) - obs) / sig, dtype=np.float64)

    lo, hi = _bounds(model)
    best: tuple[float, F64] | None = None
    for x0 in starts if starts is not None else _starts(model):
        x0 = np.clip(x0, lo, hi)
        r = optimize.least_squares(resid, x0, bounds=(lo, hi), method="trf", max_nfev=2000)
        chi2 = float((r.fun**2).sum())
        if best is None or chi2 < best[0]:
            best = (chi2, np.asarray(r.x, dtype=np.float64))
    assert best is not None
    return best[1], best[0]


# ---------------------------------------------------------------- data


def excess_curves(
    s_sums: pl.DataFrame, p_sums: pl.DataFrame, windows: Sequence[str], days: Sequence[str]
) -> tuple[F64, F64]:
    from lobflow.model import excess_masses

    n, j = excess_masses(s_sums, p_sums, windows, days)
    return np.asarray(n, dtype=np.float64), np.asarray(j, dtype=np.float64)


def boot_sigma(
    s_sums: pl.DataFrame,
    p_sums: pl.DataFrame,
    windows: Sequence[str],
    days: Sequence[str],
    *,
    n_boot: int = 200,
    seed: int = 0,
) -> tuple[F64, F64]:
    """Day-bootstrap standard errors of N(w) and J(w), floored at 5% of the median SE."""
    rng = np.random.default_rng(seed)
    draws = [
        excess_curves(s_sums, p_sums, windows, list(rng.choice(days, size=len(days))))
        for _ in range(n_boot)
    ]
    sn = np.array([d[0] for d in draws]).std(axis=0)
    sj = np.array([d[1] for d in draws]).std(axis=0)
    floor = 0.05 * float(np.median(np.concatenate([sn, sj])))
    return np.maximum(sn, floor), np.maximum(sj, floor)


# ---------------------------------------------------------------- comparison


def describe(model: Model, x: F64) -> dict[str, float]:
    """Interpretable quantities: per component mass, peak time and mean time (ms)."""
    out: dict[str, float] = {}
    for kind, m, k, th in unpack(model, x):
        out[f"{kind}_mass"] = m
        out[f"{kind}_peak_ms"] = (k - 1) * th
        out[f"{kind}_mean_ms"] = k * th
        out[f"{kind}_k"] = k
    return out


def compare(
    s_sums: pl.DataFrame,
    p_sums: pl.DataFrame,
    windows: Sequence[str],
    *,
    models: Sequence[Model] = MODELS,
    n_folds: int = 5,
    n_boot_sigma: int = 200,
    n_boot_params: int = 100,
    seed: int = 0,
) -> tuple[pl.DataFrame, pl.DataFrame, dict[str, tuple[F64, F64, F64, F64]]]:
    """Returns (scores per model, parameter table with bootstrap CIs, curves for plotting:
    model -> (edges, N_fit, J_fit, unused)); observed curves under key ``"obs"``."""
    from lobflow.model import window_edges

    days = sorted(set(s_sums["day"].to_list()))
    edges = window_edges(windows)
    n_obs, j_obs = excess_curves(s_sums, p_sums, windows, days)
    sig_n, sig_j = boot_sigma(s_sums, p_sums, windows, days, n_boot=n_boot_sigma, seed=seed)
    n_pts = 2 * len(windows)
    ss0 = float(((np.concatenate([n_obs, j_obs])) ** 2).sum())

    rng = np.random.default_rng(seed)
    folds = np.array_split(rng.permutation(len(days)), n_folds)
    rows, prow = [], []
    curves: dict[str, tuple[F64, F64, F64, F64]] = {
        "obs": (edges, n_obs, j_obs, np.concatenate([sig_n, sig_j]))
    }
    for model in models:
        x, chi2 = fit(model, edges, n_obs, j_obs, sig_n, sig_j)
        n_fit, j_fit = predict(model, x, edges)
        curves[model.name] = (edges, n_fit, j_fit, x)
        sse = float(((np.concatenate([n_fit - n_obs, j_fit - j_obs])) ** 2).sum())
        # cross-validation over days
        cv_chi2, cv_sse, cv_ss0 = 0.0, 0.0, 0.0
        for test_idx in folds:
            test = [days[i] for i in test_idx]
            train = [d for d in days if d not in set(test)]
            tn, tj = excess_curves(s_sums, p_sums, windows, train)
            xt, _ = fit(model, edges, tn, tj, sig_n, sig_j, starts=[x, *_starts(model)[::7]])
            pn, pj = predict(model, xt, edges)
            on, oj = excess_curves(s_sums, p_sums, windows, test)
            res = np.concatenate([pn - on, pj - oj])
            cv_chi2 += float(((res / np.concatenate([sig_n, sig_j])) ** 2).sum())
            cv_sse += float((res**2).sum())
            cv_ss0 += float((np.concatenate([on, oj]) ** 2).sum())
        p = model.n_params
        rows.append(
            {
                "model": model.name,
                "label": model.label,
                "n_params": p,
                "chi2": chi2,
                "aic": chi2 + 2 * p,
                "bic": chi2 + p * np.log(n_pts),
                "r2_in": 1 - sse / ss0,
                "cv_chi2": cv_chi2,
                "cv_r2": 1 - cv_sse / cv_ss0,
            }
        )
        # parameter stability: refit on day-bootstrap samples
        point = describe(model, x)
        draws = []
        for _ in range(n_boot_params):
            bd = list(rng.choice(days, size=len(days)))
            bn, bj = excess_curves(s_sums, p_sums, windows, bd)
            xb, _ = fit(model, edges, bn, bj, sig_n, sig_j, starts=[x])
            draws.append(describe(model, xb))
        for key, v in point.items():
            d = np.array([dr[key] for dr in draws])
            prow.append(
                {
                    "model": model.name,
                    "param": key,
                    "value": v,
                    "lo": float(np.percentile(d, 2.5)),
                    "hi": float(np.percentile(d, 97.5)),
                }
            )
    return pl.DataFrame(rows), pl.DataFrame(prow), curves


def run_fitmodels(
    out_dir: Path,
    results_dir: Path,
    *,
    tag: str = "flowsfine",
    max_push_ms: float = 20.0,
    n_boot_params: int = 100,
) -> str:
    """Model comparison for one symbol (deep book d > 5); writes ``fitmodels.md`` + parquet."""
    from lobflow.model import DEEP, load_flow_sums

    sums, post = load_flow_sums(
        out_dir, tag=tag, max_push_ms=max_push_ms, variants={"deep_d_gt_5": DEEP}
    )
    s_sums, p_sums = sums["deep_d_gt_5"]
    scores, params, curves = compare(s_sums, p_sums, post, n_boot_params=n_boot_params)
    results_dir.mkdir(parents=True, exist_ok=True)
    scores.write_parquet(results_dir / "fitmodels_scores.parquet")
    params.write_parquet(results_dir / "fitmodels_params.parquet")
    edges, n_obs, j_obs, _ = curves["obs"]
    fits = [
        {"model": m, "t_lo": float(a), "t_hi": float(b), "N": float(n), "J": float(j)}
        for m, (e, nn, jj, _x) in curves.items()
        for a, b, n, j in zip(e[:-1], e[1:], nn, jj, strict=True)
    ]
    pl.DataFrame(fits).write_parquet(results_dir / "fitmodels_curves.parquet")

    best = scores.sort("cv_chi2")["model"][0]
    lines = [
        "# Parametric refill models: out-of-sample comparison",
        "",
        "Data: excess near build-up N(w) and deep depletion J(w) per window, 20–1000 ms "
        f"({len(post)} windows × 2 series), deep book d > 5, state-matched placebo. Rates are "
        "gamma pulses (k = 1: exponential from the sweep; k = 2: delayed hump). Weighted least "
        "squares with day-bootstrap standard errors; CV: 5 folds over days. Lower cv_chi2 / "
        "AIC / BIC is better; cv_r2 is out-of-sample R² relative to predicting zero.",
        "",
        "| model | description | params | χ² | AIC | BIC | in-sample R² | CV χ² | CV R² |",
        "|---|---|---|---|---|---|---|---|---|",
        *[
            f"| {r['model']} | {r['label']} | {r['n_params']} | {r['chi2']:.1f} | "
            f"{r['aic']:.1f} | {r['bic']:.1f} | {r['r2_in']:.3f} | {r['cv_chi2']:.1f} | "
            f"{r['cv_r2']:.3f} |"
            for r in scores.iter_rows(named=True)
        ],
        "",
        f"Best by cross-validated χ²: **{best}**.",
        "",
        "## Parameters (95% day-bootstrap intervals)",
        "",
        "| model | parameter | value | 95% CI |",
        "|---|---|---|---|",
        *[
            f"| {r['model']} | {r['param']} | {r['value']:.3g} | [{r['lo']:.3g}, {r['hi']:.3g}] |"
            for r in params.iter_rows(named=True)
            if not r["param"].endswith("_k") or r["model"] == "F"
        ],
    ]
    text = "\n".join(lines) + "\n"
    (results_dir / "fitmodels.md").write_text(text)
    return text
