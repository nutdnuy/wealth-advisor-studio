"""Data contracts: client profile, portfolio, report request, LLM structured output."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ---------- Client / Portfolio input ----------

class ClientProfile(BaseModel):
    name: str
    age: int | None = None
    risk_profile: Literal["conservative", "balanced", "growth", "aggressive"] = "balanced"
    goal: str = Field(default="Long-term wealth growth")
    time_horizon_years: int | None = None
    monthly_contribution: float | None = None
    tax_bracket: str | None = None
    notes: str = ""


class Holding(BaseModel):
    ticker: str
    shares: float = Field(gt=0)
    avg_cost: float = Field(ge=0, description="Average cost basis per share.")
    asset_class: str | None = None
    sector: str | None = None


class PortfolioInput(BaseModel):
    client: ClientProfile
    holdings: list[Holding]
    cash: float = 0.0
    benchmark: str = "SPY"


# ---------- Enriched portfolio (after market data + computations) ----------

class EnrichedHolding(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    current_price: float
    cost_basis: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    allocation_pct: float
    sector: str | None = None
    asset_class: str | None = None
    price_error: str | None = None


class PortfolioMetrics(BaseModel):
    total_cost: float
    total_market_value: float
    total_with_cash: float
    cash: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    holdings: list[EnrichedHolding]
    allocation_by_sector: dict[str, float]
    allocation_by_asset_class: dict[str, float]
    concentration_top1: float
    concentration_top5: float
    n_holdings: int
    winners: list[EnrichedHolding]
    losers: list[EnrichedHolding]
    benchmark: str
    benchmark_ytd_return: float | None = None


# ---------- LLM structured output ----------

class Recommendation(BaseModel):
    title: str
    rationale: str = Field(description="Why this recommendation fits this client now (2-3 sentences).")
    action: Literal["rebalance", "buy", "trim", "hold", "tax-loss-harvest", "diversify", "review"]
    priority: Literal["high", "medium", "low"] = "medium"
    tickers: list[str] = Field(default_factory=list, description="Affected tickers (may be empty).")


class AdvisorNarrative(BaseModel):
    executive_summary: list[str] = Field(min_length=3, max_length=5, description="3-5 bullet points summarizing the review.")
    market_commentary: str = Field(description="2-3 paragraphs interpreting current markets for this client.")
    portfolio_commentary: str = Field(description="1-2 paragraphs assessing portfolio performance and risk.")
    recommendations: list[Recommendation] = Field(min_length=3, max_length=6)
    action_items: list[str] = Field(min_length=3, max_length=6, description="Next-step checklist for the client.")
    closing_note: str = Field(description="1 short paragraph — closing encouragement / reminder.")


# ---------- Report API ----------

class ReportRequest(BaseModel):
    portfolio: PortfolioInput
    fetch_live_prices: bool = True
    price_overrides: dict[str, float] = Field(default_factory=dict, description="Ticker → price fallback / override.")
    guide_page_indices: list[int] | None = Field(default=None, description="1-indexed pages from Guide to Markets to embed. None = auto.")


class ReportMeta(BaseModel):
    report_id: str
    created_at: str
    client_name: str
    filename: str
    size_bytes: int
    metrics_snapshot: dict
