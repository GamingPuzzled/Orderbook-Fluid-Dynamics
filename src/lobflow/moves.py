"""Order-level evidence for repositioning without order identifiers (exact-size matching).

If market makers *move* orders after a sweep (cancel deep, re-post near the new touch), a
near-touch addition (d ≤ 5) should often have exactly the size of a cancellation at a strictly
deeper price (d ≥ 6) on the same side, within a short lag in either order (cancel-then-post or
post-then-cancel). Crypto order sizes are fine-grained (e.g. 0.137 BTC), so exact matches are
informative once round sizes are excluded.

Per near addition (``toward``) we flag, among deep cancellations at a deeper price within
``lag_ms`` in the same event:

- ``exact``      one with identical size (any order); split into ``same`` message,
                 ``src_first`` (cancel earlier) and ``tgt_first`` (post earlier);
- ``ctrl``       one with size exactly one lot larger / smaller (mean of the two): the
                 coincidence rate for sizes this close, absent any link.

Controls: (i) ``ctrl`` (exact − ctrl = matches beyond coincidence); (ii) the ``away``
direction, near cancellations matched to deep additions (moves away from the touch);
(iii) state-matched placebo times. Only *rare* sizes are used: each day's most common sizes
(together half of all updates, e.g. round lots placed by many traders) are excluded.

Caveat: each L2 message nets changes per price over one push, so a delta equals an order's size
only when one order changed at that price; this lowers match rates for sweeps and placebo alike.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import polars as pl

NEAR_MAX_D = 5
DEEP_MIN_D = 6
TIME_BINS_MS: tuple[int, ...] = (20, 100, 250, 1000)
SIZE_SCALE = 1e8  # sizes compared after rounding to 1e-8
SHARES: tuple[str, ...] = ("exact", "same", "src_first", "tgt_first", "ctrl")

LogRow = tuple[int, int, int, int, float, int]


def log_frame(log: Sequence[LogRow]) -> pl.DataFrame:
    """Log tuples from :func:`lobflow.flows.flow_panel` → DataFrame with an integer size key."""
    df = pl.DataFrame(
        log,
        schema={
            "e": pl.Int64,
            "t": pl.Int64,
            "d": pl.Int64,
            "kind": pl.Int8,
            "size": pl.Float64,
            "dpx": pl.Int64,
        },
        orient="row",
    )
    return df.with_columns((pl.col("size") * SIZE_SCALE).round().cast(pl.Int64).alias("key"))


def common_sizes(logs: Sequence[pl.DataFrame], top_share: float = 0.5) -> set[int]:
    """Size keys that together cover the top ``top_share`` of all logged updates of a day
    (most frequent first)."""
    keys = pl.concat([lg.select("key") for lg in logs])
    if keys.height == 0:
        return set()
    vc = keys["key"].value_counts(sort=True)
    cum = vc["count"].cum_sum() / vc["count"].sum()
    return set(vc.filter(cum.shift(1, fill_value=0.0) < top_share)["key"].to_list())


def lot_size(logs: Sequence[pl.DataFrame]) -> int:
    """Smallest positive size key logged that day (the exchange lot, in key units)."""
    keys = pl.concat([lg.select("key") for lg in logs])["key"]
    pos = keys.filter(keys > 0)
    return int(pos.min()) if pos.len() else 1  # type: ignore[arg-type]


def _pairs(tg: pl.DataFrame, src: pl.DataFrame, lag_us: int, shift: int) -> pl.DataFrame:
    """Per target ``rid``: flags for a source at a strictly deeper price within ``lag_us``
    whose size key equals target key + ``shift``."""
    s = src.select(
        "e",
        (pl.col("key") - shift).alias("key"),
        pl.col("t").alias("ts"),
        pl.col("dpx").alias("sdpx"),
    )
    j = (
        tg.select("rid", "e", "key", "t", "dpx")
        .join(s, on=["e", "key"], how="inner")
        .filter(pl.col("sdpx") > pl.col("dpx"), (pl.col("t") - pl.col("ts")).abs() <= lag_us)
    )
    dt = pl.col("t") - pl.col("ts")
    return j.group_by("rid").agg(
        (dt == 0).any().alias("same"),
        (dt > 0).any().alias("src_first"),
        (dt < 0).any().alias("tgt_first"),
    )


def _match(tg: pl.DataFrame, src: pl.DataFrame, lag_us: int, lot: int) -> pl.DataFrame:
    tg = tg.with_row_index("rid")
    ex = _pairs(tg, src, lag_us, 0)
    up = _pairs(tg, src, lag_us, lot).select("rid", pl.lit(0.5).alias("c_up"))
    dn = _pairs(tg, src, lag_us, -lot).select("rid", pl.lit(0.5).alias("c_dn"))
    out = (
        tg.join(ex, on="rid", how="left")
        .join(up, on="rid", how="left")
        .join(dn, on="rid", how="left")
        .with_columns(
            pl.col("same", "src_first", "tgt_first").fill_null(False),
            (pl.col("c_up").fill_null(0.0) + pl.col("c_dn").fill_null(0.0)).alias("ctrl"),
        )
    )
    return out.with_columns(
        (pl.col("same") | pl.col("src_first") | pl.col("tgt_first")).alias("exact")
    ).drop("rid", "c_up", "c_dn")


def move_stats(
    log: pl.DataFrame,
    common: set[int],
    lot: int,
    *,
    lag_ms: int = 100,
    bins_ms: Sequence[int] = TIME_BINS_MS,
) -> pl.DataFrame:
    """Per event × time bin × direction: rare-size target volume ``v`` and matched volumes
    ``v_<share>`` for ``SHARES``.

    direction ``toward``: near additions matched to cancellations at deeper prices
    (repositioning); ``away``: near cancellations matched to additions at deeper prices.
    """
    lag_us = lag_ms * 1000
    lo, hi = bins_ms[0] * 1000, bins_ms[-1] * 1000
    rare = log.filter(~pl.col("key").is_in(list(common)))
    near, deep = pl.col("d") <= NEAR_MAX_D, pl.col("d") >= DEEP_MIN_D
    in_win = pl.col("t").is_between(lo, hi - 1)
    pairs = {
        "toward": (
            rare.filter(near, pl.col("kind") == 1, in_win),
            log.filter(deep, pl.col("kind") == -1),
        ),
        "away": (
            rare.filter(near, pl.col("kind") == -1, in_win),
            log.filter(deep, pl.col("kind") == 1),
        ),
    }
    labels = [f"{a}-{b}" for a, b in zip(bins_ms[:-1], bins_ms[1:], strict=True)]
    edges = [b * 1000 for b in bins_ms[1:-1]]
    parts = []
    for direction, (tg, src) in pairs.items():
        if tg.height == 0:
            continue
        m = _match(tg, src, lag_us, lot).with_columns(
            pl.col("t").cut(edges, labels=labels, left_closed=True).cast(pl.Utf8).alias("bin"),
            pl.lit(direction).alias("direction"),
        )
        parts.append(
            m.group_by("e", "bin", "direction").agg(
                pl.col("size").sum().alias("v"),
                *(
                    (pl.col("size") * pl.col(c).cast(pl.Float64)).sum().alias(f"v_{c}")
                    for c in SHARES
                ),
                pl.len().alias("n"),
            )
        )
    if not parts:
        return pl.DataFrame(
            schema={"e": pl.Int64, "bin": pl.Utf8, "direction": pl.Utf8, "v": pl.Float64}
            | {f"v_{c}": pl.Float64 for c in SHARES}
            | {"n": pl.UInt32}
        ).rename({"e": "event_id"})
    return pl.concat(parts).rename({"e": "event_id"})


def _pooled(df: pl.DataFrame, keys: Sequence[str]) -> pl.DataFrame:
    """Volume shares per group: matched volume ÷ target volume (ratio of sums, weight w)."""
    tot = (pl.col("v") * pl.col("w")).sum()
    return df.group_by(keys).agg(
        *(((pl.col(f"v_{c}") * pl.col("w")).sum() / tot).alias(c) for c in SHARES),
        tot.alias("v"),
    )


def share_table(
    sweeps: pl.DataFrame, placebo: pl.DataFrame, *, n_boot: int = 200, seed: int = 0
) -> pl.DataFrame:
    """Shares for sweeps and weighted placebo per (direction, bin), with bins pooled as
    ``20-250`` and ``20-1000``. Day-cluster bootstrap CIs for the sweep shares, for
    ``beyond`` = exact − ctrl (sweeps) and for ``excess`` = beyond(sweeps) − beyond(placebo)."""
    import numpy as np

    def with_pools(df: pl.DataFrame) -> pl.DataFrame:
        early = df.filter(pl.col("bin").is_in(["20-100", "100-250"])).with_columns(
            pl.lit("20-250").alias("bin")
        )
        return pl.concat([df, early, df.with_columns(pl.lit("20-1000").alias("bin"))])

    s_all, p_all = with_pools(sweeps), with_pools(placebo)
    keys = ["direction", "bin"]
    days = s_all["day"].unique().sort().to_list()

    def one(ds: Sequence[str]) -> pl.DataFrame:
        cnt = pl.DataFrame({"day": list(ds)}).group_by("day").len()
        a = _pooled(s_all.join(cnt, on="day").with_columns(pl.col("w") * pl.col("len")), keys)
        b = _pooled(p_all.join(cnt, on="day").with_columns(pl.col("w") * pl.col("len")), keys)
        return (
            a.join(b, on=keys, suffix="_pl")
            .with_columns(
                (pl.col("exact") - pl.col("ctrl")).alias("beyond"),
                (pl.col("exact_pl") - pl.col("ctrl_pl")).alias("beyond_pl"),
            )
            .with_columns((pl.col("beyond") - pl.col("beyond_pl")).alias("excess"))
        )

    point = one(days).sort(keys)
    rng = np.random.default_rng(seed)
    boots = pl.concat([one(rng.choice(days, size=len(days)).tolist()) for _ in range(n_boot)])
    ci = boots.group_by(keys).agg(
        *(
            pl.col(c).quantile(q).alias(f"{c}_{s}")
            for c in (*SHARES, "beyond", "beyond_pl", "excess")
            for q, s in ((0.025, "lo"), (0.975, "hi"))
        )
    )
    return point.join(ci, on=keys).sort(keys)


def run_moves(
    out_dir: Path, results_dir: Path, *, max_push_ms: float = 20.0, n_boot: int = 200
) -> str:
    """Pool ``{day}_moves.parquet``; placebo reweighted by within-day NN state matching."""
    from lobflow.analysis import load_outputs
    from lobflow.robustness import COVS, load_tag, match_within_day

    data = load_outputs(out_dir, max_push_ms=max_push_ms)
    days = data["meta"].filter(pl.col("ok"))["day"].sort().to_list()
    have = [d for d in days if (out_dir / f"{d}_moves.parquet").exists()]
    if not have:
        raise ValueError(f"no moves outputs in {out_dir}")
    # ids must use the full day list (same offsets as load_outputs)
    parts = [
        pl.read_parquet(out_dir / f"{d}_moves.parquet").with_columns(
            (pl.col("event_id") + days.index(d) * 1_000_000).alias("event_id"),
            pl.lit(d).alias("day"),
        )
        for d in have
    ]
    mv = pl.concat(parts)
    keep = data["events"].filter(pl.col("cleared_frac") >= 0.95)["event_id"]
    s_info = load_tag(out_dir, days, "flows_info").filter(pl.col("valid"))
    p_info = load_tag(out_dir, days, "flows_placebo_info").filter(pl.col("valid"))
    state = data["state"]
    s_cov = state.filter(pl.col("set") == "sweep").join(
        s_info.filter(pl.col("event_id").is_in(keep.implode())).select("event_id", *COVS[2:]),
        on="event_id",
    )
    p_cov = state.filter(pl.col("set") == "placebo").join(
        p_info.select("event_id", *COVS[2:]), on="event_id"
    )
    w = match_within_day(s_cov, p_cov, method="nn", min_n=8)
    sweeps = mv.filter(
        pl.col("set") == "sweep", pl.col("event_id").is_in(s_cov["event_id"].implode())
    ).with_columns(pl.lit(1.0).alias("w"))
    placebo = mv.filter(pl.col("set") == "placebo").join(w, on="event_id", how="inner")
    tab = share_table(sweeps, placebo, n_boot=n_boot)
    results_dir.mkdir(parents=True, exist_ok=True)
    tab.write_parquet(results_dir / "moves.parquet")

    def f(r: dict[str, object], c: str) -> str:
        return f"{r[c]:.3f} [{r[c + '_lo']:.3f}, {r[c + '_hi']:.3f}]"

    lines = [
        "# Exact-size matching: are near-touch additions moved deep orders?",
        "",
        f"Days: {len(have)}. Sweeps: {sweeps['event_id'].n_unique()}. Placebo (NN-matched): "
        f"{placebo['event_id'].n_unique()}.",
        "Share of rare-size near-touch (d ≤ 5) addition volume (`toward`) whose size exactly "
        "equals a cancellation at a strictly deeper price (d ≥ 6) within 100 ms in the same "
        "event (`exact`; split: same message / cancel first / post first), vs sizes one lot "
        "apart (`ctrl`, coincidence rate). `away`: near cancellations matched to deeper "
        "additions. beyond = exact − ctrl; excess = beyond(sweeps) − beyond(placebo, NN-matched). "
        "95% day-bootstrap CIs.",
        "",
        "| direction | bin (ms) | exact | same msg | cancel first | post first | ctrl | "
        "beyond | placebo exact | placebo ctrl | excess |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in tab.iter_rows(named=True):
        lines.append(
            f"| {r['direction']} | {r['bin']} | {f(r, 'exact')} | {r['same']:.3f} | "
            f"{r['src_first']:.3f} | {r['tgt_first']:.3f} | {f(r, 'ctrl')} | {f(r, 'beyond')} | "
            f"{r['exact_pl']:.3f} | {r['ctrl_pl']:.3f} | {f(r, 'excess')} |"
        )
    text = "\n".join(lines) + "\n"
    (results_dir / "moves.md").write_text(text)
    return text
