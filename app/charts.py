"""Matplotlib charts in QuantSeras dark theme → base64 PNG for embedding."""
from __future__ import annotations
import base64
from io import BytesIO
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from app.schemas import PortfolioMetrics

# QuantSeras palette
BG = "#121212"
SURFACE = "#1D1D1D"
PRIMARY = "#69F0AE"
SECONDARY = "#03DAC6"
PROFIT = "#00E676"
LOSS = "#FF5252"
NEUTRAL = "#B0BEC5"
TEXT_HIGH = "#FFFFFF"
TEXT_MED = "#BDBDBD"
GRID = "#2C2C2C"


def _style_axes(ax):
    ax.set_facecolor(SURFACE)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.tick_params(colors=TEXT_MED, labelsize=9)
    ax.title.set_color(TEXT_HIGH)
    ax.xaxis.label.set_color(TEXT_MED)
    ax.yaxis.label.set_color(TEXT_MED)
    ax.grid(True, color=GRID, linewidth=0.6)


def _fig_to_b64(fig) -> str:
    buf = BytesIO()
    fig.patch.set_facecolor(BG)
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def pie_allocation(alloc: dict[str, float], title: str = "Asset allocation") -> str:
    alloc = {k: v for k, v in alloc.items() if v > 0}
    if not alloc:
        return ""
    items = sorted(alloc.items(), key=lambda x: -x[1])
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    colors = [PRIMARY, SECONDARY, "#FFB74D", "#81D4FA", "#F48FB1", "#CE93D8", "#A5D6A7", "#FFCC80", "#B0BEC5", "#E6EE9C"]
    colors = (colors * ((len(items) // len(colors)) + 1))[:len(items)]

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct="%1.1f%%",
        wedgeprops={"edgecolor": BG, "linewidth": 1.5},
        textprops={"color": TEXT_HIGH, "fontsize": 10},
    )
    for t in autotexts:
        t.set_color("#000000")
        t.set_fontweight("bold")
    ax.set_title(title, color=TEXT_HIGH, fontsize=13, fontweight="600", pad=14)
    fig.patch.set_facecolor(BG)
    return _fig_to_b64(fig)


def bar_pnl(metrics: PortfolioMetrics) -> str:
    holdings = sorted(metrics.holdings, key=lambda x: x.unrealized_pnl_pct)
    if not holdings:
        return ""
    names = [h.ticker for h in holdings]
    pcts = [h.unrealized_pnl_pct for h in holdings]
    colors = [PROFIT if p >= 0 else LOSS for p in pcts]

    fig, ax = plt.subplots(figsize=(7.8, max(3.2, 0.35 * len(holdings))))
    ax.barh(names, pcts, color=colors, edgecolor="none")
    ax.axvline(0, color=TEXT_MED, linewidth=1)
    ax.set_xlabel("Unrealized P&L (%)", color=TEXT_MED)
    ax.set_title("Per-position unrealized P&L", color=TEXT_HIGH, fontsize=13, fontweight="600", pad=10)
    _style_axes(ax)
    for i, p in enumerate(pcts):
        ax.text(p + (0.4 if p >= 0 else -0.4), i, f"{p:+.1f}%",
                va="center", ha="left" if p >= 0 else "right",
                color=TEXT_HIGH, fontsize=9, fontfamily="monospace")
    return _fig_to_b64(fig)


def bar_sector(sectors: dict[str, float]) -> str:
    sectors = {k: v for k, v in sectors.items() if v > 0}
    if not sectors:
        return ""
    items = sorted(sectors.items(), key=lambda x: -x[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(7.8, max(3, 0.4 * len(items))))
    ax.barh(names, vals, color=PRIMARY, edgecolor="none")
    ax.invert_yaxis()
    ax.set_xlabel("Allocation (%)", color=TEXT_MED)
    ax.set_title("Sector allocation", color=TEXT_HIGH, fontsize=13, fontweight="600", pad=10)
    _style_axes(ax)
    for i, v in enumerate(vals):
        ax.text(v + 0.3, i, f"{v:.1f}%", va="center", color=TEXT_HIGH, fontsize=9, fontfamily="monospace")
    return _fig_to_b64(fig)


def kpi_strip(metrics: PortfolioMetrics) -> str:
    """Single row of 4 KPI tiles rendered as an image so PDF is self-contained."""
    fig, axes = plt.subplots(1, 4, figsize=(10.6, 1.7))
    kpis = [
        ("Market value", f"${metrics.total_market_value:,.0f}", TEXT_HIGH),
        ("Unrealized P&L", f"{'+' if metrics.unrealized_pnl >= 0 else ''}${metrics.unrealized_pnl:,.0f}", PROFIT if metrics.unrealized_pnl >= 0 else LOSS),
        ("Return", f"{metrics.unrealized_pnl_pct:+.2f}%", PROFIT if metrics.unrealized_pnl_pct >= 0 else LOSS),
        ("Top-5 concentration", f"{metrics.concentration_top5:.1f}%", TEXT_HIGH),
    ]
    for ax, (label, value, vcolor) in zip(axes, kpis):
        ax.set_facecolor(SURFACE)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.5, 0.72, label, ha="center", color=TEXT_MED, fontsize=10,
                fontweight="600", transform=ax.transAxes)
        ax.text(0.5, 0.30, value, ha="center", color=vcolor, fontsize=20,
                fontweight="700", fontfamily="monospace", transform=ax.transAxes)
    fig.patch.set_facecolor(BG)
    fig.subplots_adjust(wspace=0.18, left=0.01, right=0.99, top=0.92, bottom=0.05)
    return _fig_to_b64(fig)
