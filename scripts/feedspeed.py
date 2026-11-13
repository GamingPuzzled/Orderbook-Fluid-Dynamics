"""How much repositioning does a slower feed hide? (feed-speed emulation)

Compares excess repositioning for Bybit BTCUSDT at its real 20 ms feed (tag ``flowsfine``),
Bybit BTCUSDT with its book messages netted into 52, 100 and 200 ms buckets on a fixed clock
(tags ``flowscoarse<ms>``; ``lobflow flows --coarsen-ms <ms>``), and Binance BTCUSDT (52 ms
feed). Two outputs:

- by levels cleared (Bybit 20 ms, Bybit emulated 52 ms, Binance): is Binance's weaker
  repositioning a feed and sweep-mix effect?
- the feed-speed curve (Bybit at 20/52/100/200 ms): how fast measured repositioning decays
  with the netting interval, which predicts what a 100 ms feed (OKX) can show and bounds what
  the 20 ms feed misses.

"Before 250 ms" sums the windows that end by 250 ms (20–200 ms on the fine grid); "total" sums
all windows from 20 ms to 1 s, which is less sensitive to where bucket boundaries fall. The
placebo added ÷ cancelled ratio (swept side, 20–1000 ms) checks the flow accounting of each
emulated feed. Writes results/pooled/feedspeed.md and .parquet.

Usage: uv run python scripts/feedspeed.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from lobflow.robustness import STATS, match_within_day, prepare_subsets, subset_stats

BINS = ((3, 40), (40, 80), (80, 10**6))
# (label, exchange, tag, feed filter, netting interval in ms, split by levels cleared)
SETS = (
    ("Bybit, 20 ms feed", "bybit", "flowsfine", 20.0, 20, True),
    ("Bybit, emulated 52 ms", "bybit", "flowscoarse52", 20.0, 52, True),
    ("Bybit, emulated 100 ms", "bybit", "flowscoarse100", 20.0, 100, False),
    ("Bybit, emulated 200 ms", "bybit", "flowscoarse200", 20.0, 200, False),
    ("Binance, 52 ms feed", "binance-futures", "flowsfine", 60.0, 52, True),
)
SHOWN = ("transport_<250ms", "transport", "withdrawal_<250ms", "source_>250ms")
N_BOOT = 200


def placebo_kappa(p_flows: pl.DataFrame) -> float:
    """Added ÷ cancelled swept-side volume at placebo times, 20–1000 ms."""
    f = p_flows.filter((pl.col("side") == "swept") & (pl.col("window") != "0-20"))
    add = f.filter(pl.col("metric") == "add")["value"].sum()
    return float(add / f.filter(pl.col("metric") == "cancel")["value"].sum())


def _cell(r: dict[str, float], s: str) -> str:
    return f"{r[s]:.3f} [{r[s + '_lo']:.3f}, {r[s + '_hi']:.3f}]"


def main() -> None:
    rows = []
    for label, exchange, tag, push, feed_ms, split in SETS:
        d = Path("data/events") / exchange / "BTCUSDT"
        if not any(d.glob(f"*_{tag}.parquet")):
            print(f"skip {label}: no {tag} files")
            continue
        si = prepare_subsets(d, tag=tag, max_push_ms=push)
        pk = placebo_kappa(si.p_flows)
        groups = [("all", pl.lit(True))]
        if split:
            groups += [
                (
                    f"{lo}-{hi if hi < 10**6 else '+'}",
                    (pl.col("L_gap") >= lo) & (pl.col("L_gap") < hi),
                )
                for lo, hi in BINS
            ]
        for name, f in groups:
            cov = si.s_cov.join(si.s_info.select("event_id", "L_gap"), on="event_id").filter(f)
            w = match_within_day(cov, si.p_cov, method="nn", k=5)
            st = subset_stats(
                si.s_flows, si.s_info.filter(f), si.p_flows, si.p_info, w, si.windows,
                n_boot=N_BOOT, stats=(*STATS, "transport"),
            )  # fmt: skip
            rows.append(
                {
                    "set": label,
                    "feed_ms": feed_ms,
                    "venue": exchange,
                    "levels_cleared": name,
                    "sweeps": cov.height,
                    "placebo_kappa": pk,
                    **st,
                }
            )
    table = pl.DataFrame(rows)
    out = Path("results/pooled")
    out.mkdir(parents=True, exist_ok=True)
    table.write_parquet(out / "feedspeed.parquet")

    by_size = table.filter(pl.col("set").is_in([s[0] for s in SETS if s[5]]))
    curve = table.filter((pl.col("venue") == "bybit") & (pl.col("levels_cleared") == "all"))
    base = curve.filter(pl.col("feed_ms") == 20)
    lines = [
        "# Feed-speed emulation",
        "",
        "Excess (sweep − NN placebo) masses, fractions of pre-sweep swept depth, 95% day "
        f"bootstrap ({N_BOOT}). Emulated feeds: Bybit messages netted into fixed-clock buckets.",
        "",
        "## Repositioning by levels cleared",
        "",
        "| feed | levels cleared | sweeps | repositioning <250 | withdrawal <250 | new liq. >250 |",
        "|---|---|---|---|---|---|",
        *[
            f"| {r['set']} | {r['levels_cleared']} | {r['sweeps']} | "
            + " | ".join(_cell(r, s) for s in ("transport_<250ms", *SHOWN[2:]))
            + " |"
            for r in by_size.iter_rows(named=True)
        ],
        "",
        "## Feed-speed curve (Bybit BTCUSDT, all sweeps)",
        "",
        "| netting (ms) | placebo add/cancel | repositioning <250 | repositioning total | "
        "share of 20 ms (<250) | share of 20 ms (total) |",
        "|---|---|---|---|---|---|",
    ]
    if base.height:
        b250, btot = base["transport_<250ms"][0], base["transport"][0]
        for r in curve.sort("feed_ms").iter_rows(named=True):
            lines.append(
                f"| {r['feed_ms']} | {r['placebo_kappa']:.3f} | {_cell(r, 'transport_<250ms')} | "
                f"{_cell(r, 'transport')} | {r['transport_<250ms'] / b250:.2f} | "
                f"{r['transport'] / btot:.2f} |"
            )
        pos = curve.filter(pl.col("transport_<250ms") > 0).sort("feed_ms")
        if pos.height >= 2:
            # exponential decay in the netting interval: log mass linear in milliseconds
            ms = pos["feed_ms"].to_numpy().astype(float)
            slope, icpt = np.polyfit(ms, np.log(pos["transport_<250ms"].to_numpy()), 1)
            lines += [
                "",
                f"Exponential fit on positive points ({', '.join(map(str, pos['feed_ms']))} ms): "
                f"measured repositioning <250 falls by a factor e every {-1 / slope:.0f} ms of "
                f"netting; extrapolated to no netting: {np.exp(icpt):.3f} (20 ms observed "
                f"{b250:.3f}). Extrapolation is indicative only.",
            ]
    text = "\n".join(lines) + "\n"
    (out / "feedspeed.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
