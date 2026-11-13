"""LaTeX tables generated from results/ (so the paper never carries hand-copied numbers).

Writes paper/tables/robustness.tex (subset robustness of the three-phase refill) and
paper/tables/execution.tex (follow-up market-order cost) and paper/tables/pde.tex
(out-of-sample continuum model fits), plus sample.tex, kappa.tex and phases.tex; both assets.

Usage: uv run python scripts/tables.py [--assets BTCUSDT,ETHUSDT] [--exchange bybit]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
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


PDE_ROWS = (
    ("common", "Common (cancellation + source)"),
    ("local", "+ local (diffusion + drift)"),
    ("nonlocal", "+ non-local jump"),
    ("both", "+ both"),
)


def pde(res: Path, assets: list[str], out: Path) -> None:
    """Pooled out-of-sample R² per model, with the range across folds."""

    def r2(df: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
        return df.group_by(keys).agg((1 - pl.col("sse").sum() / pl.col("ss0").sum()).alias("r2"))

    cells: dict[str, dict[str, str]] = {}
    for a in assets:
        oos = pl.read_parquet(res / a / "pde_oos.parquet")
        tot = {m: v for m, v in r2(oos, ["model"]).iter_rows()}
        fold = (
            r2(oos, ["model", "fold"])
            .group_by("model")
            .agg(pl.col("r2").min().alias("lo"), pl.col("r2").max().alias("hi"))
        )
        rng = {m: (lo, hi) for m, lo, hi in fold.iter_rows()}
        cells[a] = {m: f"{tot[m]:.3f} [{rng[m][0]:.3f}, {rng[m][1]:.3f}]" for m, _ in PDE_ROWS}
    lines = [
        f"\\begin{{tabular}}{{l{'c' * len(assets)}}}",
        "\\toprule",
        "Model & " + " & ".join(assets) + " \\\\",
        "\\midrule",
        *[
            f"{label} & " + " & ".join(cells[a][m] for a in assets) + " \\\\"
            for m, label in PDE_ROWS
        ],
        "\\bottomrule",
        "\\end{tabular}",
    ]
    out.mkdir(parents=True, exist_ok=True)
    (out / "pde.tex").write_text("\n".join(lines) + "\n")


def _rows_tex(head: str, rows: list[str], cols: str) -> str:
    return "\n".join(
        [f"\\begin{{tabular}}{{{cols}}}", "\\toprule", head, "\\midrule", *rows, "\\bottomrule",
         "\\end{tabular}"]
    ) + "\n"  # fmt: skip


def _thou(v: int) -> str:
    return f"{v:,}".replace(",", "{,}")


def sample(res: Path, assets: list[str], out: Path) -> None:
    """Days, detected sweeps, clean sweeps and placebo times (parsed from summary.md)."""
    import re

    rows = []
    for a in assets:
        txt = (res / a / "summary.md").read_text()
        m = re.search(
            r"Days used: (\d+) of \d+.*?Sweeps: (\d+) detected, (\d+) with cleared.*?"
            r"Placebo times: (\d+)",
            txt,
            re.S,
        )
        if m is None:
            raise ValueError(f"sample line not found in {a}/summary.md")
        d, n, c, p = (int(x) for x in m.groups())
        rows.append(f"{a} & {d} & {_thou(n)} & {_thou(c)} & {_thou(p)} \\\\")
    head = " & Days & Sweeps & Clean sweeps & Placebo times \\\\"
    (out / "sample.tex").write_text(_rows_tex(head, rows, "lrrrr"))


KAPPA_WINDOWS = ("20-40", "40-100", "100-250", "250-1000")


def kappa(res: Path, assets: list[str], out: Path) -> None:
    """κ by window, sweeps (95% CI) and matched placebo."""
    tabs = {a: pl.read_parquet(res / a / "transport_test_matched.parquet") for a in assets}
    rows = []
    for w in KAPPA_WINDOWS:
        cells = []
        for a in assets:
            r = tabs[a].filter(pl.col("window") == w).row(0, named=True)
            cells += [
                f"{r['kappa']:.2f} [{r['kappa_lo']:.2f}, {r['kappa_hi']:.2f}]",
                f"{r['kappa_placebo']:.2f}",
            ]
        rows.append(f"{w.replace('-', '--')} & " + " & ".join(cells) + " \\\\")
    head = (
        " & " + " & ".join(f"\\multicolumn{{2}}{{c}}{{{a}}}" for a in assets) + " \\\\\n"
        + "".join(f"\\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}" for i in range(len(assets)))
        + "\nWindow (ms) & " + " & ".join("Sweeps & Placebo" for _ in assets) + " \\\\"
    )  # fmt: skip
    (out / "kappa.tex").write_text(_rows_tex(head, rows, "l" + "cc" * len(assets)))


PHASE_ROWS = (  # (stat, label, digits, with CI)
    ("withdrawal_<250ms", "Withdrawal, $<250$\\,ms", 2, True),
    ("transport_<250ms", "Repositioning, $<250$\\,ms", 2, True),
    ("source_<250ms", "Source, $<250$\\,ms", 2, True),
    ("source_>250ms", "Source, $>250$\\,ms", 2, True),
    ("transport_share_<250ms", "Repositioning share of near-touch build-up, $<250$\\,ms", 2, True),
    ("withdrawal_centroid_ms", "Centroid: withdrawal (ms)", 0, False),
    ("transport_centroid_ms", "Centroid: repositioning (ms)", 0, False),
    ("source_centroid_ms", "Centroid: source (ms)", 0, False),
)


def phases(res: Path, assets: list[str], out: Path) -> None:
    """Three-component decomposition, deep book d > 5."""
    tabs = {
        a: {s: (v, lo, hi) for s, v, lo, hi in
            pl.read_parquet(res / a / "model_summary_deep_d_gt_5.parquet").iter_rows()}
        for a in assets
    }  # fmt: skip
    rows = []
    for stat, label, dg, ci in PHASE_ROWS:
        cells = []
        for a in assets:
            v, lo, hi = tabs[a][stat]
            cells.append(f"{v:.{dg}f} [{lo:.{dg}f}, {hi:.{dg}f}]" if ci else f"{v:.{dg}f}")
        rows.append(f"{label} & " + " & ".join(cells) + " \\\\")
    head = " & " + " & ".join(assets) + " \\\\"
    (out / "phases.tex").write_text(_rows_tex(head, rows, "l" + "c" * len(assets)))


def fitmodels(res: Path, assets: list[str], out: Path) -> None:
    """Parametric model comparison: parameters, out-of-sample R² and ΔAIC per asset."""
    tabs = {a: pl.read_parquet(res / a / "fitmodels_scores.parquet") for a in assets}
    first = tabs[assets[0]]
    rows = []
    for r in first.iter_rows(named=True):
        bench = bool(np.isnan(r["aic"]))  # non-parametric benchmark: no p, no AIC
        cells = [r["model"], r["label"], "--" if bench else str(r["n_params"])]
        for a in assets:
            t = tabs[a]
            row = t.filter(pl.col("model") == r["model"]).row(0, named=True)
            d_aic = "--" if bench else f"{row['aic'] - float(np.nanmin(t['aic'].to_numpy())):.1f}"
            cells += [f"{row['cv_r2']:.3f}", d_aic]
        rows.append(" & ".join(cells) + " \\\\")
    head = (
        " & & & " + " & ".join(f"\\multicolumn{{2}}{{c}}{{{a}}}" for a in assets) + " \\\\\n"
        + "".join(f"\\cmidrule(lr){{{4 + 2 * i}-{5 + 2 * i}}}" for i in range(len(assets)))
        + "\nModel & Rates & $p$ & " + " & ".join("CV $R^2$ & $\\Delta$AIC" for _ in assets)
        + " \\\\"
    )  # fmt: skip
    (out / "fitmodels.tex").write_text(_rows_tex(head, rows, "cl" + "c" * (1 + 2 * len(assets))))


INFO_STATS = {
    "kappa_20-40": "$\\kappa$, 20--40\\,ms",
    "withdrawal_<250ms": "Withdrawal, $<$250\\,ms",
    "transport_<250ms": "Repositioning, $<$250\\,ms",
    "source_>250ms": "New liquidity, $>$250\\,ms",
}
INFO_POOLS = ("all placebo times", "placebo, same drift tercile")


def information(res: Path, assets: list[str], out: Path) -> None:
    """Continuation − reversal sweeps (5 s drift terciles), paired day-bootstrap CIs."""
    tabs = {a: pl.read_parquet(res / a / "information_diff.parquet") for a in assets}
    rows = []
    for stat, label in INFO_STATS.items():
        cells = [label]
        for a in assets:
            for pool in INFO_POOLS:
                r = tabs[a].filter(pl.col("stat") == stat, pl.col("placebo_pool") == pool)
                r0 = r.row(0, named=True)
                txt = f"{r0['diff']:+.3f} [{r0['lo']:+.3f}, {r0['hi']:+.3f}]"
                cells.append(txt.replace("-", "$-$").replace("+", "$+$"))
        rows.append(" & ".join(cells) + " \\\\")
    head = (
        " & " + " & ".join(f"\\multicolumn{{2}}{{c}}{{{a}}}" for a in assets) + " \\\\\n"
        + "".join(f"\\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}" for i in range(len(assets)))
        + "\nStatistic & " + " & ".join("all placebo & same-drift placebo" for _ in assets)
        + " \\\\"
    )  # fmt: skip
    (out / "information.tex").write_text(_rows_tex(head, rows, "l" + "c" * (2 * len(assets))))


ZONE_ORDER = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "LINKUSDT")


def zonewidth(res: Path, out: Path) -> None:
    """Repositioning (<250 ms) by near-zone width, every asset with ``zonewidth.parquet``."""
    found = [a for a in ZONE_ORDER if (res / a / "zonewidth.parquet").exists()]
    if not found:
        return
    tabs = {a: pl.read_parquet(res / a / "zonewidth.parquet").sort("near_max_ticks") for a in found}
    cuts = tabs[found[0]]["near_max_ticks"].to_list()
    rows = []
    for a in found:
        cells = [a]
        for r in tabs[a].iter_rows(named=True):
            v, lo, hi = (r[f"transport_<250ms{x}"] for x in ("", "_lo", "_hi"))
            cells.append(
                f"{v:.3f} {{\\scriptsize[{lo:.3f}, {hi:.3f}]}} "
                f"{{\\scriptsize({r['near_max_bp']:.2f}\\,bp)}}"
            )
        rows.append(" & ".join(cells) + " \\\\")
    head = "Asset & " + " & ".join(f"$d \\le {c}$" for c in cuts) + " \\\\"
    (out / "zonewidth.tex").write_text(_rows_tex(head, rows, "l" + "c" * len(cuts)))


def hazard(out: Path) -> None:
    """Near-touch cancellation rate at placebo times (results/pooled/hazard.parquet)."""
    f = Path("results/pooled/hazard.parquet")
    if not f.exists():
        return
    venues = {"bybit": "Bybit", "binance-futures": "Binance"}
    rows = [
        f"{venues.get(r['exchange'], r['exchange'])} & {r['symbol']} & {r['days']} & "
        f"{r['cancel_rate']:.2f} {{\\scriptsize[{r['lo']:.2f}, {r['hi']:.2f}]}} \\\\"
        for r in pl.read_parquet(f).iter_rows(named=True)
    ]
    head = "Venue & Asset & Days & Cancelled per second \\\\"
    (out / "hazard.tex").write_text(_rows_tex(head, rows, "llrc"))


def feedspeed(out: Path) -> None:
    """Repositioning by levels cleared and feed speed (results/pooled/feedspeed.parquet)."""
    f = Path("results/pooled/feedspeed.parquet")
    if not f.exists():
        return
    tab = pl.read_parquet(f)
    groups = tab["levels_cleared"].unique(maintain_order=True).to_list()
    # rows split by levels cleared only (the feed-speed curve is reported in the text)
    split = tab.group_by("set", maintain_order=True).agg(pl.len()).filter(pl.col("len") > 1)
    rows = []
    for name in split["set"].to_list():
        cells = [name]
        for g in groups:
            r = tab.filter((pl.col("set") == name) & (pl.col("levels_cleared") == g)).row(
                0, named=True
            )
            v, lo, hi = (r[f"transport_<250ms{x}"] for x in ("", "_lo", "_hi"))
            cells.append(f"{v:.3f} {{\\scriptsize[{lo:.3f}, {hi:.3f}]}}")
        rows.append(" & ".join(cells) + " \\\\")

    def label(g: str) -> str:
        if g == "all":
            return "All sweeps"
        lo, hi = g.split("-")
        return f"$\\geq {lo}$ levels" if hi == "+" else f"{lo}--{hi} levels"

    head = "Feed & " + " & ".join(label(g) for g in groups) + " \\\\"
    (out / "feedspeed.tex").write_text(_rows_tex(head, rows, "l" + "c" * len(groups)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="BTCUSDT,ETHUSDT")
    ap.add_argument("--exchange", default="bybit")
    ap.add_argument("--out", default="paper/tables")
    a = ap.parse_args()
    robustness(Path("results") / a.exchange, a.assets.split(","), Path(a.out))
    execution(Path("results") / a.exchange, a.assets.split(","), Path(a.out))
    for fn in (pde, sample, kappa, phases, fitmodels, information):
        fn(Path("results") / a.exchange, a.assets.split(","), Path(a.out))
    zonewidth(Path("results") / a.exchange, Path(a.out))
    hazard(Path(a.out))
    feedspeed(Path(a.out))
    print(f"wrote {a.out}/: all tables")


if __name__ == "__main__":
    main()
