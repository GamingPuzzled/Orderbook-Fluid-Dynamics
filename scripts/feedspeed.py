"""How much repositioning does a slower feed hide? (feed-speed emulation)

Compares excess repositioning on the three small-tick BTC books at their real feeds (tag
``flowsfine``: OKX 10 ms, Bybit 20 ms, Binance 52 ms) and with the OKX and Bybit book messages
netted into slower fixed-clock buckets (tags ``flowscoarse<ms>``; ``lobflow flows
--coarsen-ms <ms>``). Two outputs:

- by levels cleared (each venue at its own feed and at an emulated 52 ms): is Binance's weaker
  repositioning a feed and sweep-mix effect?
- the feed-speed curve per venue: how fast measured repositioning decays with the netting
  interval, and whether a feed faster than 20 ms (OKX) shows more.

"Before 250 ms" sums the windows that end by 250 ms (20–200 ms on the fine grid); "total" sums
all windows from 20 ms to 1 s, which is less sensitive to where bucket boundaries fall. The
placebo added ÷ cancelled ratio (swept side, 20–1000 ms) checks the flow accounting of each
emulated feed. Writes results/pooled/feedspeed.md and .parquet.

Usage: uv run python scripts/feedspeed.py
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from lobflow.robustness import STATS, match_within_day, prepare_subsets, subset_stats

BINS = ((3, 40), (40, 80), (80, 10**6))
# (label, exchange, symbol, tag, feed filter, netting interval in ms, split by levels cleared)
OKX = ("okex-swap", "BTC-USDT-SWAP")
BYBIT = ("bybit", "BTCUSDT")
SETS = (
    ("OKX, 10 ms feed", *OKX, "flowsfine", 110.0, 10, True),
    ("OKX, emulated 20 ms", *OKX, "flowscoarse20", 110.0, 20, False),
    ("OKX, emulated 52 ms", *OKX, "flowscoarse52", 110.0, 52, True),
    ("OKX, emulated 100 ms", *OKX, "flowscoarse100", 110.0, 100, False),
    ("Bybit, 20 ms feed", *BYBIT, "flowsfine", 20.0, 20, True),
    ("Bybit, emulated 52 ms", *BYBIT, "flowscoarse52", 20.0, 52, True),
    ("Bybit, emulated 100 ms", *BYBIT, "flowscoarse100", 20.0, 100, False),
    ("Bybit, emulated 200 ms", *BYBIT, "flowscoarse200", 20.0, 200, False),
    ("Binance, 52 ms feed", "binance-futures", "BTCUSDT", "flowsfine", 60.0, 52, True),
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
    for label, exchange, symbol, tag, push, feed_ms, split in SETS:
        d = Path("data/events") / exchange / symbol
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

    by_size = table.filter(pl.col("set").is_in([s[0] for s in SETS if s[6]]))
    lines = [
        "# Feed-speed emulation",
        "",
        "Excess (sweep − NN placebo) masses, fractions of pre-sweep swept depth, 95% day "
        f"bootstrap ({N_BOOT}). Emulated feeds: OKX or Bybit messages netted into fixed-clock "
        "buckets.",
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
    ]
    for venue in ("okex-swap", "bybit"):
        curve = table.filter((pl.col("venue") == venue) & (pl.col("levels_cleared") == "all"))
        if curve.height < 2:
            continue
        curve = curve.sort("feed_ms")
        b250, btot = curve["transport_<250ms"][0], curve["transport"][0]
        lines += [
            "",
            f"## Feed-speed curve ({venue} BTC, all sweeps; shares relative to the fastest feed)",
            "",
            "| netting (ms) | placebo add/cancel | repositioning <250 | repositioning total | "
            "share (<250) | share (total) |",
            "|---|---|---|---|---|---|",
            *[
                f"| {r['feed_ms']} | {r['placebo_kappa']:.3f} | {_cell(r, 'transport_<250ms')} | "
                f"{_cell(r, 'transport')} | {r['transport_<250ms'] / b250:.2f} | "
                f"{r['transport'] / btot:.2f} |"
                for r in curve.iter_rows(named=True)
            ],
        ]
    text = "\n".join(lines) + "\n"
    (out / "feedspeed.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
