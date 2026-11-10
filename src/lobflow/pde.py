"""Out-of-sample comparison of local vs non-local continuum models of post-sweep refill.

State: swept-side depth profile ρ_k(d), d = 1..D_MAX ticks from the opposite best quote, at
post-sweep times τ_k (pooled per day, as a fraction of pre-sweep depth over d ≤ D_MAX). Each
model predicts the one-step change Δρ_k = ρ_{k+1} − ρ_k from ρ_k, with step-specific
non-negative rates (NNLS) and global shape parameters chosen on the training days:

- common  : −ν_k ρ(d) + s_k φ_ℓ(d)                     (cancellation, near-touch source)
- local   : common + D_k Δ²ρ(d) + a_k ∇ρ(d)             (diffusion + drift; the drift also
            absorbs the mechanical shift of the moving frame)
- nonlocal: common + κ_k [φ_λ(d) Σ_{y≥m} ρ(y) − 1[d≥m] ρ(d)]   (mass-conserving jump from the
            deep book to the touch)
- both    : common + local + nonlocal terms

φ_ℓ(d) ∝ exp(−(d−1)/ℓ), normalised to sum 1. Out-of-sample R² = 1 − SSE / Σ(Δρ)² on held-out
days (k-fold by day), i.e. relative to predicting no change.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl
from scipy.optimize import nnls

F64 = npt.NDArray[np.float64]

D_MAX = 50
TAUS_MS: tuple[int, ...] = (20, 40, 60, 100, 250, 500, 1000)
ELLS: tuple[float, ...] = (1.0, 2.0, 3.0, 5.0, 8.0)
M_DEEP: tuple[int, ...] = (6, 11, 21)
MODELS: tuple[str, ...] = ("common", "local", "nonlocal", "both")


def day_profiles(moving: pl.DataFrame, taus: Sequence[int] = TAUS_MS) -> dict[str, F64]:
    """Per day: array (len(taus), D_MAX) of Σ depth(d, τ) / Σ pre-sweep depth (d ≤ D_MAX)."""
    mv = moving.filter(pl.col("d") <= D_MAX)
    pre = mv.filter(pl.col("tau_ms") == -1).group_by("day").agg(pl.col("depth").sum().alias("P"))
    prof = (
        mv.filter(pl.col("tau_ms").is_in(list(taus)))
        .group_by("day", "tau_ms", "d")
        .agg(pl.col("depth").sum())
        .join(pre, on="day")
        .with_columns(pl.col("depth") / pl.col("P"))
    )
    out: dict[str, F64] = {}
    for (day,), g in prof.group_by("day"):
        arr = np.zeros((len(taus), D_MAX))
        ti = {t: i for i, t in enumerate(taus)}
        for t, d, v in g.select("tau_ms", "d", "depth").iter_rows():
            arr[ti[t], d - 1] = v
        out[str(day)] = arr
    return out


def phi(ell: float) -> F64:
    x = np.exp(-np.arange(D_MAX, dtype=np.float64) / ell)
    return np.asarray(x / x.sum(), dtype=np.float64)


def _lap(r: F64) -> F64:
    p = np.concatenate([r[:1], r, r[-1:]])  # reflecting ends
    return np.asarray(p[2:] - 2.0 * p[1:-1] + p[:-2], dtype=np.float64)


def _grad(r: F64) -> F64:
    p = np.concatenate([r[:1], r, r[-1:]])
    return np.asarray(0.5 * (p[2:] - p[:-2]), dtype=np.float64)


def features(model: str, r: F64, ell: float, lam: float, m: int) -> F64:
    """Columns (D_MAX × p) for one profile; all coefficients constrained ≥ 0 (drift split
    into ± columns)."""
    cols = [-r, phi(ell)]
    if model in ("local", "both"):
        g = _grad(r)
        cols += [_lap(r), g, -g]
    if model in ("nonlocal", "both"):
        deep = np.arange(1, D_MAX + 1) >= m
        cols.append(phi(lam) * r[deep].sum() - deep * r)
    return np.column_stack(cols)


def _stack(
    profs: Sequence[F64], k: int, model: str, ell: float, lam: float, m: int
) -> tuple[F64, F64]:
    x = np.vstack([features(model, p[k], ell, lam, m) for p in profs])
    y = np.concatenate([p[k + 1] - p[k] for p in profs])
    return x, y


def fit_step(profs: Sequence[F64], k: int, model: str) -> tuple[F64, tuple[float, float, int]]:
    """NNLS coefficients and best global shapes (ℓ, λ, m) for step k on ``profs``."""
    best: tuple[float, F64, tuple[float, float, int]] | None = None
    lams = ELLS if model in ("nonlocal", "both") else (1.0,)
    ms = M_DEEP if model in ("nonlocal", "both") else (6,)
    for ell in ELLS:
        for lam in lams:
            for m in ms:
                x, y = _stack(profs, k, model, ell, lam, m)
                coef, rnorm = nnls(x, y)
                if best is None or rnorm < best[0]:
                    best = (rnorm, coef, (ell, lam, m))
    assert best is not None
    return best[1], best[2]


def cross_validate(
    profiles: dict[str, F64], *, n_folds: int = 5, seed: int = 0
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Returns (out-of-sample R² per model × step × fold, full-sample coefficients)."""
    days = sorted(profiles)
    rng = np.random.default_rng(seed)
    folds = np.array_split(rng.permutation(len(days)), n_folds)
    n_steps = next(iter(profiles.values())).shape[0] - 1
    rows = []
    for f, test_idx in enumerate(folds):
        test = [profiles[days[i]] for i in test_idx]
        train = [profiles[days[i]] for i in range(len(days)) if i not in set(test_idx)]
        for model in MODELS:
            for k in range(n_steps):
                coef, (ell, lam, m) = fit_step(train, k, model)
                x, y = _stack(test, k, model, ell, lam, m)
                sse = float(((y - x @ coef) ** 2).sum())
                rows.append(
                    {"fold": f, "model": model, "step": k, "sse": sse, "ss0": float((y**2).sum())}
                )
    oos = pl.DataFrame(rows)
    coefs = []
    allp = [profiles[d] for d in days]
    for model in MODELS:
        for k in range(n_steps):
            coef, (ell, lam, m) = fit_step(allp, k, model)
            names = ["nu", "s"]
            if model in ("local", "both"):
                names += ["D", "a_pos", "a_neg"]
            if model in ("nonlocal", "both"):
                names += ["kappa"]
            coefs.append(
                {"model": model, "step": k, "ell": ell, "lam": lam, "m": m}
                | dict(zip(names, coef.tolist(), strict=True))
            )
    return oos, pl.DataFrame(coefs, infer_schema_length=None)


