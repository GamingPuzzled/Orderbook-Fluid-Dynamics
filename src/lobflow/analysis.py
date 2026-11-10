"""Pooled analysis of moving-frame refill: sweeps vs placebo.

Statistics
----------
1. **Bucket recovery** R(b, τ) = Σ_e depth_e(b, τ) / Σ_e depth_e(b, pre) over distance buckets
   b from the current opposite best quote (ratio of sums; rows must be observed both pre and
   at τ). Reported for sweeps, placebo, and their difference, with event-bootstrap CIs.
2. **Half-recovery order** — per event and bucket, the first τ at which depth ≥ 50% of its
   pre-shock value. Transport (refill from deep liquidity) predicts deep buckets recover first;
   touch posting (source) predicts shallow buckets first.
3. **Spread-closure decomposition** — in sweep-direction ticks relative to pre-shock:
   ``opp_adv`` (opposite best advances into the gap: price relocation) and
   ``swept_back`` (swept-side best returns toward its pre-shock level: replenishment).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import polars as pl

BUCKETS: tuple[tuple[int, int], ...] = ((1, 1), (2, 2), (3, 5), (6, 10), (11, 20), (21, 50))


def bucket_expr(buckets: Sequence[tuple[int, int]] = BUCKETS) -> pl.Expr:
    expr = pl.lit(None, dtype=pl.Utf8)
    for lo, hi in reversed(buckets):
        label = f"{lo}" if lo == hi else f"{lo}-{hi}"
        expr = pl.when(pl.col("d").is_between(lo, hi)).then(pl.lit(label)).otherwise(expr)
    return expr.alias("bucket")


def bucket_labels(buckets: Sequence[tuple[int, int]] = BUCKETS) -> list[str]:
    return [f"{lo}" if lo == hi else f"{lo}-{hi}" for lo, hi in buckets]


def load_outputs(
    out_dir: Path, *, max_push_ms: float = 20.0, min_levels: int = 50
) -> dict[str, pl.DataFrame]:
    """Load per-day outputs for days whose feed matches the main-sample spec.

    Event and placebo ids are made globally unique as ``day * 1e6 + id``.
    """
    metas = [json.loads(p.read_text()) for p in sorted(out_dir.glob("*_meta.json"))]
    days_ok: list[str] = []
    meta_rows = []
    for m in metas:
        f = m["feed"]
        ok = (
            f["push_interval_ms_p50"] <= max_push_ms
            and min(f["snapshot_levels_bid"], f["snapshot_levels_ask"]) >= min_levels
            and m.get("n_events", 0) > 0
        )
        meta_rows.append({"day": m["day"], "ok": ok, "n_events": m.get("n_events", 0), **f})
        if ok:
            days_ok.append(m["day"])

    def _load(kind: str) -> pl.DataFrame:
        parts = []
        for k, day in enumerate(days_ok):
            df = pl.read_parquet(out_dir / f"{day}_{kind}.parquet")
            parts.append(
                df.with_columns(
                    (pl.col("event_id") + k * 1_000_000).alias("event_id"), pl.lit(day).alias("day")
                )
            )
        return pl.concat(parts, how="diagonal_relaxed") if parts else pl.DataFrame()

    events = _load("events")
    out = {
        "meta": pl.DataFrame(meta_rows),
        "events": events,
        "moving": _load("moving"),
        "placebo": _load("placebo"),
    }
    if days_ok and all((out_dir / f"{d}_flows_info.parquet").exists() for d in days_ok):
        for kind in ("flows", "flows_info", "flows_placebo", "flows_placebo_info"):
            out[kind] = _load(kind)
    if days_ok and all((out_dir / f"{d}_state.parquet").exists() for d in days_ok):
        out["state"] = _load("state")
    return out


def placebo_weights(
    state: pl.DataFrame, sweep_info: pl.DataFrame, placebo_info: pl.DataFrame
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """State-matching weights for placebo events, matched within each day.

    Strata: quartiles (of that day's sweeps) of 10 s volume, 60 s realised variation and
    pre-shock swept-side depth. Returns (weights: event_id, w), and a balance table of mean
    covariates for sweeps, raw placebo and weighted placebo.
    """
    from lobflow.state import matching_weights

    cols = ("vol_10s", "rv_60s", "depth_pre_swept")
    s_all = state.filter(pl.col("set") == "sweep").join(
        sweep_info.filter(pl.col("valid")).select("event_id", "depth_pre_swept"), on="event_id"
    )
    p_all = state.filter(pl.col("set") == "placebo").join(
        placebo_info.filter(pl.col("valid")).select("event_id", "depth_pre_swept"),
        on="event_id",
    )
    parts = []
    for day in s_all["day"].unique().sort().to_list():
        sd, pd_ = s_all.filter(pl.col("day") == day), p_all.filter(pl.col("day") == day)
        if sd.height < 8 or pd_.height == 0:
            continue
        parts.append(matching_weights(sd, pd_, columns=cols))
    w = pl.concat(parts)
    bal_cols = [*cols, "n_10s"]
    s_mean = s_all.select([pl.col(c).cast(pl.Float64).mean() for c in bal_cols]).row(0)
    p_mean = p_all.select([pl.col(c).cast(pl.Float64).mean() for c in bal_cols]).row(0)
    w_mean = w.select(
        [(pl.col(c).cast(pl.Float64) * pl.col("w")).sum() / pl.col("w").sum() for c in bal_cols]
    ).row(0)
    coverage = w.group_by("day").agg(pl.col("sweep_coverage").first())["sweep_coverage"].mean()
    balance = pl.DataFrame(
        {
            "covariate": bal_cols,
            "sweep": list(s_mean),
            "placebo_raw": list(p_mean),
            "placebo_matched": list(w_mean),
            "mean_sweep_coverage": [coverage] * len(bal_cols),
        },
        schema_overrides={"mean_sweep_coverage": pl.Float64},
    )
    return w.select("event_id", "w"), balance


def _weighted(df: pl.DataFrame, w: pl.DataFrame, cols: Sequence[str]) -> pl.DataFrame:
    """Scale per-event columns by placebo weights (ratio-of-sums reweighting)."""
    return (
        df.join(w, on="event_id", how="inner")
        .with_columns([pl.col(c) * pl.col("w") for c in cols])
        .drop("w")
    )


NEAR_ZONES = ("1-5",)
FAR_ZONES = ("11-20", "21-50")
POST_WINDOWS = ("20-40", "40-100", "100-250", "250-1000")


def _flow_day_sums(flows: pl.DataFrame, info: pl.DataFrame) -> pl.DataFrame:
    """Per day × window × zone × metric swept-side sums, plus per-day pre-shock depth."""
    ok = info.filter(pl.col("valid"))
    f = flows.filter(pl.col("side") == "swept", pl.col("event_id").is_in(ok["event_id"].implode()))
    depth = ok.group_by("day").agg(pl.col("depth_pre_swept").sum().alias("D"))
    sums = f.group_by("day", "window", "zone", "metric").agg(pl.col("value").sum())
    return sums.join(depth, on="day")


def flow_balance(flows: pl.DataFrame, info: pl.DataFrame) -> pl.DataFrame:
    """Swept-side gross flows per window and zone, as fractions of pooled pre-shock depth."""
    s = _flow_day_sums(flows, info)
    d_pre = float(s.select("day", "D").unique()["D"].sum())
    return (
        s.group_by("window", "zone", "metric")
        .agg((pl.col("value").sum() / d_pre).alias("frac"))
        .pivot(on="metric", index=["window", "zone"], values="frac")
        .fill_null(0.0)
    )


def _transport_stats(day_sums: pl.DataFrame, windows: Sequence[str]) -> dict[str, float]:
    """Pooled (ratio-of-sums) totals over ``windows`` for one set."""
    s = day_sums.filter(pl.col("window").is_in(list(windows)))
    d_pre = float(s.select("day", "D").unique()["D"].sum())

    def tot(metric: str, zones: Sequence[str] | None = None) -> float:
        q = s.filter(pl.col("metric") == metric)
        if zones is not None:
            q = q.filter(pl.col("zone").is_in(list(zones)))
        return float(q["value"].sum()) / d_pre

    return {
        "add": tot("add"),
        "cancel": tot("cancel"),
        "edge_out": tot("edge_out"),
        "near_add": tot("add", NEAR_ZONES),
        "near_cancel": tot("cancel", NEAR_ZONES),
        "far_add": tot("add", FAR_ZONES),
        "far_cancel": tot("cancel", FAR_ZONES),
    }


def transport_test(
    sweeps: tuple[pl.DataFrame, pl.DataFrame],
    placebo: tuple[pl.DataFrame, pl.DataFrame],
    *,
    windows: Sequence[str] = POST_WINDOWS,
    n_boot: int = 300,
    seed: int = 0,
) -> pl.DataFrame:
    """Mass-balance test per post-shock window (and all windows pooled).

    Statistics (fractions of pre-shock swept-side depth, sweeps minus placebo = excess):

    - ``kappa`` = add / cancel (sweeps). ≈ 1: churn conserves depth; > 1: net source.
    - ``kappa_lo`` = add / (cancel + edge_out): cancellations at their upper bound.
    - ``x_near_net`` = excess (add − cancel) in the near zone (d ≤ 5).
    - ``x_far_net`` = excess (cancel − add) in the far zone (11 ≤ d ≤ 50).
    - ``cover`` = x_far_net / x_near_net: share of the excess near-touch build-up that is
      matched by excess far-zone depletion (≥ 1: fully fundable by repositioning).

    CIs: day-cluster bootstrap (2.5%, 97.5%).
    """
    s_sums = _flow_day_sums(*sweeps)
    p_sums = _flow_day_sums(*placebo)
    days = s_sums["day"].unique().sort().to_list()
    rng = np.random.default_rng(seed)
    rows = []
    for label, wins in [*((w, (w,)) for w in windows), ("20-1000", tuple(windows))]:

        def stat(ds: list[str], wins: tuple[str, ...] = wins) -> dict[str, float]:
            a = _transport_stats(_resample(s_sums, ds), wins)
            b = _transport_stats(_resample(p_sums, ds), wins)
            x_near = (a["near_add"] - a["near_cancel"]) - (b["near_add"] - b["near_cancel"])
            x_far = (a["far_cancel"] - a["far_add"]) - (b["far_cancel"] - b["far_add"])
            return {
                "kappa": a["add"] / a["cancel"] if a["cancel"] else float("nan"),
                "kappa_lo": a["add"] / (a["cancel"] + a["edge_out"]),
                "kappa_placebo": b["add"] / b["cancel"] if b["cancel"] else float("nan"),
                "add": a["add"],
                "cancel": a["cancel"],
                "add_placebo": b["add"],
                "cancel_placebo": b["cancel"],
                "x_near_net": x_near,
                "x_far_net": x_far,
                "cover": x_far / x_near if x_near else float("nan"),
            }

        point = stat(days)
        boots = [stat(rng.choice(days, size=len(days)).tolist()) for _ in range(n_boot)]
        row: dict[str, object] = {"window": label, **point}
        for k in ("kappa", "x_near_net", "x_far_net", "cover"):
            v = np.array([b[k] for b in boots], dtype=float)
            row[f"{k}_lo"] = float(np.nanpercentile(v, 2.5))
            row[f"{k}_hi"] = float(np.nanpercentile(v, 97.5))
        rows.append(row)
    return pl.DataFrame(rows)


def _resample(day_sums: pl.DataFrame, days: list[str]) -> pl.DataFrame:
    """Stack per-day rows for a (possibly repeated) list of days."""
    counts = pl.DataFrame({"day": days}).group_by("day").len()
    return (
        day_sums.join(counts, on="day")
        .with_columns(pl.col("value") * pl.col("len"), pl.col("D") * pl.col("len"))
        .drop("len")
    )


def link_correlation(
    flows: pl.DataFrame, info: pl.DataFrame, windows: Sequence[str] = POST_WINDOWS
) -> pl.DataFrame:
    """Per-event Spearman correlation of near-zone additions with far-zone cancellations
    (both normalised by the event's pre-shock depth), by window."""
    ok = info.filter(pl.col("valid"), pl.col("depth_pre_swept") > 0)
    f = flows.filter(pl.col("side") == "swept", pl.col("event_id").is_in(ok["event_id"].implode()))
    near = (
        f.filter(pl.col("metric") == "add", pl.col("zone").is_in(list(NEAR_ZONES)))
        .group_by("event_id", "window")
        .agg(pl.col("value").sum().alias("near_add"))
    )
    far = (
        f.filter(pl.col("metric") == "cancel", pl.col("zone").is_in(list(FAR_ZONES)))
        .group_by("event_id", "window")
        .agg(pl.col("value").sum().alias("far_cancel"))
    )
    grid = ok.select("event_id", "depth_pre_swept").join(
        pl.DataFrame({"window": list(windows)}), how="cross"
    )
    j = (
        grid.join(near, on=["event_id", "window"], how="left")
        .join(far, on=["event_id", "window"], how="left")
        .fill_null(0.0)
    )
    return (
        j.group_by("window")
        .agg(
            pl.len().alias("n"),
            pl.corr(
                pl.col("near_add") / pl.col("depth_pre_swept"),
                pl.col("far_cancel") / pl.col("depth_pre_swept"),
                method="spearman",
            ).alias("rho"),
        )
        .sort("window")
    )


def _event_bucket_sums(
    prof: pl.DataFrame, buckets: Sequence[tuple[int, int]] = BUCKETS
) -> pl.DataFrame:
    """Per (event, bucket, τ): depth sum and matched pre-shock depth sum (observed in both)."""
    pre = prof.filter(pl.col("tau_ms") == -1).select(
        "event_id", "d", pl.col("depth").alias("depth_pre"), pl.col("observed").alias("obs_pre")
    )
    post = prof.filter(pl.col("tau_ms") > 0).join(pre, on=["event_id", "d"])
    post = post.filter(pl.col("observed") & pl.col("obs_pre")).with_columns(bucket_expr(buckets))
    post = post.filter(pl.col("bucket").is_not_null())
    return post.group_by("event_id", "bucket", "tau_ms").agg(
        pl.col("depth").sum().alias("num"), pl.col("depth_pre").sum().alias("den")
    )


def bucket_recovery(
    prof: pl.DataFrame,
    *,
    n_boot: int = 300,
    seed: int = 0,
    buckets: Sequence[tuple[int, int]] = BUCKETS,
) -> pl.DataFrame:
    """Ratio-of-sums recovery per (bucket, τ) with 95% event-bootstrap CI."""
    s = _event_bucket_sums(prof, buckets)
    out = []
    rng = np.random.default_rng(seed)
    for (bucket, tau), g in s.group_by("bucket", "tau_ms"):
        num, den = g["num"].to_numpy(), g["den"].to_numpy()
        if den.sum() <= 0:
            continue
        r = num.sum() / den.sum()
        idx = rng.integers(0, num.size, size=(n_boot, num.size))
        boots = num[idx].sum(1) / np.maximum(den[idx].sum(1), 1e-12)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out.append({"bucket": bucket, "tau_ms": tau, "R": r, "lo": lo, "hi": hi, "n": num.size})
    order = {b: i for i, b in enumerate(bucket_labels(buckets))}
    return (
        pl.DataFrame(out)
        .with_columns(pl.col("bucket").replace_strict(order, return_dtype=pl.Int64).alias("_o"))
        .sort("_o", "tau_ms")
        .drop("_o")
    )


def composition_recovery(
    prof: pl.DataFrame, buckets: Sequence[tuple[int, int]] = BUCKETS
) -> pl.DataFrame:
    """Split recovery R(b, τ) into surviving (upper bound) and new (lower bound) parts.

    Uses cells where both the moving-frame pre-shock depth and the same-price surviving bound
    are known. ``R_surv = Σ surv_ub / Σ depth_pre``, ``R_new = Σ (depth − surv_ub) /
    Σ depth_pre``, so ``R_known = R_surv + R_new``. ``known_share`` is the fraction of post-shock
    depth (in observed cells) whose pre-shock price was observed.
    """
    if "surv_ub" not in prof.columns:
        raise ValueError("profile lacks surv_ub; reprocess days with the current pipeline")
    pre = prof.filter(pl.col("tau_ms") == -1).select(
        "event_id", "d", pl.col("depth").alias("depth_pre"), pl.col("observed").alias("obs_pre")
    )
    post = (
        prof.filter((pl.col("tau_ms") > 0) & pl.col("observed"))
        .join(pre, on=["event_id", "d"])
        .filter(pl.col("obs_pre"))
        .with_columns(bucket_expr(buckets))
        .filter(pl.col("bucket").is_not_null())
    )
    known = pl.col("surv_ub").is_not_null() & pl.col("surv_ub").is_not_nan()
    g = post.group_by("bucket", "tau_ms").agg(
        pl.col("depth").filter(known).sum().alias("dep_k"),
        pl.col("surv_ub").filter(known).sum().alias("surv"),
        pl.col("depth_pre").filter(known).sum().alias("pre_k"),
        pl.col("depth").sum().alias("dep_all"),
    )
    order = {b: i for i, b in enumerate(bucket_labels(buckets))}
    return (
        g.with_columns(
            (pl.col("surv") / pl.col("pre_k")).alias("R_surv"),
            ((pl.col("dep_k") - pl.col("surv")) / pl.col("pre_k")).alias("R_new"),
            (pl.col("dep_k") / pl.col("pre_k")).alias("R_known"),
            (pl.col("dep_k") / pl.col("dep_all")).alias("known_share"),
            pl.col("bucket").replace_strict(order, return_dtype=pl.Int64).alias("_o"),
        )
        .sort("_o", "tau_ms")
        .drop("_o")
    )


def half_recovery_order(
    prof: pl.DataFrame,
    *,
    frac: float = 0.5,
    censor_ms: int = 2000,
    require_depleted: bool = True,
    buckets: Sequence[tuple[int, int]] = BUCKETS,
) -> pl.DataFrame:
    """Per event: first τ at which each bucket reaches ``frac`` of its pre-shock depth.

    Buckets with zero pre-shock depth are dropped; never-recovered buckets are censored at
    ``censor_ms``. With ``require_depleted`` only buckets below ``frac`` at the first sample
    are kept, so undepleted buckets do not count as "recovered first". Returns one row per
    (event, bucket) with ``t_half``.
    """
    s = _event_bucket_sums(prof, buckets).filter(pl.col("den") > 0)
    if require_depleted:
        # keep (event, bucket) pairs that are below `frac` of pre depth at the first sample
        t_first = s["tau_ms"].min()
        dep = s.filter(
            (pl.col("tau_ms") == t_first) & (pl.col("num") < frac * pl.col("den"))
        ).select("event_id", "bucket")
        s = s.join(dep, on=["event_id", "bucket"])
    rec = s.filter(pl.col("num") >= frac * pl.col("den"))
    first = rec.group_by("event_id", "bucket").agg(pl.col("tau_ms").min().alias("t_half"))
    allb = s.select("event_id", "bucket").unique()
    return allb.join(first, on=["event_id", "bucket"], how="left").with_columns(
        pl.col("t_half").fill_null(censor_ms)
    )


def order_summary(halves: pl.DataFrame, shallow: str = "1", deep: str = "6-10") -> dict[str, float]:
    """P(shallow bucket half-recovers strictly before deep), P(after), P(tie) across events."""
    w = (
        halves.filter(pl.col("bucket").is_in([shallow, deep]))
        .pivot(on="bucket", index="event_id", values="t_half")
        .drop_nulls()
    )
    if w.height == 0:
        return {
            "n": 0.0,
            "p_shallow_first": float("nan"),
            "p_deep_first": float("nan"),
            "p_tie": float("nan"),
        }
    a, b = w[shallow].to_numpy(), w[deep].to_numpy()
    return {
        "n": float(w.height),
        "p_shallow_first": float(np.mean(a < b)),
        "p_deep_first": float(np.mean(a > b)),
        "p_tie": float(np.mean(a == b)),
    }


def spread_decomposition(prof: pl.DataFrame, info: pl.DataFrame) -> pl.DataFrame:
    """Per (event, τ): opposite-side advance and swept-side displacement, sweep-direction ticks.

    ``info``: DataFrame (event_id, is_buy, tick). Best quotes are rebuilt from mid and spread.
    """
    q = (
        prof.filter(pl.col("d") == 1)
        .select("event_id", "tau_ms", "mid", "spread_ticks")
        .join(info.select("event_id", "is_buy", "tick"), on="event_id")
    )
    sign = pl.when(pl.col("is_buy")).then(1.0).otherwise(-1.0)
    half = pl.col("spread_ticks") * pl.col("tick") / 2
    q = q.with_columns(
        (pl.col("mid") + sign * half).alias("best_swept"),  # ask for buy sweep
        (pl.col("mid") - sign * half).alias("best_opp"),
    )
    pre = q.filter(pl.col("tau_ms") == -1).select(
        "event_id",
        pl.col("best_swept").alias("swept_pre"),
        pl.col("best_opp").alias("opp_pre"),
        pl.col("spread_ticks").alias("spread_pre"),
    )
    return (
        q.filter(pl.col("tau_ms") > 0)
        .join(pre, on="event_id")
        .with_columns(
            ((pl.col("best_opp") - pl.col("opp_pre")) * sign / pl.col("tick")).alias("opp_adv"),
            ((pl.col("best_swept") - pl.col("swept_pre")) * sign / pl.col("tick")).alias(
                "swept_disp"
            ),
            (pl.col("spread_ticks") - pl.col("spread_pre")).alias("d_spread"),
        )
        .select("event_id", "tau_ms", "opp_adv", "swept_disp", "d_spread", "spread_ticks")
    )


def _fmt_table(df: pl.DataFrame, value: str, digits: int = 2) -> str:
    """Markdown table: rows = bucket, columns = τ."""
    w = df.pivot(on="tau_ms", index="bucket", values=value, sort_columns=True)
    cols = w.columns
    lines = ["| " + " | ".join(["d \\ τ (ms)", *cols[1:]]) + " |", "|" + "---|" * len(cols)]
    for row in w.iter_rows():
        cells = [str(row[0])] + [f"{v:.{digits}f}" if v is not None else "—" for v in row[1:]]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _flow_summary_lines(
    tt: pl.DataFrame, bal_s: pl.DataFrame, bal_p: pl.DataFrame, link: pl.DataFrame
) -> list[str]:
    def ci(r: dict[str, float], k: str) -> str:
        return f"{r[k]:.3f} [{r[k + '_lo']:.3f}, {r[k + '_hi']:.3f}]"

    lines = [
        "## Mass balance — gross flows on the swept side (fractions of pre-shock depth)",
        "Windows by book-message time after t0. kappa = add / cancel (≈1 conserved churn, >1 "
        "net source); kappa_lo uses cancel + edge_out. x_near_net = excess (sweep − placebo) "
        "net build-up at d ≤ 5; x_far_net = excess net depletion at 11 ≤ d ≤ 50; cover = "
        "x_far / x_near. 95% day-cluster bootstrap CIs.",
        "",
        "| window | add | cancel | kappa | kappa_lo | kappa placebo | x_near_net | x_far_net "
        "| cover |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in tt.iter_rows(named=True):
        lines.append(
            f"| {r['window']} | {r['add']:.3f} | {r['cancel']:.3f} | {ci(r, 'kappa')} | "
            f"{r['kappa_lo']:.3f} | {r['kappa_placebo']:.3f} | {ci(r, 'x_near_net')} | "
            f"{ci(r, 'x_far_net')} | {ci(r, 'cover')} |"
        )
    lines += ["", "Net (add − cancel) by zone, fractions of pre-shock depth:", ""]
    for name, bal in (("sweep", bal_s), ("placebo", bal_p)):
        t = bal.with_columns((pl.col("add") - pl.col("cancel")).alias("net"))
        piv = t.pivot(on="window", index="zone", values="net")
        cols = [c for c in ("0-20", *POST_WINDOWS) if c in piv.columns]
        zones = [z for z in ("1-5", "6-10", "11-20", "21-50", "51+") if z in piv["zone"]]
        lines += [f"{name}:", "", "| zone | " + " | ".join(cols) + " |"]
        lines.append("|---" * (len(cols) + 1) + "|")
        for z in zones:
            r = piv.filter(pl.col("zone") == z).row(0, named=True)
            lines.append(f"| {z} | " + " | ".join(f"{r[c]:.3f}" for c in cols) + " |")
        lines.append("")
    lines += [
        "Per-event Spearman rho(near add, far cancel), normalised by pre depth:",
        "",
        "| set | window | n | rho |",
        "|---|---|---|---|",
        *[
            f"| {r['set']} | {r['window']} | {r['n']} | {r['rho']:.3f} |"
            for r in link.iter_rows(named=True)
        ],
    ]
    return lines


def _matched_lines(
    tt: pl.DataFrame,
    balance: pl.DataFrame,
    comp_s: pl.DataFrame | None,
    comp_pm: pl.DataFrame | None,
) -> list[str]:
    lines = [
        "",
        "## State-matched placebo (within-day CEM on 10 s volume, 60 s RV, pre depth)",
        f"Mean share of sweeps in strata with placebo support: "
        f"{balance['mean_sweep_coverage'][0]:.2f}.",
        "",
        "| covariate | sweep | placebo raw | placebo matched |",
        "|---|---|---|---|",
        *[
            f"| {r['covariate']} | {r['sweep']:.4g} | {r['placebo_raw']:.4g} | "
            f"{r['placebo_matched']:.4g} |"
            for r in balance.iter_rows(named=True)
        ],
        "",
        "| window | kappa sweep | kappa matched placebo | x_near_net | x_far_net | cover |",
        "|---|---|---|---|---|---|",
    ]
    for r in tt.iter_rows(named=True):
        lines.append(
            f"| {r['window']} | {r['kappa']:.3f} | {r['kappa_placebo']:.3f} | "
            f"{r['x_near_net']:.3f} [{r['x_near_net_lo']:.3f}, {r['x_near_net_hi']:.3f}] | "
            f"{r['x_far_net']:.3f} [{r['x_far_net_lo']:.3f}, {r['x_far_net_hi']:.3f}] | "
            f"{r['cover']:.2f} [{r['cover_lo']:.2f}, {r['cover_hi']:.2f}] |"
        )
    if comp_s is not None and comp_pm is not None:
        lines += [
            "",
            "R_new — matched placebo:",
            _fmt_table(comp_pm, "R_new"),
        ]
    return lines


def run(
    out_dir: Path,
    results_dir: Path,
    *,
    min_cleared: float = 0.95,
    n_boot: int = 300,
    max_push_ms: float = 20.0,
) -> str:
    """Pool all main-sample days, compute statistics, write ``summary.md`` + parquet tables."""
    data = load_outputs(out_dir, max_push_ms=max_push_ms)
    ev, mv, pb, meta = data["events"], data["moving"], data["placebo"], data["meta"]
    if ev.height == 0:
        raise ValueError(f"no usable days in {out_dir}")
    keep = ev.filter(pl.col("cleared_frac") >= min_cleared)
    mv = mv.filter(pl.col("event_id").is_in(keep["event_id"].implode()))

    rec_s = bucket_recovery(mv, n_boot=n_boot).with_columns(pl.lit("sweep").alias("set"))
    rec_p = bucket_recovery(pb, n_boot=n_boot).with_columns(pl.lit("placebo").alias("set"))
    excess = rec_s.join(rec_p, on=["bucket", "tau_ms"], suffix="_pl").with_columns(
        (pl.col("R") - pl.col("R_pl")).alias("excess")
    )
    fine = tuple((k, k) for k in range(1, 11))
    rec_fine = bucket_recovery(mv, n_boot=n_boot, buckets=fine)
    halves = half_recovery_order(mv, buckets=fine)
    comp_s = composition_recovery(mv) if "surv_ub" in mv.columns else None
    comp_p = composition_recovery(pb) if "surv_ub" in pb.columns else None
    t_half_by_d = (
        halves.group_by("bucket")
        .agg(
            pl.len().alias("n_depleted"),
            pl.col("t_half").median().alias("t_half_median"),
            (pl.col("t_half") >= 2000).mean().alias("p_unrecovered"),
        )
        .with_columns(pl.col("bucket").cast(pl.Int64))
        .sort("bucket")
    )
    orders = {f"1 vs {b}": order_summary(halves, "1", b) for b in ("2", "3", "5")}

    tick_by_day = ev.group_by("day").agg(pl.col("tick").first())
    info_s = keep.select("event_id", (pl.col("side") == "buy").alias("is_buy"), "tick")
    info_p = pb.select("event_id", "is_buy", "day").unique().join(tick_by_day, on="day")
    dec_s = spread_decomposition(mv, info_s)
    dec_p = spread_decomposition(pb, info_p)
    dsum = (
        pl.concat(
            [
                dec_s.with_columns(pl.lit("sweep").alias("set")),
                dec_p.with_columns(pl.lit("placebo").alias("set")),
            ]
        )
        .group_by("set", "tau_ms")
        .agg(
            pl.col("opp_adv").median().alias("opp_adv_med"),
            pl.col("swept_disp").median().alias("swept_disp_med"),
            pl.col("d_spread").median().alias("d_spread_med"),
            (pl.col("spread_ticks") <= 1.0).mean().alias("p_one_tick_spread"),
        )
        .sort("set", "tau_ms", descending=[True, False])
    )

    results_dir.mkdir(parents=True, exist_ok=True)
    rec_s.vstack(rec_p).write_parquet(results_dir / "bucket_recovery.parquet")
    halves.write_parquet(results_dir / "half_recovery.parquet")
    dec_s.write_parquet(results_dir / "spread_decomp_sweeps.parquet")

    flow_lines: list[str] = []
    if "flows" in data:
        f_info = data["flows_info"].filter(pl.col("event_id").is_in(keep["event_id"].implode()))
        sw_set = (data["flows"], f_info)
        pb_set = (data["flows_placebo"], data["flows_placebo_info"])
        tt = transport_test(sw_set, pb_set, n_boot=n_boot)
        bal_s = flow_balance(*sw_set).with_columns(pl.lit("sweep").alias("set"))
        bal_p = flow_balance(*pb_set).with_columns(pl.lit("placebo").alias("set"))
        link_s = link_correlation(*sw_set).with_columns(pl.lit("sweep").alias("set"))
        link_p = link_correlation(*pb_set).with_columns(pl.lit("placebo").alias("set"))
        tt.write_parquet(results_dir / "transport_test.parquet")
        pl.concat([bal_s, bal_p], how="diagonal_relaxed").write_parquet(
            results_dir / "flow_balance.parquet"
        )
        flow_lines = _flow_summary_lines(tt, bal_s, bal_p, pl.concat([link_s, link_p]))
        if "state" in data:
            w, balance = placebo_weights(data["state"], f_info, data["flows_placebo_info"])
            pb_m = (
                _weighted(data["flows_placebo"], w, ("value",)),
                _weighted(data["flows_placebo_info"], w, ("depth_pre_swept",)),
            )
            tt_m = transport_test(sw_set, pb_m, n_boot=n_boot)
            tt_m.write_parquet(results_dir / "transport_test_matched.parquet")
            comp_pm = (
                composition_recovery(_weighted(pb, w, ("depth", "surv_ub")))
                if "surv_ub" in pb.columns
                else None
            )
            flow_lines += _matched_lines(tt_m, balance, comp_s, comp_pm)

    used = meta.filter(pl.col("ok"))
    lines = [
        "# Moving-frame refill — pooled results",
        "",
        f"Days used: {used.height} of {meta.height} "
        f"(feed: push ≤ {max_push_ms:g} ms, ≥ 50 levels). "
        f"Sweeps: {ev.height} detected, {keep.height} with cleared fraction ≥ {min_cleared}. "
        f"Placebo times: {pb['event_id'].n_unique()}.",
        "",
        "Frame: swept-side depth at distance d ticks from the current opposite best quote.",
        "R = Σ depth(d, τ) / Σ depth_pre(d) (ratio of sums; 95% event-bootstrap CI in parquet).",
        "",
        "## Recovery R — sweeps",
        _fmt_table(rec_s, "R"),
        "",
        "## Recovery R — placebo (no large sweep within ±2 s)",
        _fmt_table(rec_p, "R"),
        "",
        "## Excess recovery (sweep − placebo)",
        _fmt_table(excess, "excess"),
        "",
        *(
            [
                "## Composition — sweeps: surviving (upper bound) vs new (lower bound)",
                "R_surv ≤ depth already resting at that price pre-shock; R_new ≥ depth added "
                "after the shock (running-minimum bound per price). Cells with known pre-shock "
                "price only.",
                "",
                "R_new:",
                _fmt_table(comp_s, "R_new"),
                "",
                "R_surv:",
                _fmt_table(comp_s, "R_surv"),
                "",
                "Known share of post-shock depth:",
                _fmt_table(comp_s, "known_share"),
                "",
                "## Composition — placebo, R_new:",
                _fmt_table(comp_p, "R_new"),
                "",
            ]
            if comp_s is not None and comp_p is not None
            else []
        ),
        "## Recovery R by single tick distance — sweeps",
        _fmt_table(rec_fine.with_columns(pl.col("bucket").cast(pl.Int64)).sort("bucket"), "R"),
        "",
        "## Half-recovery time by distance (buckets depleted at τ=20 ms only)",
        "| d | n depleted | median t½ (ms) | P(not recovered by 1 s) |",
        "|---|---|---|---|",
        *[
            f"| {r['bucket']} | {r['n_depleted']} | {r['t_half_median']:.0f} | "
            f"{r['p_unrecovered']:.2f} |"
            for r in t_half_by_d.iter_rows(named=True)
        ],
        "",
        "## Half-recovery order (per event, both buckets depleted; censored at 2000 ms)",
        "| comparison | n | P(touch first) | P(deep first) | P(tie) |",
        "|---|---|---|---|---|",
        *[
            f"| d={k} | {int(v['n'])} | {v['p_shallow_first']:.2f} | {v['p_deep_first']:.2f} | "
            f"{v['p_tie']:.2f} |"
            for k, v in orders.items()
        ],
        "",
        "## Spread closure (medians, sweep-direction ticks vs pre-shock)",
        "opp_adv > 0: opposite best advanced into the gap. swept_disp > 0: swept-side best "
        "sits further away than pre-shock.",
        "",
        "| set | τ | opp_adv | swept_disp | Δspread | P(1-tick spread) |",
        "|---|---|---|---|---|---|",
        *[
            f"| {r['set']} | {r['tau_ms']} | {r['opp_adv_med']:.1f} | {r['swept_disp_med']:.1f} | "
            f"{r['d_spread_med']:.1f} | {r['p_one_tick_spread']:.2f} |"
            for r in dsum.iter_rows(named=True)
        ],
        "",
        *flow_lines,
    ]
    text = "\n".join(lines) + "\n"
    (results_dir / "summary.md").write_text(text)
    return text
