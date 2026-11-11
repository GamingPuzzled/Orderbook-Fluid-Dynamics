"""Cross-asset / cross-venue summary of the three-phase refill.

Discovers every results/<exchange>/<symbol>/ that has the model and robustness outputs and
writes, for all of them at once:

- paper/tables/crossasset.tex : days, sweeps, relative tick size (bp), κ(20–40), repositioning
  share (<250 ms), phase centroids, switch time, PDE R² gain from diffusion, execution excess
  left at 250 ms ("cens." when more than 20% of follow-up walks still exhaust the 50-tick
  profile at 250 ms);
- figures/fig4_cross_asset.{png,pdf} (+ paper/figures copy): forest plot of κ(20–40) and the
  repositioning share, and the three phase centroids per asset.

Rows missing an optional input (PDE, execution) show "--". New coins and venues appear
automatically once their pipeline has run.

Usage: uv run python scripts/crossasset.py [--results results]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.ticker import NullFormatter

sys.path.insert(0, str(Path(__file__).parent))
from figures import AQUA, BLUE, ORANGE, TEXT_2, _save, _style  # noqa: E402

VENUES = {"bybit": "Bybit", "binance-futures": "Binance", "okex-swap": "OKX"}
MAIN_ORDER = ("BTC", "ETH", "SOL", "XRP", "LINK")
MAX_SHORT = 0.2  # execution excess is censored if more walks than this run out of depth


@dataclass(frozen=True)
class Row:
    venue: str
    symbol: str
    stats: dict[str, tuple[float, float, float]]  # name -> (value, lo, hi)
    n_days: int
    n_sweeps: int
    pde_gain: float | None
    exec_left: float | None
    exec_censored: bool
    tick_bp: float | None


def discover(results: Path) -> list[tuple[str, str]]:
    found = []
    for d in sorted(results.glob("*/*")):
        if (d / "model_summary_deep_d_gt_5.parquet").exists() and (
            d / "robustness.parquet"
        ).exists():
            found.append((d.parent.name, d.name))

    def key(es: tuple[str, str]) -> tuple[int, int, str]:
        e, s = es
        base = next((i for i, b in enumerate(MAIN_ORDER) if s.upper().startswith(b)), 99)
        return (list(VENUES).index(e) if e in VENUES else 99, base, s)

    return sorted(found, key=key)


def tick_bp(d: Path) -> float | None:
    """Median tick relative to the pre-sweep mid (bp), over the analysed sweeps (zonewidth)."""
    f = d / "zonewidth.parquet"
    if not f.exists():
        return None
    r = pl.read_parquet(f).row(0, named=True)
    return float(r["near_max_bp"] / r["near_max_ticks"])


def load_row(results: Path, exchange: str, symbol: str) -> Row:
    d = results / exchange / symbol
    ms = pl.read_parquet(d / "model_summary_deep_d_gt_5.parquet")
    stats = {s: (v, lo, hi) for s, v, lo, hi in ms.iter_rows()}
    rb = pl.read_parquet(d / "robustness.parquet").filter(
        (pl.col("group") == "matching") & (pl.col("subset") == "NN")
    )
    r = rb.row(0, named=True)
    stats["kappa_20-40"] = (r["kappa_20-40"], r["kappa_20-40_lo"], r["kappa_20-40_hi"])
    pde_gain = None
    if (d / "pde_oos.parquet").exists():
        oos = pl.read_parquet(d / "pde_oos.parquet")
        r2 = oos.group_by("model").agg((1 - pl.col("sse").sum() / pl.col("ss0").sum()).alias("r2"))
        get = {m: v for m, v in r2.iter_rows()}
        pde_gain = get["local"] - get["common"]
    exec_left, exec_censored = None, False
    if (d / "execution.parquet").exists():
        ex = pl.read_parquet(d / "execution.parquet").filter(
            (pl.col("q_mult") == 0.1) & (pl.col("stat") == "cost_bps")
        )
        e20 = ex.filter(pl.col("tau_ms") == 20)["diff"]
        e250 = ex.filter(pl.col("tau_ms") == 250)["diff"]
        short = pl.read_parquet(d / "execution.parquet").filter(
            (pl.col("q_mult") == 0.1) & (pl.col("stat") == "short") & (pl.col("tau_ms") == 250)
        )["sweep"]
        exec_censored = bool(len(short) and short[0] > MAX_SHORT)
        if len(e20) and len(e250) and e20[0] > 0:
            exec_left = float(e250[0] / e20[0])
    return Row(
        VENUES.get(exchange, exchange),
        symbol,
        stats,
        int(r["n_days"]),
        int(r["n_sweeps"]),
        pde_gain,
        exec_left,
        exec_censored,
        tick_bp(d),
    )


def _ci(v: tuple[float, float, float], digits: int) -> str:
    val, lo, hi = v
    head = "--" if np.isnan(val) else f"{val:.{digits}f}"
    return f"{head} {{\\scriptsize[{lo:.{digits}f}, {hi:.{digits}f}]}}"


def _switch(v: tuple[float, float, float]) -> str:
    val, lo, hi = v
    if np.isnan(lo) or np.isnan(hi):
        return "--"
    if not np.isnan(val):
        return f"{val:.0f} {{\\scriptsize[{lo:.0f}, {hi:.0f}]}}"
    return f"{lo:.0f}--{hi:.0f}"


def _ms(v: float) -> str:
    return "--" if np.isnan(v) else f"{v:.0f}"


def _exec(r: Row) -> str:
    if r.exec_censored:
        return "cens."
    return "--" if r.exec_left is None else f"{r.exec_left:.2f}"


def table(rows: list[Row], out: Path) -> None:
    head = (
        "Venue & Asset & Days & Sweeps & Tick (bp) & $\\kappa_{20\\text{--}40}$ & Repos.\\ share & "
        "$\\bar t_{\\mathrm{W}}$ & $\\bar t_{\\mathrm{R}}$ & $\\bar t_{\\mathrm{S}}$ & "
        "Switch & $\\Delta R^2_{\\mathrm{diff}}$ & Exec.\\ left \\\\"
    )
    lines = ["\\begin{tabular}{llrrrcccccccc}", "\\toprule", head, "\\midrule"]
    for r in rows:
        s = r.stats
        cells = [
            r.venue,
            r.symbol,
            str(r.n_days),
            f"{r.n_sweeps:,}".replace(",", "{,}"),
            "--" if r.tick_bp is None else f"{r.tick_bp:.3f}",
            _ci(s["kappa_20-40"], 2),
            _ci(s["transport_share_<250ms"], 2),
            _ms(s["withdrawal_centroid_ms"][0]),
            _ms(s["transport_centroid_ms"][0]),
            _ms(s["source_centroid_ms"][0]),
            _switch(s["t_switch_ms"]),
            "--" if r.pde_gain is None else f"{r.pde_gain:+.3f}",
            _exec(r),
        ]
        lines.append(" & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "crossasset.tex").write_text("\n".join(lines) + "\n")


def figure(rows: list[Row], out: Path, paper_out: Path) -> None:
    labels = [f"{r.venue} {r.symbol}" for r in rows]
    y = np.arange(len(rows))[::-1]
    fig, axes = plt.subplots(
        1, 3, figsize=(9.6, 0.5 * len(rows) + 1.6), sharey=True, width_ratios=[1, 1, 1.4]
    )
    for ax, stat, title, ref in (
        (axes[0], "kappa_20-40", "added ÷ cancelled, 20–40 ms", 1.0),
        (axes[1], "transport_share_<250ms", "repositioning share, < 250 ms", None),
    ):
        v = np.array([r.stats[stat] for r in rows])
        ax.errorbar(
            v[:, 0], y, xerr=[v[:, 0] - v[:, 1], v[:, 2] - v[:, 0]], fmt="o", color=BLUE,
            ecolor=BLUE, elinewidth=1.5, capsize=0, markersize=6,
        )  # fmt: skip
        if ref is not None:
            ax.axvline(ref, color=TEXT_2, linewidth=1, linestyle="--")
            ax.annotate("placebo ≈ 1", (ref, y.max() + 0.45), ha="right", fontsize=8, color=TEXT_2)
        ax.set_title(title)
    ax = axes[2]
    for key, label, colour, marker in (
        ("withdrawal_centroid_ms", "Withdrawal", ORANGE, "s"),
        ("transport_centroid_ms", "Repositioning", BLUE, "o"),
        ("source_centroid_ms", "New liquidity", AQUA, "^"),
    ):
        v = np.array([r.stats[key] for r in rows])
        ax.errorbar(
            v[:, 0], y, xerr=[v[:, 0] - v[:, 1], v[:, 2] - v[:, 0]], fmt=marker, color=colour,
            ecolor=colour, elinewidth=1.2, capsize=0, markersize=6, label=label,
        )  # fmt: skip
    ax.set_xscale("log")
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([20, 50, 100, 250, 500, 1000], labels=["20", "50", "100", "250", "500", "1000"])
    ax.set_xlim(20, 1000)
    ax.set_title("phase centroid (ms after sweep)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, fontsize=8)
    axes[0].set_yticks(y, labels=labels)
    axes[0].set_ylim(-0.6, y.max() + 0.8)
    for a in axes:
        a.grid(axis="y", visible=False)
    fig.suptitle("The three-phase refill across assets and venues (95% CIs)", y=1.06)
    _save(fig, out, "fig4_cross_asset")
    paper_out.mkdir(parents=True, exist_ok=True)
    shutil.copy(out / "fig4_cross_asset.pdf", paper_out / "fig4_cross_asset.pdf")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--tables", default="paper/tables")
    ap.add_argument("--figures", default="figures")
    ap.add_argument("--paper-figures", default="paper/figures")
    a = ap.parse_args()
    res = Path(a.results)
    rows = [load_row(res, e, s) for e, s in discover(res)]
    if not rows:
        raise SystemExit("no complete results found")
    _style()
    table(rows, Path(a.tables))
    figure(rows, Path(a.figures), Path(a.paper_figures))
    print("assets:", ", ".join(f"{r.venue} {r.symbol}" for r in rows))


if __name__ == "__main__":
    main()
