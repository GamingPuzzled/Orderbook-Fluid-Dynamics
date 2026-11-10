"""Two-phase refill model: non-local transport (repositioning) + delayed source.

Reduced-form mass balance on the swept side in the moving frame, using gross flows on a fine
window grid and the state-matched placebo as baseline ("excess" = sweep − matched placebo, as
fractions of pre-shock swept-side depth, ratio of sums):

    near build-up   N(w) = excess (add − cancel) at d ≤ 5            in window w
    deep depletion  J(w) = excess (cancel − add) at deep zones (default d > 5)

split per window into three non-negative components

    transport   T(w) = max(min(N, J), 0)    deep depth matched by near build-up (repositioning)
    withdrawal  W(w) = max(J − T, 0)        unmatched deep depletion (liquidity leaves the book)
    source      S(w) = max(N − T, 0)        near build-up beyond deep depletion (new liquidity)

Transport conserves swept-side depth; withdrawal removes it; the source adds it. Each
component's rate is a gamma-shaped pulse in time since the sweep,

    r_X(t) = M_X · Gamma(t; k_X, θ_X),

fitted to its window masses by least squares (descriptive smooth curves only: pulses are
poorly identified outside 20–1000 ms). Headline statistics are nonparametric over the
observed windows (``observed_summary``). CIs: day-cluster bootstrap.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl
from scipy import optimize, stats

F64 = npt.NDArray[np.float64]

NEAR = ("1-5",)
DEEP = ("6-10", "11-20", "21-50", "51+")


@dataclass(frozen=True)
class Pulse:
    mass: float
    shape: float
    scale_ms: float

    def cdf(self, t_ms: F64) -> F64:
        out: F64 = self.mass * stats.gamma.cdf(t_ms, self.shape, scale=self.scale_ms)
        return out

    def rate(self, t_ms: F64) -> F64:
        out: F64 = self.mass * stats.gamma.pdf(t_ms, self.shape, scale=self.scale_ms)
        return out

    @property
    def mode_ms(self) -> float:
        return max(self.shape - 1.0, 0.0) * self.scale_ms

    @property
    def mean_ms(self) -> float:
        return self.shape * self.scale_ms


def window_edges(labels: Sequence[str]) -> F64:
    """Sorted edges (ms) from window labels like ``"20-40"``."""
    pairs = sorted({tuple(int(x) for x in lab.split("-")) for lab in labels})
    return np.array([pairs[0][0], *(b for _, b in pairs)], dtype=np.float64)


def day_window_sums(
    flows: pl.DataFrame,
    info: pl.DataFrame,
    w: pl.DataFrame | None,
    deep_zones: Sequence[str] = DEEP,
) -> pl.DataFrame:
    """Per day × window: near net build-up and deep net depletion (sums), and pre depth.

    ``w`` (event_id, w) reweights events (placebo matching); None = unit weights.
    """
    ok = info.filter(pl.col("valid"))
    if w is not None:
        ok = ok.join(w, on="event_id", how="inner")
    else:
        ok = ok.with_columns(pl.lit(1.0).alias("w"))
    f = (
        flows.filter(pl.col("side") == "swept", pl.col("metric").is_in(["add", "cancel"]))
        .join(ok.select("event_id", "w"), on="event_id", how="inner")
        .with_columns(
            (
                pl.col("value")
                * pl.col("w")
                * pl.when(pl.col("metric") == "add").then(1).otherwise(-1)
            ).alias("net_add")
        )
    )
    near = (
        f.filter(pl.col("zone").is_in(list(NEAR)))
        .group_by("day", "window")
        .agg(pl.col("net_add").sum().alias("near"))
    )
    deep = (
        f.filter(pl.col("zone").is_in(list(deep_zones)))
        .group_by("day", "window")
        .agg((-pl.col("net_add")).sum().alias("deep"))
    )
    depth = ok.group_by("day").agg((pl.col("depth_pre_swept") * pl.col("w")).sum().alias("D"))
    return (
        near.join(deep, on=["day", "window"], how="full", coalesce=True)
        .fill_null(0.0)
        .join(depth, on="day")
    )


def excess_masses(
    s_sums: pl.DataFrame, p_sums: pl.DataFrame, windows: Sequence[str], days: Sequence[str]
) -> tuple[F64, F64]:
    """(N, J) per window: excess near build-up and deep depletion, pooled over ``days``
    (repeats allowed, for the bootstrap)."""
    counts = pl.DataFrame({"day": list(days)}).group_by("day").len()

    def pooled(df: pl.DataFrame) -> tuple[F64, F64]:
        d = df.join(counts, on="day")
        tot_d = float(
            d.select("day", "D", "len").unique().select(pl.col("D") * pl.col("len")).sum().item()
        )
        agg = d.group_by("window").agg(
            (pl.col("near") * pl.col("len")).sum(), (pl.col("deep") * pl.col("len")).sum()
        )
        m = {r["window"]: (r["near"], r["deep"]) for r in agg.iter_rows(named=True)}
        near = np.array([m.get(wl, (0.0, 0.0))[0] for wl in windows]) / tot_d
        deep = np.array([m.get(wl, (0.0, 0.0))[1] for wl in windows]) / tot_d
        return near, deep

    sn, sd = pooled(s_sums)
    pn, pd_ = pooled(p_sums)
    return sn - pn, sd - pd_


def fit_pulse(edges: F64, masses: F64, *, t_max: float = 5000.0) -> Pulse:
    """Least-squares gamma pulse matching window masses (window i = [edges[i], edges[i+1]))."""

    def resid(theta: F64) -> F64:
        p = Pulse(float(theta[0]), float(theta[1]), float(theta[2]))
        c = p.cdf(edges)
        return np.diff(c) - masses

    total = max(float(masses.sum()), 1e-6)
    best: optimize.OptimizeResult | None = None
    for k0 in (1.5, 3.0, 6.0):
        for s0 in (10.0, 50.0, 200.0):
            r = optimize.least_squares(
                resid,
                x0=np.array([total, k0, s0]),
                bounds=([0.0, 1.0, 1.0], [10 * total + 1.0, 50.0, t_max]),
            )
            if best is None or r.cost < best.cost:
                best = r
    assert best is not None
    return Pulse(float(best.x[0]), float(best.x[1]), float(best.x[2]))


def split_components(n: F64, j: F64) -> tuple[F64, F64, F64]:
    """(transport, withdrawal, source) per window from near build-up and deep depletion."""
    t = np.clip(np.minimum(n, j), 0.0, None)
    return t, np.clip(j - t, 0.0, None), np.clip(n - t, 0.0, None)


def observed_summary(
    edges: F64, t: F64, w: F64, s: F64, *, split_ms: float = 250.0
) -> dict[str, float]:
    """Nonparametric summaries over the observed windows only (no extrapolation).

    Masses per component overall and before/after ``split_ms``; mass-weighted mean time
    (window midpoints); switch time = start of the first window from which the source exceeds
    transport in every later window; transport share of near build-up before ``split_ms``.
    """
    mid = 0.5 * (edges[:-1] + edges[1:])
    early = edges[1:] <= split_ms

    def centroid(x: F64) -> float:
        return float((x * mid).sum() / x.sum()) if x.sum() > 0 else float("nan")

    dom = s > t
    t_switch = float("nan")
    for i in range(dom.size):
        if dom[i:].all():
            t_switch = float(edges[i])
            break
    te, se = float(t[early].sum()), float(s[early].sum())
    return {
        "transport": float(t.sum()),
        "withdrawal": float(w.sum()),
        "source": float(s.sum()),
        f"transport_<{int(split_ms)}ms": te,
        f"withdrawal_<{int(split_ms)}ms": float(w[early].sum()),
        f"source_<{int(split_ms)}ms": se,
        f"source_>{int(split_ms)}ms": float(s[~early].sum()),
        "transport_centroid_ms": centroid(t),
        "withdrawal_centroid_ms": centroid(w),
        "source_centroid_ms": centroid(s),
        "t_switch_ms": t_switch,
        f"transport_share_<{int(split_ms)}ms": te / (te + se) if te + se > 0 else float("nan"),
    }


def summarize(
    transport: Pulse, source: Pulse, withdrawal: Pulse, *, early_ms: float = 250.0
) -> dict[str, float]:
    t = np.linspace(1.0, 3000.0, 6000)
    rj, rs = transport.rate(t), source.rate(t)
    after = rs > rj
    # switch: first time after which source rate stays above transport rate
    idx = np.nonzero(~after)[0]
    t_switch = float(t[idx[-1] + 1]) if idx.size and idx[-1] + 1 < t.size else float("nan")
    if not idx.size:
        t_switch = float(t[0])
    ej = float(transport.cdf(np.array([early_ms]))[0])
    es = float(source.cdf(np.array([early_ms]))[0])
    return {
        "M_transport": transport.mass,
        "M_withdrawal": withdrawal.mass,
        "M_source": source.mass,
        "withdrawal_mean_ms": withdrawal.mean_ms,
        "transport_peak_ms": transport.mode_ms,
        "transport_mean_ms": transport.mean_ms,
        "source_peak_ms": source.mode_ms,
        "source_mean_ms": source.mean_ms,
        "t_switch_ms": t_switch,
        f"transport_share_{int(early_ms)}ms": ej / (ej + es) if ej + es > 0 else float("nan"),
    }


def fit_two_phase(
    s_sums: pl.DataFrame,
    p_sums: pl.DataFrame,
    windows: Sequence[str],
    *,
    n_boot: int = 200,
    seed: int = 0,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Returns (per-window excess masses with fitted values, summary with bootstrap CIs)."""
    edges = window_edges(windows)
    days = s_sums["day"].unique().sort().to_list()

    def one(ds: Sequence[str]) -> tuple[dict[str, float], F64, F64]:
        n, j = excess_masses(s_sums, p_sums, windows, ds)
        return observed_summary(edges, *split_components(n, j)), n, j

    point, n, j = one(days)
    t_m, w_m, s_m = split_components(n, j)
    pt, pw, ps = (fit_pulse(edges, x) for x in (t_m, w_m, s_m))
    rng = np.random.default_rng(seed)
    boots = [one(rng.choice(days, size=len(days)).tolist())[0] for _ in range(n_boot)]
    rows = []
    for k, v in point.items():
        b = np.array([x[k] for x in boots], dtype=float)
        rows.append(
            {
                "stat": k,
                "value": v,
                "lo": float(np.nanpercentile(b, 2.5)),
                "hi": float(np.nanpercentile(b, 97.5)),
            }
        )
    per_window = pl.DataFrame(
        {
            "window": list(windows),
            "t_lo": edges[:-1],
            "t_hi": edges[1:],
            "near_build": n,
            "deep_depletion": j,
            "transport": t_m,
            "withdrawal": w_m,
            "source": s_m,
            "fit_transport": np.diff(pt.cdf(edges)),
            "fit_withdrawal": np.diff(pw.cdf(edges)),
            "fit_source": np.diff(ps.cdf(edges)),
        }
    )
    return per_window, pl.DataFrame(rows)


