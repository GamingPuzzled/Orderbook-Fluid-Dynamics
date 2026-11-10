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
θ.

Benchmarks from the order-flow literature:

- Linear Hawkes, exponential kernels (``H`` modes): the expected response of add/cancel
  intensities to an exogenous shock is a sum of decaying exponentials, one per eigenmode of the
  kernel matrix, with loadings of either sign. Each ``H`` mode has its own time scale and
  signed loadings on N and J (a difference of two modes can produce a delayed hump).
- Power-law kernels (``PN``/``PJ``): rate m · β/c · (1 + t/c)^-(1+β) for N and for J
  separately, the slow decay typical of fitted Hawkes kernels in order books.
- Queue-reactive (Huang, Lehalle & Rosenbaum 2015): flows depend on the current queue sizes
  only, not on time since the sweep; see ``queuereactive.py``.

Models are fitted by weighted least squares (weights: day-bootstrap standard errors of each
window's N and J) with many starting points, and compared by 5-fold cross-validation over days
(out-of-sample weighted error), AIC/BIC, and bootstrap stability of their parameters.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import numpy.typing as npt
import polars as pl
from scipy import optimize, stats

F64 = npt.NDArray[np.float64]

THETA_BOUNDS = (2.0, 5000.0)  # ms
K_BOUNDS = (1.0, 8.0)
M_MAX = 3.0
THETA_STARTS = (30.0, 100.0, 300.0, 1000.0)
BETA_BOUNDS = (0.05, 5.0)
GAMMA_KINDS = ("W", "W2", "T", "T2", "S")
N_KINDS = ("T", "T2", "S")
J_KINDS = ("W", "W2", "T", "T2")


@dataclass(frozen=True)
class Component:
    """One rate term. Gamma kinds (W, W2, T, T2, S): mass ≥ 0, scale θ, shape k (fixed or
    free, ``k=None``). ``H1``/``H2``: Hawkes exponential mode, signed loadings on N and J and a
    shared θ (``k`` unused). ``PN``/``PJ``: power-law (Lomax) rate, signed mass, scale c and
    tail exponent β, on N or J only (``k`` unused)."""

    kind: str
    k: float | None = 1.0

    @property
    def n_params(self) -> int:
        if self.kind in GAMMA_KINDS:
            return 3 if self.k is None else 2
        return 3


@dataclass(frozen=True)
class Model:
    name: str
    label: str
    comps: tuple[Component, ...]

    @property
    def n_params(self) -> int:
        return sum(c.n_params for c in self.comps)


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
    Model("K", "linear Hawkes, exponential kernels (2 modes)", (Component("H1"), Component("H2"))),
    Model(
        "K3",
        "linear Hawkes, exponential kernels (3 modes)",
        (Component("H1"), Component("H2"), Component("H3")),
    ),
    Model("P", "Hawkes-type power-law decay", (Component("PN"), Component("PJ"))),
)


def unpack(model: Model, x: F64) -> list[tuple[str, tuple[float, ...]]]:
    """Parameter vector -> [(kind, natural parameters)]: gamma (m, k, θ); H (a_N, a_J, θ);
    P (m, c, β)."""
    out: list[tuple[str, tuple[float, ...]]] = []
    i = 0
    for c in model.comps:
        if c.kind in GAMMA_KINDS:
            m, th = float(x[i]), float(np.exp(x[i + 1]))
            i += 2
            if c.k is None:
                k = float(x[i])
                i += 1
            else:
                k = c.k
            out.append((c.kind, (m, k, th)))
        elif c.kind.startswith("H"):
            out.append((c.kind, (float(x[i]), float(x[i + 1]), float(np.exp(x[i + 2])))))
            i += 3
        else:
            out.append((c.kind, (float(x[i]), float(np.exp(x[i + 1])), float(x[i + 2]))))
            i += 3
    return out


def _lomax_cdf(t: F64, c: float, beta: float) -> F64:
    return np.asarray(1.0 - (1.0 + np.maximum(t, 0.0) / c) ** (-beta), dtype=np.float64)


