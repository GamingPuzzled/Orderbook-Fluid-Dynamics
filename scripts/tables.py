"""LaTeX tables generated from results/ (so the paper never carries hand-copied numbers).

Writes paper/tables/robustness.tex (subset robustness of the three-phase refill) and
paper/tables/execution.tex (follow-up market-order cost), both assets.

Usage: uv run python scripts/tables.py [--assets BTCUSDT,ETHUSDT] [--exchange bybit]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

COLS = (  # (stat, digits)
    ("kappa_20-40", 2),
    ("withdrawal_<250ms", 2),
    ("transport_<250ms", 2),
    ("transport_share_<250ms", 2),
)
ORDER = [
    ("matching", "CEM", "All sweeps, CEM placebo"),
    ("matching", "NN", "All sweeps, NN placebo"),
    ("levels cleared (day tercile)", "smallest third", "Levels cleared: smallest third"),
    ("levels cleared (day tercile)", "middle third", "Levels cleared: middle third"),
    ("levels cleared (day tercile)", "largest third", "Levels cleared: largest third"),
    ("sweep volume", "below day median", "Volume below day median"),
    ("sweep volume", "above day median", "Volume above day median"),
    ("side", "buy sweeps (ask side)", "Buy sweeps (ask side)"),
    ("side", "sell sweeps (bid side)", "Sell sweeps (bid side)"),
    ("time of day (UTC)", "00-08", "00--08 UTC"),
    ("time of day (UTC)", "08-16", "08--16 UTC"),
    ("time of day (UTC)", "16-24", "16--24 UTC"),
]
RULE_AFTER = {"NN", "largest third", "above day median", "sell sweeps (bid side)"}


def cell(r: dict[str, float], stat: str, digits: int) -> str:
    v, lo, hi = r[stat], r[f"{stat}_lo"], r[f"{stat}_hi"]
    return f"{v:.{digits}f} {{\\scriptsize[{lo:.{digits}f}, {hi:.{digits}f}]}}"


def robustness(res: Path, assets: list[str], out: Path) -> None:
    tabs = {a: pl.read_parquet(res / a / "robustness.parquet") for a in assets}
    n_cols = len(COLS)
    head = " & ".join(f"\\multicolumn{{{n_cols}}}{{c}}{{{a}}}" for a in assets)
    sub = " & ".join(
        "$\\kappa_{20\\text{--}40}$ & Withdr. & Repos. & Repos.\\ share" for _ in assets
    )
    rules = "".join(
        f"\\cmidrule(lr){{{2 + i * n_cols}-{1 + (i + 1) * n_cols}}}" for i in range(len(assets))
    )
    lines = [
        f"\\begin{{tabular}}{{l{'c' * n_cols * len(assets)}}}",
        "\\toprule",
        f" & {head} \\\\",
        rules,
        f"Subset & {sub} \\\\",
        "\\midrule",
    ]
    for group, subset, label in ORDER:
        cells = []
        for a in assets:
            r = (
                tabs[a]
                .filter(pl.col("group") == group, pl.col("subset") == subset)
                .row(0, named=True)
            )
            cells += [cell(r, s, d) for s, d in COLS]
        lines.append(f"{label} & " + " & ".join(cells) + " \\\\")
        if subset in RULE_AFTER:
            lines.append("\\addlinespace")
    lines += ["\\bottomrule", "\\end{tabular}"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "robustness.tex").write_text("\n".join(lines) + "\n")


def execution(res: Path, assets: list[str], out: Path, q_mult: float = 0.1) -> None:
    """Follow-up cost by delay for Q = ``q_mult`` × median placebo depth."""
    tabs = {
        a: pl.read_parquet(res / a / "execution.parquet").filter(
            (pl.col("q_mult") == q_mult) & (pl.col("stat") == "cost_bps")
        )
        for a in assets
    }
    head = " & ".join(f"\\multicolumn{{4}}{{c}}{{{a}}}" for a in assets)
    sub = " & ".join("Sweep & Placebo & Excess & Left" for _ in assets)
    rules = "".join(f"\\cmidrule(lr){{{2 + i * 4}-{1 + (i + 1) * 4}}}" for i in range(len(assets)))
    lines = [
        f"\\begin{{tabular}}{{r{'c' * 4 * len(assets)}}}",
        "\\toprule",
        f" & {head} \\\\",
        rules,
        f"$\\tau$ (ms) & {sub} \\\\",
        "\\midrule",
    ]
    taus = tabs[assets[0]]["tau_ms"].sort().to_list()
    for t in taus:
        cells = []
        for a in assets:
            df = tabs[a]
            r = df.filter(pl.col("tau_ms") == t).row(0, named=True)
            ex20 = float(df.filter(pl.col("tau_ms") == 20)["diff"][0])
            left = "" if t < 0 else f"{r['diff'] / ex20:.2f}"
            cells += [
                f"{r['sweep']:.3f}",
                f"{r['placebo']:.3f}",
                f"{r['diff']:+.3f} {{\\scriptsize[{r['diff_lo']:+.3f}, {r['diff_hi']:+.3f}]}}",
                left,
            ]
        label = "pre" if t < 0 else str(t)
        lines.append(f"{label} & " + " & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "execution.tex").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="BTCUSDT,ETHUSDT")
    ap.add_argument("--exchange", default="bybit")
    ap.add_argument("--out", default="paper/tables")
    a = ap.parse_args()
    robustness(Path("results") / a.exchange, a.assets.split(","), Path(a.out))
    execution(Path("results") / a.exchange, a.assets.split(","), Path(a.out))
    print(f"wrote {a.out}/robustness.tex, {a.out}/execution.tex")


if __name__ == "__main__":
    main()