@dataclass(frozen=True)
class FlowFrames:
    """Per-event post-sweep flows for the main sample (ids made unique per day)."""

    s_flows: pl.DataFrame
    s_info: pl.DataFrame
    p_flows: pl.DataFrame
    p_info: pl.DataFrame
    w: pl.DataFrame  # placebo weights (event_id, w)
    windows: list[str]  # all window labels, sorted
    post: list[str]  # windows after the sweep-absorption window
    days: list[str]


def load_flow_frames(
    out_dir: Path, *, tag: str = "flowsfine", max_push_ms: float = 20.0
) -> FlowFrames:
    """Sweeps with ≥ 95% of the gap cleared, their flows, and CEM-weighted placebo flows."""
    from lobflow.analysis import load_outputs, placebo_weights

    data = load_outputs(out_dir, max_push_ms=max_push_ms)
    days_ok = data["meta"].filter(pl.col("ok"))["day"].sort().to_list()

    def load(kind: str) -> pl.DataFrame:
        parts = [
            pl.read_parquet(out_dir / f"{d}_{kind}.parquet").with_columns(
                (pl.col("event_id") + k * 1_000_000).alias("event_id"), pl.lit(d).alias("day")
            )
            for k, d in enumerate(days_ok)
        ]
        return pl.concat(parts, how="diagonal_relaxed")

    keep = data["events"].filter(pl.col("cleared_frac") >= 0.95)["event_id"]
    s_flows, s_info = load(tag), load(f"{tag}_info")
    s_info = s_info.filter(pl.col("event_id").is_in(keep.implode()))
    p_flows, p_info = load(f"{tag}_placebo"), load(f"{tag}_placebo_info")
    w, _ = placebo_weights(data["state"], data["flows_info"], data["flows_placebo_info"])
    edges = window_edges(s_flows["window"].unique().to_list())
    windows = [f"{int(a)}-{int(b)}" for a, b in zip(edges[:-1], edges[1:], strict=True)]
    post = [x for x in windows if not x.startswith("0-")]  # drop sweep-absorption window
    return FlowFrames(s_flows, s_info, p_flows, p_info, w, windows, post, days_ok)


