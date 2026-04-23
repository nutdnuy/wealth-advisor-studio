"""Wealth Advisor Studio — Streamlit edition.

Same backend as the FastAPI version:
  - Numbers computed in Python (deterministic)
  - LLM writes narrative only (cannot invent numbers)
  - Alpha Vantage for live prices (with caching + rate-limit)
  - Guide to the Markets PDF pages embedded
  - QuantSeras dark theme
"""
from __future__ import annotations
import asyncio
import io
import base64
import csv as csvlib
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import streamlit as st
from app.config import settings
from app.schemas import ClientProfile, Holding, PortfolioInput
from app import market_data, portfolio as pfmod, recommender, deck_builder, guide_extractor


# ---------- Page config ----------
st.set_page_config(
    page_title="Wealth Advisor Studio",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- QuantSeras CSS overlay ----------
QUANTSERAS_CSS = """
<style>
:root {
  --bg: #121212;
  --surface-1: #1D1D1D;
  --surface-2: #212121;
  --surface-3: #242424;
  --primary: #69F0AE;
  --primary-variant: #00C853;
  --secondary: #03DAC6;
  --profit: #00E676;
  --loss: #FF5252;
  --text-high: rgba(255,255,255,0.87);
  --text-med: rgba(255,255,255,0.60);
  --border: rgba(255,255,255,0.08);
}
.stApp { background: #121212; }
html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, sans-serif !important;
  color: var(--text-high);
}
section[data-testid="stSidebar"] { background: #1D1D1D; border-right: 1px solid var(--border); }
h1, h2, h3 { color: var(--text-high) !important; font-weight: 700 !important; letter-spacing: -0.01em; }
h1 { font-size: 32px !important; }
h3 { color: var(--primary) !important; text-transform: uppercase; letter-spacing: 0.12em; font-size: 14px !important; }
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1280px; }
/* Buttons */
.stButton > button, .stDownloadButton > button {
  background: var(--primary) !important;
  color: #000 !important; font-weight: 700 !important; letter-spacing: 0.04em;
  text-transform: uppercase; border: none !important; border-radius: 4px !important;
  padding: 10px 22px !important;
}
.stButton > button:hover, .stDownloadButton > button:hover { background: var(--primary-variant) !important; }
.stButton > button:disabled { opacity: 0.45 !important; }
/* Inputs */
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
  background: var(--surface-2) !important; color: var(--text-high) !important;
  border: 1px solid rgba(255,255,255,0.12) !important; border-radius: 4px !important;
}
.stTextInput input:focus, .stNumberInput input:focus { border-color: var(--primary) !important; }
/* Metrics */
[data-testid="stMetric"] {
  background: var(--surface-2); padding: 16px; border-radius: 8px;
  border: 1px solid var(--border);
}
[data-testid="stMetricLabel"] { color: var(--text-med) !important; text-transform: uppercase; letter-spacing: 0.1em; font-size: 11px !important; font-weight: 600; }
[data-testid="stMetricValue"] { color: var(--text-high) !important; font-family: 'JetBrains Mono', monospace !important; font-size: 26px !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] { font-family: 'JetBrains Mono', monospace !important; }
/* DataFrames */
.stDataFrame { background: var(--surface-1); border-radius: 8px; border: 1px solid var(--border); }
/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] { color: var(--text-med); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; font-size: 13px; padding: 10px 18px; border-bottom: 3px solid transparent; }
.stTabs [aria-selected="true"] { color: var(--primary) !important; border-bottom-color: var(--primary) !important; }
/* Callouts */
.stAlert { border-radius: 6px; }
/* Progress */
.stProgress > div > div > div > div { background: var(--primary) !important; }
/* Custom kicker */
.kicker {
  display: inline-block; color: var(--primary); font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.15em; font-weight: 700;
  padding-bottom: 4px; border-bottom: 2px solid var(--primary); margin-bottom: 8px;
}
.rec-card {
  background: var(--surface-2); border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
  border-left: 3px solid var(--primary);
}
.rec-card.high { border-left-color: #FFB74D; }
.rec-card.low { border-left-color: var(--secondary); }
.rec-title { font-weight: 700; color: var(--text-high); font-size: 15px; }
.rec-action { color: var(--primary); font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px; }
.rec-rationale { color: var(--text-high); margin-top: 6px; font-size: 13.5px; line-height: 1.5; }
.rec-badge { float: right; font-size: 9px; padding: 2px 7px; border-radius: 2px; background: var(--primary-variant); color: #000; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; }
.rec-card.high .rec-badge { background: #FFB74D; }
.rec-card.low .rec-badge { background: var(--secondary); }
</style>
"""
st.markdown(QUANTSERAS_CSS, unsafe_allow_html=True)


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(
        "<div style='display:flex; align-items:center; gap:10px; margin-bottom:14px;'>"
        "<div style='width:32px; height:32px; background:#69F0AE; border-radius:7px; "
        "position:relative;'>"
        "<div style='position:absolute; inset:7px; border:2px solid #000; border-radius:3px;'></div>"
        "</div>"
        "<div><div style='color:#69F0AE; font-size:10px; letter-spacing:0.15em; "
        "text-transform:uppercase; font-weight:700;'>QuantSeras</div>"
        "<div style='font-size:17px; font-weight:700; color:white;'>Wealth Advisor Studio</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.caption("LLM-generated personalized wealth reviews with Alpha Vantage pricing & Guide-to-the-Markets context.")
    st.divider()

    st.markdown("### ⚙️ System")
    ok_openai = "✅" if settings.openai_api_key else "❌"
    ok_av = "✅" if settings.alpha_vantage_key else "❌"
    ok_pdf = "✅" if Path(settings.guide_pdf_path).exists() else "❌"
    st.text(f"OpenAI key     {ok_openai}")
    st.text(f"Alpha Vantage  {ok_av}")
    st.text(f"Guide PDF      {ok_pdf}")
    st.text(f"Model          {settings.model}")

    if not settings.openai_api_key:
        st.warning("Set `WAS_OPENAI_API_KEY` in `.env` or Streamlit secrets.")
    if not settings.alpha_vantage_key:
        st.info("Alpha Vantage key is optional — you can enter override prices per ticker instead.")

    st.divider()
    st.markdown(
        "<div style='font-size:11px; color:rgba(255,255,255,0.55); line-height:1.5;'>"
        "<strong>Disclaimer.</strong> Outputs are informational only, not investment advice. "
        "Numerical calculations are deterministic; narrative is LLM-generated and must be reviewed by a licensed advisor before client delivery."
        "</div>",
        unsafe_allow_html=True,
    )


# ---------- Header ----------
st.markdown("<div class='kicker'>Input</div>", unsafe_allow_html=True)
st.title("Build a personalized wealth review")
st.caption("Enter a client profile and portfolio. Python computes the numbers, LLM writes the narrative, WeasyPrint renders the PDF — with JPM Guide-to-the-Markets pages embedded for market context.")


# ---------- Session state ----------
if "holdings_df" not in st.session_state:
    st.session_state.holdings_df = pd.DataFrame([
        {"ticker": "", "shares": 0.0, "avg_cost": 0.0, "override_price": 0.0, "sector": ""},
    ])
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_pdf_bytes" not in st.session_state:
    st.session_state.last_pdf_bytes = None
if "selected_pages" not in st.session_state:
    st.session_state.selected_pages = set()


def _sample_portfolio():
    st.session_state.holdings_df = pd.DataFrame([
        {"ticker": "AAPL", "shares": 50.0, "avg_cost": 150.0, "override_price": 0.0, "sector": ""},
        {"ticker": "MSFT", "shares": 30.0, "avg_cost": 280.0, "override_price": 0.0, "sector": ""},
        {"ticker": "NVDA", "shares": 20.0, "avg_cost": 320.0, "override_price": 0.0, "sector": ""},
        {"ticker": "VOO",  "shares": 40.0, "avg_cost": 380.0, "override_price": 0.0, "sector": ""},
        {"ticker": "BND",  "shares": 100.0, "avg_cost": 74.0, "override_price": 0.0, "sector": "Fixed Income"},
    ])


# ---------- Client profile ----------
st.markdown("### Client profile")
st.markdown("#### Who is this for?")
col1, col2 = st.columns(2)
with col1:
    client_name = st.text_input("Full name", placeholder="Jane Lertpanyarit")
with col2:
    client_age = st.number_input("Age", min_value=18, max_value=100, value=42, step=1)

col3, col4, col5 = st.columns(3)
with col3:
    risk_profile = st.selectbox("Risk profile", ["conservative", "balanced", "growth", "aggressive"], index=1)
with col4:
    time_horizon = st.number_input("Time horizon (yrs)", min_value=1, max_value=60, value=15, step=1)
with col5:
    monthly_contrib = st.number_input("Monthly contribution (USD)", min_value=0.0, value=0.0, step=100.0)

col6, col7 = st.columns(2)
with col6:
    goal = st.text_input("Primary goal", value="Long-term wealth growth")
with col7:
    tax_bracket = st.text_input("Tax bracket", placeholder="35% marginal / Thai PIT")

notes = st.text_area("Advisor notes (optional)", placeholder="Any special circumstances, constraints, or preferences (ESG, restricted tickers, upcoming life events…)")

st.divider()

# ---------- Portfolio ----------
st.markdown("### Portfolio")
st.markdown("#### Positions & cost basis")

tab_edit, tab_csv = st.tabs(["📝 Edit manually", "📥 Upload CSV"])

with tab_edit:
    st.caption("Fill the table below. `override_price` = manual per-share price (leave 0 for live Alpha Vantage fetch).")
    edited = st.data_editor(
        st.session_state.holdings_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", required=True),
            "shares": st.column_config.NumberColumn("Shares", format="%g", min_value=0.0),
            "avg_cost": st.column_config.NumberColumn("Avg cost ($)", format="%.2f", min_value=0.0),
            "override_price": st.column_config.NumberColumn("Override price ($)", format="%.2f", min_value=0.0, help="Manual price override. 0 = fetch live."),
            "sector": st.column_config.TextColumn("Sector (opt)"),
        },
        key="holdings_editor",
    )
    st.session_state.holdings_df = edited
    col_s1, col_s2 = st.columns([1, 4])
    with col_s1:
        if st.button("Load sample portfolio", type="secondary"):
            _sample_portfolio()
            st.rerun()

with tab_csv:
    st.caption("CSV with columns: `ticker, shares, avg_cost` (optional: `sector`, `asset_class`).")
    up = st.file_uploader("Drop CSV here", type=["csv"])
    if up is not None:
        try:
            df = pd.read_csv(up)
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            if "cost" in df.columns and "avg_cost" not in df.columns:
                df["avg_cost"] = df["cost"]
            needed = {"ticker", "shares", "avg_cost"}
            missing = needed - set(df.columns)
            if missing:
                st.error(f"Missing columns: {missing}")
            else:
                df["ticker"] = df["ticker"].str.upper()
                if "override_price" not in df.columns:
                    df["override_price"] = 0.0
                if "sector" not in df.columns:
                    df["sector"] = ""
                st.session_state.holdings_df = df[["ticker", "shares", "avg_cost", "override_price", "sector"]].fillna(0)
                st.success(f"Loaded {len(df)} rows from {up.name}")
                st.rerun()
        except Exception as e:
            st.error(f"CSV parse error: {e}")

col_cash, col_bench = st.columns(2)
with col_cash:
    cash = st.number_input("Cash (USD)", min_value=0.0, value=0.0, step=500.0)
with col_bench:
    benchmark = st.text_input("Benchmark", value="SPY")

fetch_live = st.checkbox("Fetch live prices from Alpha Vantage", value=bool(settings.alpha_vantage_key))

st.divider()

# ---------- Guide pages ----------
st.markdown("### Market context")
st.markdown("#### Pages from JPM Guide to the Markets")
st.caption("Leave all unchecked → auto-select based on portfolio tilt. Otherwise pick specific pages to embed.")
guide_pages_available = [(k, v) for k, v in guide_extractor.GUIDE_INDEX.items()]
cols_guide = st.columns(3)
for i, (pg, info) in enumerate(guide_pages_available):
    with cols_guide[i % 3]:
        checked = st.checkbox(
            f"p.{pg} · {info['title']}",
            key=f"gp_{pg}",
            value=pg in st.session_state.selected_pages,
        )
        if checked:
            st.session_state.selected_pages.add(pg)
        else:
            st.session_state.selected_pages.discard(pg)

st.divider()

# ---------- Generate ----------
gen_col1, gen_col2 = st.columns([1, 3])
with gen_col1:
    run = st.button("🚀 Generate presentation", type="primary", use_container_width=True, disabled=not settings.openai_api_key)
with gen_col2:
    if not settings.openai_api_key:
        st.error("Missing OpenAI API key — set `WAS_OPENAI_API_KEY` in .env or Streamlit secrets.")


def _collect_inputs():
    client = ClientProfile(
        name=client_name.strip() or "Client",
        age=int(client_age) if client_age else None,
        risk_profile=risk_profile,
        goal=goal.strip() or "Long-term wealth growth",
        time_horizon_years=int(time_horizon) if time_horizon else None,
        monthly_contribution=float(monthly_contrib) if monthly_contrib else None,
        tax_bracket=tax_bracket or None,
        notes=notes or "",
    )
    df = st.session_state.holdings_df.dropna(subset=["ticker"])
    df = df[df["ticker"].astype(str).str.strip() != ""]
    df = df[(df["shares"].astype(float) > 0) & (df["avg_cost"].astype(float) >= 0)]
    holdings = []
    overrides: dict[str, float] = {}
    for _, row in df.iterrows():
        t = str(row["ticker"]).strip().upper()
        holdings.append(Holding(
            ticker=t,
            shares=float(row["shares"]),
            avg_cost=float(row["avg_cost"]),
            sector=(str(row.get("sector") or "").strip() or None),
        ))
        op = float(row.get("override_price") or 0)
        if op > 0:
            overrides[t] = op
    portfolio_in = PortfolioInput(
        client=client,
        holdings=holdings,
        cash=float(cash),
        benchmark=benchmark.strip() or "SPY",
    )
    return portfolio_in, overrides


async def _run_pipeline(portfolio_in: PortfolioInput, overrides: dict[str, float], guide_pages: list[int] | None, fetch_live_prices: bool, progress_cb):
    progress_cb(10, "Fetching market data")
    tickers = [h.ticker for h in portfolio_in.holdings]
    market: dict = {}
    if fetch_live_prices and tickers:
        try:
            market = await market_data.fetch_bulk(tickers, include_overview=True, overrides=overrides)
        except RuntimeError as e:
            market = {t: {"price": overrides.get(t), "sector": "Unknown", "error": str(e)} for t in tickers}
    else:
        market = {t: {"price": overrides.get(t), "sector": "Unknown"} for t in tickers}
    for t, p in overrides.items():
        market.setdefault(t, {})["price"] = p

    progress_cb(35, "Computing portfolio metrics")
    metrics = pfmod.compute_metrics(portfolio_in, market)

    if not guide_pages:
        guide_pages = guide_extractor.auto_select_pages(
            metrics.allocation_by_sector, metrics.allocation_by_asset_class,
        )
    as_of = datetime.now(timezone.utc).strftime("%b %d, %Y")
    selected_meta = [
        {"page": p, "title": guide_extractor.GUIDE_INDEX.get(p, {}).get("title") or f"p.{p}"}
        for p in guide_pages
    ]

    progress_cb(55, "LLM generating narrative")
    narrative = await recommender.build_narrative(
        portfolio_in.client, metrics, selected_meta, as_of,
    )

    progress_cb(80, "Building deck & rendering PDF")
    html, _ = deck_builder.build_deck_html(
        portfolio_in.client, metrics, narrative, guide_pages, as_of,
    )
    safe_name = "".join(c for c in portfolio_in.client.name.lower().replace(" ", "-") if c.isalnum() or c in "-_")
    rid = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"wealth-review-{safe_name}-{rid}.pdf"
    out_path = Path(settings.output_dir) / filename
    size = deck_builder.render_pdf(html, out_path)

    progress_cb(100, "Done")
    return {
        "metrics": metrics,
        "narrative": narrative,
        "guide_pages": guide_pages,
        "pdf_path": out_path,
        "pdf_size": size,
        "filename": filename,
        "as_of": as_of,
    }


if run:
    portfolio_in, overrides = _collect_inputs()
    if not portfolio_in.client.name.strip():
        st.error("Client name is required.")
    elif not portfolio_in.holdings:
        st.error("Add at least one holding (ticker + shares + avg cost).")
    else:
        pct_bar = st.progress(0, text="Starting…")
        def _cb(p, msg):
            pct_bar.progress(p, text=msg)
        try:
            with st.spinner("Running full pipeline (30–90s typical)…"):
                result = asyncio.run(_run_pipeline(
                    portfolio_in, overrides,
                    list(st.session_state.selected_pages) or None,
                    fetch_live,
                    _cb,
                ))
            st.session_state.last_result = result
            with open(result["pdf_path"], "rb") as f:
                st.session_state.last_pdf_bytes = f.read()
            st.success(f"✅ Deck ready — {result['filename']} ({result['pdf_size']/1024:.1f} KB)")
        except Exception as e:
            st.error(f"Pipeline failed: {e}")


# ---------- Result ----------
if st.session_state.last_result:
    res = st.session_state.last_result
    metrics = res["metrics"]
    narrative = res["narrative"]

    st.markdown("---")
    st.markdown("<div class='kicker'>Result</div>", unsafe_allow_html=True)
    st.title("📄 Deck ready")

    # Download
    col_d1, col_d2 = st.columns([2, 1])
    with col_d1:
        st.markdown(
            f"**File:** `{res['filename']}`  \n"
            f"**Size:** {res['pdf_size']/1024:.1f} KB · "
            f"{metrics.n_holdings} positions · "
            f"{len(res['guide_pages'])} guide pages embedded"
        )
    with col_d2:
        if st.session_state.last_pdf_bytes:
            st.download_button(
                "⬇ Download PDF",
                st.session_state.last_pdf_bytes,
                file_name=res["filename"],
                mime="application/pdf",
                use_container_width=True,
            )

    # KPIs
    st.markdown("### Executive snapshot")
    k1, k2, k3, k4 = st.columns(4)
    pnl_sign = "+" if metrics.unrealized_pnl >= 0 else ""
    with k1: st.metric("Market value", f"${metrics.total_market_value:,.0f}")
    with k2: st.metric(
        "Unrealized P&L",
        f"{pnl_sign}${metrics.unrealized_pnl:,.0f}",
        delta=f"{metrics.unrealized_pnl_pct:+.2f}%",
    )
    with k3: st.metric("Top-5 concentration", f"{metrics.concentration_top5:.1f}%")
    with k4: st.metric("Holdings", metrics.n_holdings)

    # Bullets
    st.markdown("### Executive summary")
    for b in narrative.executive_summary:
        st.markdown(f"- {b}")

    # Holdings table
    st.markdown("### Positions")
    holdings_df = pd.DataFrame([
        {
            "Ticker": h.ticker,
            "Sector": h.sector or "—",
            "Shares": h.shares,
            "Avg cost": h.avg_cost,
            "Price": h.current_price,
            "Market value": h.market_value,
            "Weight %": h.allocation_pct,
            "P&L %": h.unrealized_pnl_pct,
        }
        for h in metrics.holdings
    ])
    st.dataframe(
        holdings_df.style.format({
            "Shares": "{:g}",
            "Avg cost": "${:,.2f}",
            "Price": "${:,.2f}",
            "Market value": "${:,.0f}",
            "Weight %": "{:.1f}%",
            "P&L %": "{:+.2f}%",
        }),
        use_container_width=True,
    )

    col_m, col_p = st.columns(2)
    with col_m:
        st.markdown("### Market commentary")
        st.write(narrative.market_commentary)
    with col_p:
        st.markdown("### Portfolio commentary")
        st.write(narrative.portfolio_commentary)

    # Recommendations
    st.markdown("### Recommendations")
    for r in narrative.recommendations:
        tickers_str = " · " + ", ".join(r.tickers) if r.tickers else ""
        st.markdown(
            f"<div class='rec-card {r.priority}'>"
            f"<div class='rec-badge'>{r.priority}</div>"
            f"<div class='rec-title'>{r.title}</div>"
            f"<div class='rec-action'>{r.action}{tickers_str}</div>"
            f"<div class='rec-rationale'>{r.rationale}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Action items + closing
    st.markdown("### Action items")
    for i, a in enumerate(narrative.action_items, 1):
        st.markdown(f"**{i:02d}.** {a}")
    st.info(narrative.closing_note)
