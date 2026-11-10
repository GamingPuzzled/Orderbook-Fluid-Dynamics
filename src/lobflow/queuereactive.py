"""Queue-reactive benchmark for post-sweep refill (Huang, Lehalle & Rosenbaum 2015).

In a queue-reactive model the order-flow intensities at a level depend only on the current
queue sizes, not on how the book got there. Applied to sweeps, it asks: is the post-sweep
refill just the normal response of liquidity providers to a thin book, or does time since the
sweep matter beyond the book's state?

Implementation (zone-level, matching the observables in ``fitmodels``):

- State at the start of each post-sweep window: near depth (d = 1–5 ticks from the opposite
  best quote, moving frame) and deep depth (d = 6–50), linearly interpolated between the
  profile grid (τ = 20, 40, 60, 100, 250, 500, 1000 ms) and scaled by that day's median
  placebo pre-shock depth in the same zone (dimensionless queue sizes, as in HLR).
- Outcome: near net additions and deep net cancellations per ms, in the same units.
- Intensity function: weighted mean rate in each cell of a 2-D grid of (near, deep) queue
  sizes, falling back to a 1-D grid of the zone's own queue size, then to the overall mean,
  when a cell has fewer than ``min_obs`` observations.
- Prediction: each sweep window's expected flows given its *observed* state at the window
  start. This is a one-step-ahead forecast that sees the realised book, so it is generous to
  the benchmark relative to the time-only parametric models.

Two calibrations: on placebo windows only (normal-time state dependence, ``Q``), and on placebo
plus sweep windows of the training days (state-only regression, ``Q+``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl

from lobflow.model import DEEP, NEAR, FlowFrames, excess_masses, window_edges

F64 = npt.NDArray[np.float64]

QUEUE_BINS: tuple[float, ...] = (0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0, 3.0)
NEAR_MAX_D = 5
DEEP_MAX_D = 50


def _profiles(out_dir: Path, days: Sequence[str], kind: str) -> pl.DataFrame:
    """Near and deep depth per (event, τ) from ``moving`` (sweeps) or ``placebo`` profiles,
    with ids renumbered as in ``analysis.load_outputs``."""
    parts = []
    for k, day in enumerate(days):
        df = pl.read_parquet(
            out_dir / f"{day}_{kind}.parquet", columns=["event_id", "tau_ms", "d", "depth"]
        )
        parts.append(
            df.filter(pl.col("d") <= DEEP_MAX_D)
            .group_by("event_id", "tau_ms")
            .agg(
                pl.col("depth").filter(pl.col("d") <= NEAR_MAX_D).sum().alias("near"),
                pl.col("depth").filter(pl.col("d") > NEAR_MAX_D).sum().alias("deep"),
            )
            .with_columns(
                (pl.col("event_id") + k * 1_000_000).alias("event_id"), pl.lit(day).alias("day")
            )
        )
    return pl.concat(parts)


def _state_at(profiles: pl.DataFrame, starts: Sequence[float]) -> pl.DataFrame:
    """Linear interpolation of (near, deep) at each window start τ (post-sweep grid only)."""
    grid = profiles.filter(pl.col("tau_ms") >= 0).sort("event_id", "tau_ms")
    taus = np.array(sorted(grid["tau_ms"].unique().to_list()), dtype=np.float64)
    ids = grid["event_id"].unique().sort()
    full = (
        pl.DataFrame({"event_id": ids})
        .join(pl.DataFrame({"tau_ms": taus.astype(np.int64)}), how="cross")
        .join(grid, on=["event_id", "tau_ms"], how="left")
        .sort("event_id", "tau_ms")
    )
    n_ev, n_t = len(ids), len(taus)
    near = full["near"].to_numpy().reshape(n_ev, n_t)
    deep = full["deep"].to_numpy().reshape(n_ev, n_t)
    out = []
    for t in starts:
        i = int(np.clip(np.searchsorted(taus, t, side="right") - 1, 0, n_t - 2))
        a = float(np.clip((t - taus[i]) / (taus[i + 1] - taus[i]), 0.0, 1.0))
        out.append(
            pl.DataFrame(
                {
                    "event_id": ids,
                    "t_start": np.full(n_ev, t),
                    "near_q": (1 - a) * near[:, i] + a * near[:, i + 1],
                    "deep_q": (1 - a) * deep[:, i] + a * deep[:, i + 1],
                }
            )
        )
    return (
        pl.concat(out)
        .drop_nulls()
        .filter(pl.col("near_q").is_not_nan(), pl.col("deep_q").is_not_nan())
    )


def _net_flows(flows: pl.DataFrame, windows: Sequence[str]) -> pl.DataFrame:
    """Per (event, window): near net additions and deep net cancellations on the swept side."""
    f = flows.filter(
        pl.col("side") == "swept",
        pl.col("metric").is_in(["add", "cancel"]),
        pl.col("window").is_in(list(windows)),
    ).with_columns(
        (pl.col("value") * pl.when(pl.col("metric") == "add").then(1.0).otherwise(-1.0)).alias(
            "net_add"
        )
    )
    return f.group_by("event_id", "window").agg(
        pl.col("net_add").filter(pl.col("zone").is_in(list(NEAR))).sum().alias("near_net"),
        (-pl.col("net_add").filter(pl.col("zone").is_in(list(DEEP)))).sum().alias("deep_net"),
    )


def _bin(q: F64) -> npt.NDArray[np.int64]:
    return np.searchsorted(np.array(QUEUE_BINS), q, side="right").astype(np.int64)


@dataclass
class Intensity:
    """Binned queue-reactive intensity: rates (per ms, scaled units) by queue-size cell."""

    min_obs: int = 30
    cell2: dict[tuple[int, int], tuple[float, float]] = field(default_factory=dict)
    near1: dict[int, float] = field(default_factory=dict)
    deep1: dict[int, float] = field(default_factory=dict)
    overall: tuple[float, float] = (0.0, 0.0)

    def fit(self, rows: pl.DataFrame) -> Intensity:
        """``rows``: qn, qd (scaled queue sizes), rn, rd (scaled rates), wt (weights)."""
        r = rows.with_columns(
            pl.Series("bn", _bin(rows["qn"].to_numpy())),
            pl.Series("bd", _bin(rows["qd"].to_numpy())),
        )

        def wmean(by: list[str]) -> pl.DataFrame:
            return (
                r.group_by(by)
                .agg(
                    (pl.col("rn") * pl.col("wt")).sum() / pl.col("wt").sum(),
                    (pl.col("rd") * pl.col("wt")).sum() / pl.col("wt").sum(),
                    pl.len().alias("n"),
                )
                .filter(pl.col("n") >= self.min_obs)
            )

        self.cell2 = {(a, b): (x, y) for a, b, x, y, _ in wmean(["bn", "bd"]).iter_rows()}
        self.near1 = {a: x for a, x, _, _ in wmean(["bn"]).iter_rows()}
        self.deep1 = {b: y for b, _, y, _ in wmean(["bd"]).iter_rows()}
        tot = float(r["wt"].sum())
        self.overall = (
            float((r["rn"] * r["wt"]).sum()) / tot,
            float((r["rd"] * r["wt"]).sum()) / tot,
        )
        return self

    def rates(self, qn: F64, qd: F64) -> tuple[F64, F64]:
        bn, bd = _bin(qn), _bin(qd)
        rn, rd = np.empty(len(qn)), np.empty(len(qn))
        for i, (a, b) in enumerate(zip(bn.tolist(), bd.tolist(), strict=True)):
            if (a, b) in self.cell2:
                rn[i], rd[i] = self.cell2[(a, b)]
            else:
                rn[i] = self.near1.get(a, self.overall[0])
                rd[i] = self.deep1.get(b, self.overall[1])
        return rn, rd

    @property
    def n_cells(self) -> int:
        return len(self.cell2)


@dataclass
class QueueReactive:
    """Queue-reactive benchmark, callable as ``(train_days, test_days) -> (N, J)`` predicted
    excess, pooled over ``test_days`` like ``model.excess_masses``."""

    label: str
    sweep_rows: pl.DataFrame  # per sweep × window: day, event_id, window, len, scales, state, flows
    placebo_rows: pl.DataFrame
    s_depth: pl.DataFrame  # per day: D (pre-shock swept depth of valid sweeps)
    p_sums: pl.DataFrame
    windows: list[str]
    include_sweeps: bool
    min_obs: int = 30
    n_params: int = 0

    def _train(self, days: Sequence[str]) -> Intensity:
        ds = sorted(set(days))
        parts = [self.placebo_rows.filter(pl.col("day").is_in(ds))]
        if self.include_sweeps:
            parts.append(self.sweep_rows.filter(pl.col("day").is_in(ds)))
        rows = pl.concat(parts).select("qn", "qd", "rn", "rd", "wt")
        it = Intensity(min_obs=self.min_obs).fit(rows)
        self.n_params = 2 * it.n_cells
        return it

    def predicted_sums(self, it: Intensity, days: Sequence[str]) -> pl.DataFrame:
        """Sweep day × window sums (near, deep, D) with flows replaced by predictions."""
        s = self.sweep_rows.filter(pl.col("day").is_in(sorted(set(days))))
        rn, rd = it.rates(s["qn"].to_numpy(), s["qd"].to_numpy())
        s = s.with_columns(
            (pl.Series(rn) * pl.col("scale_n") * pl.col("len")).alias("near"),
            (pl.Series(rd) * pl.col("scale_d") * pl.col("len")).alias("deep"),
        )
        sums = s.group_by("day", "window").agg(pl.col("near").sum(), pl.col("deep").sum())
        return sums.join(self.s_depth, on="day")

    def __call__(self, train_days: Sequence[str], test_days: Sequence[str]) -> tuple[F64, F64]:
        it = self._train(train_days)
        pred = self.predicted_sums(it, test_days)
        n, j = excess_masses(pred, self.p_sums, self.windows, test_days)
        return np.asarray(n, dtype=np.float64), np.asarray(j, dtype=np.float64)


def build_rows(out_dir: Path, fr: FlowFrames) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(sweep rows, placebo rows): one row per valid event × post-sweep window with scaled
    state (qn, qd), scaled rates (rn, rd), weight wt, and the scales to undo them."""
    edges = window_edges(fr.post)
    starts = [float(x) for x in edges[:-1]]
    win = pl.DataFrame(
        {
            "window": fr.post,
            "t_start": starts,
            "len": [float(b - a) for a, b in zip(edges[:-1], edges[1:], strict=True)],
        }
    )
    s_prof = _profiles(out_dir, fr.days, "moving")
    p_prof = _profiles(out_dir, fr.days, "placebo")
    p_valid = fr.p_info.filter(pl.col("valid")).select("event_id")
    scales = (
        p_prof.filter(pl.col("tau_ms") == -1)
        .join(p_valid, on="event_id")
        .group_by("day")
        .agg(pl.col("near").median().alias("scale_n"), pl.col("deep").median().alias("scale_d"))
        .with_columns(
            pl.col("scale_n").clip(lower_bound=1e-9), pl.col("scale_d").clip(lower_bound=1e-9)
        )
    )

    def rows(
        prof: pl.DataFrame, info: pl.DataFrame, flows: pl.DataFrame, w: pl.DataFrame | None
    ) -> pl.DataFrame:
        ok = info.filter(pl.col("valid")).select("event_id", "day")
        ok = ok.join(w, on="event_id") if w is not None else ok.with_columns(pl.lit(1.0).alias("w"))
        st = _state_at(prof.join(ok.select("event_id"), on="event_id"), starts)
        fl = _net_flows(flows, fr.post)
        return (
            ok.join(win, how="cross")
            .join(st, on=["event_id", "t_start"], how="inner")
            .join(fl, on=["event_id", "window"], how="left")
            .fill_null(0.0)
            .join(scales, on="day")
            .with_columns(
                (pl.col("near_q") / pl.col("scale_n")).alias("qn"),
                (pl.col("deep_q") / pl.col("scale_d")).alias("qd"),
                (pl.col("near_net") / (pl.col("scale_n") * pl.col("len"))).alias("rn"),
                (pl.col("deep_net") / (pl.col("scale_d") * pl.col("len"))).alias("rd"),
                pl.col("w").alias("wt"),
            )
        )

    return rows(s_prof, fr.s_info, fr.s_flows, None), rows(p_prof, fr.p_info, fr.p_flows, fr.w)


def benchmarks(out_dir: Path, fr: FlowFrames, p_sums: pl.DataFrame) -> list[QueueReactive]:
    """The two queue-reactive calibrations, ready for ``fitmodels.compare``."""
    s_rows, p_rows = build_rows(out_dir, fr)
    s_depth = (
        fr.s_info.filter(pl.col("valid"))
        .group_by("day")
        .agg(pl.col("depth_pre_swept").sum().alias("D"))
    )
    return [
        QueueReactive(label, s_rows, p_rows, s_depth, p_sums, fr.post, include_sweeps=inc)
        for label, inc in (
            ("queue-reactive, calibrated on placebo times", False),
            ("queue-reactive, calibrated on placebo + sweep windows", True),
        )
    ]
