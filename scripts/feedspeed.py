"""Is Binance's weaker repositioning a feed effect? (feed-speed emulation)

Compares excess repositioning before 250 ms, by levels cleared, for Bybit BTCUSDT at its real
20 ms feed (tag ``flowsfine``), Bybit BTCUSDT with its book messages netted into 52 ms buckets
(tag ``flowscoarse52``; ``lobflow flows --coarsen-ms 52``), and Binance BTCUSDT (52 ms feed).
Writes results/pooled/feedspeed.md and .parquet.

Usage: uv run python scripts/feedspeed.py
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from lobflow.robustness import match_within_day, prepare_subsets, subset_stats

BINS = ((3, 40), (40, 80), (80, 10**6))
SETS = (
    ("Bybit, 20 ms feed", "bybit", "flowsfine", 20.0),
    ("Bybit, emulated 52 ms", "bybit", "flowscoarse52", 20.0),
    ("Binance, 52 ms feed", "binance-futures", "flowsfine", 60.0),
)
STATS = ("transport_<250ms", "withdrawal_<250ms", "source_>250ms")


def main() -> None:
    rows = []
    for label, exchange, tag, push in SETS:
        si = prepare_subsets(Path("data/events") / exchange / "BTCUSDT", tag=tag, max_push_ms=push)
        groups = [("all", pl.lit(True))] + [
            (f"{lo}-{hi if hi < 10**6 else '+'}", (pl.col("L_gap") >= lo) & (pl.col("L_gap") < hi))
            for lo, hi in BINS
        ]
        for name, f in groups:
            cov = si.s_cov.join(si.s_info.select("event_id", "L_gap"), on="event_id").filter(f)
            w = match_within_day(cov, si.p_cov, method="nn", k=5)
            st = subset_stats(
                si.s_flows, si.s_info.filter(f), si.p_flows, si.p_info, w, si.windows, n_boot=200
            )
            rows.append({"set": label, "levels_cleared": name, "sweeps": cov.height, **st})
    table = pl.DataFrame(rows)
    out = Path("results/pooled")
    out.mkdir(parents=True, exist_ok=True)
    table.write_parquet(out / "feedspeed.parquet")
    lines = [
        "# Feed-speed emulation: repositioning by levels cleared",
        "",
        "Excess (sweep − NN placebo) masses before/after 250 ms, fractions of pre-sweep swept "
        "depth, 95% day bootstrap. Bybit 52 ms: Bybit messages netted into 52 ms buckets.",
        "",
        "| feed | levels cleared | sweeps | repositioning <250 | withdrawal <250 | new liq. >250 |",
        "|---|---|---|---|---|---|",
    ]
    for r in table.iter_rows(named=True):
        cells = [f"{r[s]:.3f} [{r[s + '_lo']:.3f}, {r[s + '_hi']:.3f}]" for s in STATS]
        lines.append(
            f"| {r['set']} | {r['levels_cleared']} | {r['sweeps']} | " + " | ".join(cells) + " |"
        )
    (out / "feedspeed.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