def load_flow_sums(
    out_dir: Path,
    *,
    tag: str = "flowsfine",
    max_push_ms: float = 20.0,
    variants: dict[str, Sequence[str]] | None = None,
) -> tuple[dict[str, tuple[pl.DataFrame, pl.DataFrame]], list[str]]:
    """Per deep-zone variant: (sweep day×window sums, matched-placebo sums), and the post-sweep
    window labels (0–20 ms excluded). Placebo weights: within-day CEM (``placebo_weights``)."""
    fr = load_flow_frames(out_dir, tag=tag, max_push_ms=max_push_ms)
    variants = variants or {"deep_d_gt_5": DEEP, "deep_d_6_50": ("6-10", "11-20", "21-50")}
    out = {
        name: (
            day_window_sums(fr.s_flows, fr.s_info, None, zones),
            day_window_sums(fr.p_flows, fr.p_info, fr.w, zones),
        )
        for name, zones in variants.items()
    }
    return out, fr.post


def run_model(
    out_dir: Path,
    results_dir: Path,
    *,
    tag: str = "flowsfine",
    n_boot: int = 200,
    max_push_ms: float = 20.0,
) -> str:
    """Fit the two-phase model for one symbol; write ``model.md`` and parquet tables."""
    sums, post = load_flow_sums(out_dir, tag=tag, max_push_ms=max_push_ms)
    variants = {"deep_d_gt_5": DEEP, "deep_d_6_50": ("6-10", "11-20", "21-50")}
    results_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Two-phase refill model (transport + withdrawal + delayed source)",
        "",
        "Excess vs state-matched placebo, fractions of pre-shock swept-side depth. Per window: "
        "transport = deep depletion matched by near (d ≤ 5) build-up; withdrawal = unmatched "
        "deep depletion; source = near build-up beyond deep depletion. Nonparametric over "
        "observed windows 20–1000 ms (0–20 ms sweep absorption excluded); 95% day-cluster "
        "bootstrap CIs. Centroid = mass-weighted mean time; switch = start of first window from "
        "which source > transport in all later windows.",
    ]
    for name, zones in variants.items():
        s_sums, p_sums = sums[name]
        per_window, summary = fit_two_phase(s_sums, p_sums, post, n_boot=n_boot)
        per_window.write_parquet(results_dir / f"model_windows_{name}.parquet")
        summary.write_parquet(results_dir / f"model_summary_{name}.parquet")
        lines += [
            "",
            f"## Deep zones: {', '.join(zones)}",
            "",
            "| stat | value | 95% CI |",
            "|---|---|---|",
            *[
                f"| {r['stat']} | {r['value']:.3f} | [{r['lo']:.3f}, {r['hi']:.3f}] |"
                for r in summary.iter_rows(named=True)
            ],
            "",
            "| window (ms) | near build | deep depletion | transport | withdrawal | source |",
            "|---|---|---|---|---|---|",
            *[
                f"| {r['window']} | {r['near_build']:.4f} | {r['deep_depletion']:.4f} | "
                f"{r['transport']:.4f} | {r['withdrawal']:.4f} | {r['source']:.4f} |"
                for r in per_window.iter_rows(named=True)
            ],
        ]
    text = "\n".join(lines) + "\n"
    (results_dir / "model.md").write_text(text)
    return text