def _r2(df: pl.DataFrame, keys: Sequence[str]) -> pl.DataFrame:
    return df.group_by(keys).agg((1 - pl.col("sse").sum() / pl.col("ss0").sum()).alias("r2"))


def run_pde(
    out_dir: Path, results_dir: Path, *, max_push_ms: float = 20.0, n_folds: int = 5
) -> str:
    """Model comparison for one symbol; writes ``pde.md`` and parquet tables."""
    from lobflow.analysis import load_outputs

    data = load_outputs(out_dir, max_push_ms=max_push_ms)
    keep = data["events"].filter(pl.col("cleared_frac") >= 0.95)["event_id"]
    mv = data["moving"].filter(pl.col("event_id").is_in(keep.implode()))
    profiles = day_profiles(mv)
    oos, coefs = cross_validate(profiles, n_folds=n_folds)
    results_dir.mkdir(parents=True, exist_ok=True)
    oos.write_parquet(results_dir / "pde_oos.parquet")
    coefs.write_parquet(results_dir / "pde_coefs.parquet")
    steps = [f"{a}→{b}" for a, b in zip(TAUS_MS[:-1], TAUS_MS[1:], strict=True)]
    tot = _r2(oos, ["model"])
    by_fold = (
        _r2(oos, ["model", "fold"])
        .group_by("model")
        .agg(pl.col("r2").min().alias("lo"), pl.col("r2").max().alias("hi"))
    )
    by_step = _r2(oos, ["model", "step"])

    def get(df: pl.DataFrame, model: str, col: str = "r2", **kw: int) -> float:
        q = df.filter(pl.col("model") == model)
        for k, v in kw.items():
            q = q.filter(pl.col(k) == v)
        return float(q[col][0])

    fmt: Callable[[float], str] = lambda v: f"{v:.3f}"  # noqa: E731
    lines = [
        "# Local vs non-local continuum models: out-of-sample fit",
        "",
        f"Days: {len(profiles)}; {n_folds}-fold cross-validation by day. One-step prediction of "
        "the change in the swept-side profile ρ(d), d = 1..50, between post-sweep times. "
        "R² relative to 'no change'. Parameters per step: common 2, local +3 (D, drift ±), "
        "non-local +1 (κ) plus global shapes.",
        "",
        "| model | R² (pooled) | fold range |",
        "|---|---|---|",
        *[
            f"| {m} | {fmt(get(tot, m))} | [{fmt(get(by_fold, m, 'lo'))}, "
            f"{fmt(get(by_fold, m, 'hi'))}] |"
            for m in MODELS
        ],
        "",
        "| step (ms) | " + " | ".join(MODELS) + " |",
        "|---|" + "---|" * len(MODELS),
        *[
            f"| {s} | " + " | ".join(fmt(get(by_step, m, step=k)) for m in MODELS) + " |"
            for k, s in enumerate(steps)
        ],
        "",
        "## Full-sample coefficients, model `both` (per step)",
        "",
        "| step (ms) | ν | s | D | drift + | drift − | κ | ℓ | λ | m |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in coefs.filter(pl.col("model") == "both").sort("step").iter_rows(named=True):
        lines.append(
            f"| {steps[r['step']]} | {r['nu']:.3f} | {r['s']:.3f} | {r['D']:.3f} | "
            f"{r['a_pos']:.3f} | {r['a_neg']:.3f} | {r['kappa']:.3f} | {r['ell']:g} | "
            f"{r['lam']:g} | {r['m']} |"
        )
    text = "\n".join(lines) + "\n"
    (results_dir / "pde.md").write_text(text)
    return text
