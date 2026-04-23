"""Portfolio math — MTM, P&L, allocations, concentration. Deterministic (no LLM)."""
from __future__ import annotations
from collections import defaultdict
from app.schemas import PortfolioInput, EnrichedHolding, PortfolioMetrics


def compute_metrics(portfolio: PortfolioInput, market: dict[str, dict]) -> PortfolioMetrics:
    """Deterministic portfolio stats from positions + market data dict."""
    enriched: list[EnrichedHolding] = []
    total_mv = 0.0
    total_cost = 0.0

    for h in portfolio.holdings:
        t = h.ticker.upper()
        m = market.get(t, {})
        price = m.get("price")
        sector = h.sector or m.get("sector", "Unknown")
        asset_class = h.asset_class or m.get("asset_class", "Equity")
        err = m.get("error")

        if price is None:
            # missing market data → use cost as fallback so the report still renders
            price = h.avg_cost
            err = err or "No live price — used cost basis"

        cost = h.avg_cost * h.shares
        mv = price * h.shares
        pnl = mv - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0.0

        enriched.append(EnrichedHolding(
            ticker=t,
            shares=h.shares,
            avg_cost=h.avg_cost,
            current_price=price,
            cost_basis=cost,
            market_value=mv,
            unrealized_pnl=pnl,
            unrealized_pnl_pct=pnl_pct,
            allocation_pct=0.0,
            sector=sector,
            asset_class=asset_class,
            price_error=err,
        ))
        total_mv += mv
        total_cost += cost

    total_with_cash = total_mv + portfolio.cash
    denom = total_with_cash or 1.0
    for e in enriched:
        e.allocation_pct = round(100 * e.market_value / denom, 2)

    by_sector: dict[str, float] = defaultdict(float)
    by_asset: dict[str, float] = defaultdict(float)
    for e in enriched:
        by_sector[e.sector or "Unknown"] += e.market_value
        by_asset[e.asset_class or "Equity"] += e.market_value
    if portfolio.cash > 0:
        by_sector["Cash"] += portfolio.cash
        by_asset["Cash"] += portfolio.cash
    by_sector = {k: round(100 * v / denom, 2) for k, v in by_sector.items()}
    by_asset = {k: round(100 * v / denom, 2) for k, v in by_asset.items()}

    sorted_by_mv = sorted(enriched, key=lambda x: -x.market_value)
    conc_top1 = sorted_by_mv[0].allocation_pct if sorted_by_mv else 0.0
    conc_top5 = sum(h.allocation_pct for h in sorted_by_mv[:5])

    winners = sorted(enriched, key=lambda x: -x.unrealized_pnl_pct)[:3]
    losers = sorted(enriched, key=lambda x: x.unrealized_pnl_pct)[:3]
    total_pnl = total_mv - total_cost

    return PortfolioMetrics(
        total_cost=round(total_cost, 2),
        total_market_value=round(total_mv, 2),
        total_with_cash=round(total_with_cash, 2),
        cash=portfolio.cash,
        unrealized_pnl=round(total_pnl, 2),
        unrealized_pnl_pct=round((total_pnl / total_cost * 100) if total_cost else 0.0, 2),
        holdings=enriched,
        allocation_by_sector=by_sector,
        allocation_by_asset_class=by_asset,
        concentration_top1=round(conc_top1, 2),
        concentration_top5=round(conc_top5, 2),
        n_holdings=len(enriched),
        winners=winners,
        losers=losers,
        benchmark=portfolio.benchmark,
    )