def predict(model: Model, x: F64, edges: F64) -> tuple[F64, F64]:
    """Window integrals (N, J) for windows between consecutive ``edges`` (ms)."""
    n = np.zeros(len(edges) - 1)
    j = np.zeros(len(edges) - 1)
    for kind, par in unpack(model, x):
        if kind in GAMMA_KINDS:
            m, k, th = par
            mass = m * np.diff(stats.gamma.cdf(edges, k, scale=th))
            if kind in N_KINDS:
                n += mass
            if kind in J_KINDS:
                j += mass
        elif kind.startswith("H"):
            a_n, a_j, th = par
            shape = np.diff(stats.expon.cdf(edges, scale=th))
            n += a_n * shape
            j += a_j * shape
        else:
            m, c_, beta = par
            mass = m * np.diff(_lomax_cdf(edges, c_, beta))
            if kind == "PN":
                n += mass
            else:
                j += mass
    return n, j


_H_LOADINGS = ((0.1, 0.1), (0.2, -0.1), (-0.1, 0.2), (-0.1, -0.1))


def _starts(model: Model) -> list[F64]:
    per_comp: list[list[list[float]]] = []
    for c in model.comps:
        opts: list[list[float]] = []
        for th in THETA_STARTS:
            lt = float(np.log(th))
            if c.kind in GAMMA_KINDS:
                opts.append([0.1, lt] + ([2.0] if c.k is None else []))
            elif c.kind.startswith("H"):
                opts += [[a, b, lt] for a, b in _H_LOADINGS]
            else:
                opts += [[0.1, lt, beta] for beta in (0.5, 1.5)]
        per_comp.append(opts)
    combos = list(itertools.product(*per_comp))
    if len(combos) > 400:  # thin large grids deterministically
        combos = combos[:: len(combos) // 400 + 1]
    return [np.array([v for part in combo for v in part]) for combo in combos]


def _bounds(model: Model) -> tuple[list[float], list[float]]:
    lo, hi = [], []
    lt = (float(np.log(THETA_BOUNDS[0])), float(np.log(THETA_BOUNDS[1])))
    for c in model.comps:
        if c.kind in GAMMA_KINDS:
            lo += [0.0, lt[0]]
            hi += [M_MAX, lt[1]]
            if c.k is None:
                lo.append(K_BOUNDS[0])
                hi.append(K_BOUNDS[1])
        elif c.kind.startswith("H"):
            lo += [-M_MAX, -M_MAX, lt[0]]
            hi += [M_MAX, M_MAX, lt[1]]
        else:
            lo += [-M_MAX, lt[0], BETA_BOUNDS[0]]
            hi += [M_MAX, lt[1], BETA_BOUNDS[1]]
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


class Benchmark(Protocol):
    """A non-parametric competitor: predicts the excess (N, J) pooled over ``test_days``
    after calibrating on ``train_days`` (e.g. ``queuereactive.QueueReactive``)."""

    label: str
    n_params: int

    def __call__(self, train_days: Sequence[str], test_days: Sequence[str]) -> tuple[F64, F64]: ...


def describe(model: Model, x: F64) -> dict[str, float]:
    """Interpretable quantities per component: gamma (mass, peak, mean, k); Hawkes mode
    (loadings on N and J, time scale); power law (mass, scale c, exponent β)."""
    out: dict[str, float] = {}
    comps = unpack(model, x)
    # Hawkes modes are exchangeable: name them by increasing time scale (no label switching)
    modes = sorted((par for kind, par in comps if kind.startswith("H")), key=lambda p: p[2])
    comps = [c for c in comps if not c[0].startswith("H")]
    comps += [(f"H{i + 1}", par) for i, par in enumerate(modes)]
    for kind, par in comps:
        if kind in GAMMA_KINDS:
            m, k, th = par
            out[f"{kind}_mass"] = m
            out[f"{kind}_peak_ms"] = (k - 1) * th
            out[f"{kind}_mean_ms"] = k * th
            out[f"{kind}_k"] = k
        elif kind.startswith("H"):
            out[f"{kind}_aN"], out[f"{kind}_aJ"], out[f"{kind}_tau_ms"] = par
        else:
            out[f"{kind}_mass"], out[f"{kind}_c_ms"], out[f"{kind}_beta"] = par
    return out


def compare(
    s_sums: pl.DataFrame,
    p_sums: pl.DataFrame,
    windows: Sequence[str],
    *,
    models: Sequence[Model] = MODELS,
    benchmarks: dict[str, Benchmark] | None = None,
    n_folds: int = 5,
    n_boot_sigma: int = 200,
    n_boot_params: int = 100,
    seed: int = 0,
) -> tuple[pl.DataFrame, pl.DataFrame, dict[str, tuple[F64, F64, F64, F64]]]:
    """Returns (scores per model, parameter table with bootstrap CIs, curves for plotting:
    model -> (edges, N_fit, J_fit, unused)); observed curves under key ``"obs"``.
    ``benchmarks`` are scored on the same folds and weights (no AIC/BIC: not parametric)."""
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
    sig = np.concatenate([sig_n, sig_j])
    for name, bench in (benchmarks or {}).items():
        n_fit, j_fit = bench(days, days)
        curves[name] = (edges, n_fit, j_fit, np.zeros(0))
        res_in = np.concatenate([n_fit - n_obs, j_fit - j_obs])
        cv_chi2, cv_sse, cv_ss0 = 0.0, 0.0, 0.0
        for test_idx in folds:
            test = [days[i] for i in test_idx]
            train = [d for d in days if d not in set(test)]
            pn, pj = bench(train, test)
            on, oj = excess_curves(s_sums, p_sums, windows, test)
            res = np.concatenate([pn - on, pj - oj])
            cv_chi2 += float(((res / sig) ** 2).sum())
            cv_sse += float((res**2).sum())
            cv_ss0 += float((np.concatenate([on, oj]) ** 2).sum())
        chi2 = float(((res_in / sig) ** 2).sum())
        rows.append(
            {
                "model": name,
                "label": bench.label,
                "n_params": bench.n_params,
                "chi2": chi2,
                "aic": float("nan"),
                "bic": float("nan"),
                "r2_in": 1 - float((res_in**2).sum()) / ss0,
                "cv_chi2": cv_chi2,
                "cv_r2": 1 - cv_sse / cv_ss0,
            }
        )
    return pl.DataFrame(rows), pl.DataFrame(prow), curves


def _fmt(v: float) -> str:
    return "–" if np.isnan(v) else f"{v:.1f}"


def run_fitmodels(
    out_dir: Path,
    results_dir: Path,
    *,
    tag: str = "flowsfine",
    max_push_ms: float = 20.0,
    n_boot_params: int = 100,
) -> str:
    """Model comparison for one symbol (deep book d > 5); writes ``fitmodels.md`` + parquet."""
    from lobflow.model import DEEP, day_window_sums, load_flow_frames
    from lobflow.queuereactive import benchmarks as qr_benchmarks

    fr = load_flow_frames(out_dir, tag=tag, max_push_ms=max_push_ms)
    post = fr.post
    s_sums = day_window_sums(fr.s_flows, fr.s_info, None, DEEP)
    p_sums = day_window_sums(fr.p_flows, fr.p_info, fr.w, DEEP)
    q, q_plus = qr_benchmarks(out_dir, fr, p_sums)
    scores, params, curves = compare(
        s_sums, p_sums, post, benchmarks={"Q": q, "Q+": q_plus}, n_boot_params=n_boot_params
    )
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
        "AIC / BIC is better; cv_r2 is out-of-sample R² relative to predicting zero. K, K3, P: "
        "Hawkes-type impulse responses. Q, Q+: queue-reactive benchmarks given the observed book "
        "state at each window start (params = binned intensity values; no AIC/BIC).",
        "",
        "| model | description | params | χ² | AIC | BIC | in-sample R² | CV χ² | CV R² |",
        "|---|---|---|---|---|---|---|---|---|",
        *[
            f"| {r['model']} | {r['label']} | {r['n_params']} | {r['chi2']:.1f} | "
            f"{_fmt(r['aic'])} | {_fmt(r['bic'])} | {r['r2_in']:.3f} | {r['cv_chi2']:.1f} | "
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
