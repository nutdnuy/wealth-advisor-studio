"""LLM-driven narrative + recommendations. Numbers come from Python, not the LLM."""
from __future__ import annotations
from app.llm import structured
from app.schemas import (
    ClientProfile, PortfolioMetrics, AdvisorNarrative,
)


def _portfolio_brief(metrics: PortfolioMetrics) -> str:
    holds = [
        f"  - {h.ticker}: {h.shares:g} sh @ cost ${h.avg_cost:,.2f} → MV ${h.market_value:,.0f} "
        f"({h.allocation_pct:.1f}% port., P&L {h.unrealized_pnl_pct:+.1f}%, sector={h.sector})"
        for h in metrics.holdings
    ]
    winners = ", ".join(f"{w.ticker} ({w.unrealized_pnl_pct:+.1f}%)" for w in metrics.winners)
    losers = ", ".join(f"{l.ticker} ({l.unrealized_pnl_pct:+.1f}%)" for l in metrics.losers)
    return (
        f"Total MV: ${metrics.total_market_value:,.0f} (+cash ${metrics.cash:,.0f}) | "
        f"Unrealized P&L: {metrics.unrealized_pnl_pct:+.2f}% (${metrics.unrealized_pnl:,.0f})\n"
        f"Holdings ({metrics.n_holdings}):\n" + "\n".join(holds) + "\n"
        f"Top-1 concentration: {metrics.concentration_top1:.1f}% | Top-5: {metrics.concentration_top5:.1f}%\n"
        f"Sector allocation: {metrics.allocation_by_sector}\n"
        f"Asset class: {metrics.allocation_by_asset_class}\n"
        f"Winners: {winners} | Losers: {losers}"
    )


def _guide_brief(selected_pages: list[dict]) -> str:
    if not selected_pages:
        return "(no market-context pages selected)"
    return "\n".join(f"  - p.{p['page']}: {p['title']}" for p in selected_pages)


async def build_narrative(
    client: ClientProfile,
    metrics: PortfolioMetrics,
    selected_guide_pages: list[dict],
    as_of_date: str,
) -> AdvisorNarrative:
    system = (
        "You are a senior wealth advisor preparing a personalized quarterly review presentation for a private client. "
        "Write in clear, confident, regulator-friendly English. Tone: warm but disciplined, never hyped. "
        "IMPORTANT rules:\n"
        "1. DO NOT invent new numbers — the numbers in the user message are ground truth and are the ONLY numbers you may cite.\n"
        "2. Recommendations must be justified by (a) the client's profile and (b) the actual portfolio state.\n"
        "3. Be specific — name tickers, sectors, allocation % when relevant.\n"
        "4. Market commentary must reference JPM Guide to the Markets themes (valuation, rates, concentration, diversification).\n"
        "5. Avoid making specific return predictions. Use probabilistic language.\n"
        "6. Keep bullets tight. No filler like 'in today's dynamic market environment'.\n"
    )
    user = (
        f"As of: {as_of_date}\n"
        f"CLIENT PROFILE\n"
        f"  Name: {client.name}\n"
        f"  Age: {client.age or 'n/a'}\n"
        f"  Risk profile: {client.risk_profile}\n"
        f"  Goal: {client.goal}\n"
        f"  Time horizon: {client.time_horizon_years or 'n/a'} yrs\n"
        f"  Monthly contribution: {client.monthly_contribution or 'n/a'}\n"
        f"  Tax bracket: {client.tax_bracket or 'n/a'}\n"
        f"  Notes: {client.notes or '(none)'}\n\n"
        f"PORTFOLIO (snapshot — these numbers are authoritative, do not change them):\n"
        f"{_portfolio_brief(metrics)}\n\n"
        f"BENCHMARK: {metrics.benchmark}\n\n"
        f"MARKET CONTEXT (pages selected from JPM Guide to the Markets):\n"
        f"{_guide_brief(selected_guide_pages)}\n\n"
        "Produce the full advisor narrative per schema. Recommendations must be ACTIONABLE and fit this specific client."
    )
    return await structured(system, user, AdvisorNarrative)
