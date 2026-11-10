"""Publication figures from results/ tables (PNG + PDF into figures/).

Fig 1  three-phase refill: withdrawal / transport / source rates vs time, per asset.
Fig 2  mass balance: added ÷ cancelled (κ) per window, sweeps vs state-matched placebo.
Fig 3  moving-frame recovery R(d, τ) heatmap (diverging around R = 1), per asset.
Fig 5  excess cost of a follow-up market order vs delay, sweeps − matched placebo.
Fig 6  parametric refill models (fitmodels) against observed excess flows.
PDFs are also copied to paper/figures/.

Usage: uv run python scripts/figures.py [--assets BTCUSDT,ETHUSDT] [--exchange bybit]
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.figure import Figure

# Reference palette (dataviz skill), light mode. Slots 1-3 validated all-pairs.
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
DIV_LOW, DIV_MID, DIV_HIGH = "#e34948", "#f0efec", "#2a78d6"  # depleted / pre level / surplus

COMPONENTS = (  # (column, label, colour, linestyle) - linestyle is the secondary encoding
    ("withdrawal", "Withdrawal", ORANGE, "--"),
    ("transport", "Repositioning", BLUE, "-"),
    ("source", "New liquidity", AQUA, ":"),
)


def _style() -> None:
    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": TEXT_2,
            "axes.labelcolor": TEXT,
            "axes.titlecolor": TEXT,
            "xtick.color": TEXT_2,
            "ytick.color": TEXT_2,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "font.size": 9,
            "axes.titlesize": 10,
            "legend.frameon": False,
            "lines.linewidth": 2.0,
        }
    )


def _save(fig: Figure, out: Path, name: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(out / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_phases(res: Path, assets: list[str], out: Path) -> None:
    fig, axes = plt.subplots(1, len(assets), figsize=(3.4 * len(assets), 2.8), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, sym in zip(axes, assets, strict=True):
        w = pl.read_parquet(res / sym / "model_windows_deep_d_gt_5.parquet").sort("t_lo")
        lo, hi = w["t_lo"].to_numpy(), w["t_hi"].to_numpy()
        for col, label, colour, ls in COMPONENTS:
            rate = w[col].to_numpy() / (hi - lo) * 100.0  # fraction of pre depth per 100 ms
            x = np.append(lo, hi[-1])
            y = np.append(rate, rate[-1])
            ax.step(x, y, where="post", color=colour, linestyle=ls, label=label)
            k = int(np.argmax(rate))
            ax.annotate(
                label,
                (0.5 * (lo[k] + hi[k]), rate[k]),
                xytext=(4, 4),
                textcoords="offset points",
                color=TEXT,
                fontsize=8,
            )
        ax.set_xscale("log")
        ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
        ax.set_xlim(20, 1000)
        ax.set_xticks(
            [20, 50, 100, 250, 500, 1000], labels=["20", "50", "100", "250", "500", "1000"]
        )
        ax.set_xlabel("time since sweep (ms)")
        ax.set_title(sym)
    top = max(ax.get_ylim()[1] for ax in axes)
    axes[0].set_ylim(top=top * 1.12)
    axes[0].set_ylabel("excess rate\n(fraction of pre-sweep depth per 100 ms)")
    axes[-1].legend(loc="upper right", fontsize=8)
    fig.suptitle("Refill after a sweep: withdrawal, then repositioning, then new liquidity", y=1.03)
    _save(fig, out, "fig1_three_phases")


def fig_kappa(res: Path, assets: list[str], out: Path) -> None:
    fig, axes = plt.subplots(1, len(assets), figsize=(3.4 * len(assets), 2.6), sharey=True)
    axes = np.atleast_1d(axes)
    order = ["20-40", "40-100", "100-250", "250-1000"]
    for ax, sym in zip(axes, assets, strict=True):
        t = pl.read_parquet(res / sym / "transport_test_matched.parquet")
        t = t.filter(pl.col("window").is_in(order))
        t = t.with_columns(
            pl.col("window")
            .replace_strict({w: i for i, w in enumerate(order)}, return_dtype=pl.Int64)
            .alias("i")
        ).sort("i")
        x = t["i"].to_numpy()
        k, klo, khi = (t[c].to_numpy() for c in ("kappa", "kappa_lo", "kappa_hi"))
        ax.axhline(1.0, color=TEXT_2, linewidth=0.8)
        ax.plot(
            x,
            t["kappa_placebo"].to_numpy(),
            color=TEXT_2,
            marker="o",
            markersize=7,
            markerfacecolor=SURFACE,
            linewidth=1.2,
            linestyle="--",
            label="Matched placebo",
        )
        ax.errorbar(
            x,
            k,
            yerr=[k - klo, khi - k],
            color=BLUE,
            marker="o",
            markersize=8,
            capsize=0,
            elinewidth=2,
            label="Sweeps (95% CI)",
        )
        ax.set_xticks(x, labels=[f"{w}" for w in order])
        ax.set_xlabel("window after sweep (ms)")
        ax.set_title(sym)
    axes[0].set_ylabel("added ÷ cancelled depth (κ)")
    axes[0].legend(loc="lower right", fontsize=8)
    fig.suptitle("Cancellations exceed additions early; new liquidity later", y=1.03)
    _save(fig, out, "fig2_mass_balance")


def fig_recovery(res: Path, assets: list[str], out: Path) -> None:
    cmap = LinearSegmentedColormap.from_list("div", [DIV_LOW, DIV_MID, DIV_HIGH])
    norm = TwoSlopeNorm(vmin=-2.5, vcenter=0.0, vmax=1.5)  # log2 R
    fig, axes = plt.subplots(1, len(assets), figsize=(3.6 * len(assets), 2.8), sharey=True)
    axes = np.atleast_1d(axes)
    im = None
    for ax, sym in zip(axes, assets, strict=True):
        r = pl.read_parquet(res / sym / "bucket_recovery.parquet").filter(pl.col("set") == "sweep")
        buckets = ["1", "2", "3-5", "6-10", "11-20", "21-50"]
        taus = sorted(r["tau_ms"].unique().to_list())
        grid = np.full((len(buckets), len(taus)), np.nan)
        for b, tau, val in r.select("bucket", "tau_ms", "R").iter_rows():
            if b in buckets:
                grid[buckets.index(b), taus.index(tau)] = val
        im = ax.imshow(np.log2(grid), cmap=cmap, norm=norm, aspect="auto", origin="lower")
        for i in range(len(buckets)):
            for j in range(len(taus)):
                v = grid[i, j]
                if np.isfinite(v):
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.5, color=TEXT)
        ax.set_xticks(range(len(taus)), labels=[str(t) for t in taus])
        ax.set_yticks(range(len(buckets)), labels=buckets)
        ax.set_xlabel("time since sweep (ms)")
        ax.set_title(sym)
        ax.grid(False)
    axes[0].set_ylabel("distance from opposite best (ticks)")
    assert im is not None
    cb = fig.colorbar(im, ax=list(axes), shrink=0.85, pad=0.02)
    ticks = np.array([0.25, 0.5, 1, 2])
    cb.set_ticks(np.log2(ticks).tolist(), labels=[f"{t:g}" for t in ticks])
    cb.set_label("depth ÷ pre-sweep depth (R)")
    cb.outline.set_visible(False)
    fig.suptitle("Book depth after a sweep, relative to the moving price", y=1.03)
    _save(fig, out, "fig3_recovery_heatmap")


def fig_execution(res: Path, assets: list[str], out: Path, q_mult: float = 0.1) -> None:
    fig, ax = plt.subplots(figsize=(4.6, 2.9))
    styles = ((BLUE, "-", "o"), (ORANGE, "--", "s"), (AQUA, ":", "^"))
    for sym, (colour, ls, marker) in zip(assets, styles, strict=False):
        p = res / sym / "execution.parquet"
        if not p.exists():
            continue
        e = (
            pl.read_parquet(p)
            .filter((pl.col("q_mult") == q_mult) & (pl.col("stat") == "cost_bps"))
            .filter(pl.col("tau_ms") > 0)
            .sort("tau_ms")
        )
        t = e["tau_ms"].to_numpy()
        ax.fill_between(t, e["diff_lo"].to_numpy(), e["diff_hi"].to_numpy(), color=colour,
                        alpha=0.15, linewidth=0)  # fmt: skip
        ax.plot(t, e["diff"].to_numpy(), color=colour, linestyle=ls, marker=marker,
                markersize=4, label=sym)  # fmt: skip
        ax.annotate(sym, (t[0], float(e["diff"][0])), xytext=(6, 2), textcoords="offset points",
                    color=TEXT, fontsize=8)  # fmt: skip
    ax.axhline(0, color=TEXT_2, linewidth=1)
    ax.set_xscale("log")
    ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    ax.set_xticks([20, 50, 100, 250, 500, 1000], labels=["20", "50", "100", "250", "500", "1000"])
    ax.set_xlim(18, 1100)
    ax.set_xlabel("delay after sweep (ms)")
    ax.set_ylabel("excess cost vs matched placebo (bps)")
    ax.legend(loc="upper right", fontsize=8)
    fig.suptitle(f"Follow-up market order of {q_mult:g} × typical depth", y=1.02)
    _save(fig, out, "fig5_execution")


def fig_fitmodels(res: Path, assets: list[str], out: Path) -> None:
    """Observed excess near build-up N and deep depletion J vs parametric fits."""
    fig, axes = plt.subplots(2, len(assets), figsize=(3.6 * len(assets), 5.0), sharex=True)
    axes = np.atleast_2d(axes).reshape(2, len(assets))
    fits = (("E", "three-phase (E)", BLUE, "--"), ("G", "three-phase + late withdrawal (G)",
            ORANGE, "-"), ("C", "no move phase (C)", AQUA, ":"))  # fmt: skip
    for col, sym in enumerate(assets):
        c = pl.read_parquet(res / sym / "fitmodels_curves.parquet")
        obs = c.filter(pl.col("model") == "obs").sort("t_lo")
        mid = np.sqrt(obs["t_lo"].to_numpy() * obs["t_hi"].to_numpy())
        width = obs["t_hi"].to_numpy() - obs["t_lo"].to_numpy()
        for row, (series, title) in enumerate((("N", "near build-up"), ("J", "deep depletion"))):
            ax = axes[row, col]
            ax.plot(mid, obs[series].to_numpy() / width * 100, "o", color=TEXT, markersize=4,
                    label="observed")  # fmt: skip
            for m, lab, colour, ls in fits:
                f = c.filter(pl.col("model") == m).sort("t_lo")
                ax.plot(mid, f[series].to_numpy() / width * 100, color=colour, linestyle=ls,
                        label=lab)  # fmt: skip
            ax.axhline(0, color=TEXT_2, linewidth=0.8)
            ax.set_xscale("log")
            ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
            ax.set_xticks([20, 50, 100, 250, 500, 1000], labels=["20", "50", "100", "250", "500",
                          "1000"])  # fmt: skip
            ax.set_title(f"{sym}: {title}")
            if col == 0:
                ax.set_ylabel("excess rate per 100 ms\n(fraction of pre depth)")
            if row == 1:
                ax.set_xlabel("time since sweep (ms)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("Parametric refill models against the data", y=1.01)
    _save(fig, out, "fig6_fitmodels")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="BTCUSDT,ETHUSDT")
    ap.add_argument("--exchange", default="bybit")
    ap.add_argument("--out", default="figures")
    ap.add_argument("--paper-figures", default="paper/figures")
    a = ap.parse_args()
    _style()
    res = Path("results") / a.exchange
    assets = a.assets.split(",")
    out = Path(a.out)
    fig_phases(res, assets, out)
    fig_kappa(res, assets, out)
    fig_recovery(res, assets, out)
    fig_execution(res, assets, out)
    if all((res / a / "fitmodels_curves.parquet").exists() for a in assets):
        fig_fitmodels(res, assets, out)
    paper = Path(a.paper_figures)
    paper.mkdir(parents=True, exist_ok=True)
    for f in out.glob("fig[12356]_*.pdf"):
        shutil.copy(f, paper / f.name)
    print(f"wrote figures to {out}/ and PDFs to {paper}/")


if __name__ == "__main__":
    main()
