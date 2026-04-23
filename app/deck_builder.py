"""Build an HTML deck (slides styled with QuantSeras dark theme), then render to PDF via WeasyPrint."""
from __future__ import annotations
from datetime import datetime
from html import escape
from pathlib import Path
from weasyprint import HTML
from app.config import settings
from app.schemas import (
    ClientProfile, PortfolioMetrics, AdvisorNarrative,
)
from app import charts, guide_extractor


# Page size 297mm x 210mm landscape (A4) matches classic report decks and prints well.

BASE_CSS = """
@page {
  size: 297mm 210mm;
  margin: 0;
  background: #121212;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #121212; color: rgba(255,255,255,0.87); font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; }
.slide {
  width: 297mm; height: 210mm;
  padding: 16mm 18mm;
  page-break-after: always;
  position: relative;
  background: #121212;
  overflow: hidden;
}
.slide:last-child { page-break-after: auto; }

h1, h2, h3 { color: rgba(255,255,255,0.96); margin: 0; font-weight: 700; }
h1 { font-size: 34pt; line-height: 1.1; letter-spacing: -0.01em; }
h2 { font-size: 22pt; line-height: 1.2; margin-bottom: 4mm; }
h3 { font-size: 14pt; color: #69F0AE; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 3mm; font-weight: 600; }
p { font-size: 10.5pt; line-height: 1.5; color: rgba(255,255,255,0.82); margin: 0 0 2mm 0; }
.muted { color: rgba(255,255,255,0.60); font-size: 9pt; }
.mono { font-family: 'JetBrains Mono', 'SF Mono', Menlo, monospace; font-variant-numeric: tabular-nums; }

.header-bar {
  position: absolute; top: 0; left: 0; right: 0;
  height: 10mm; padding: 3mm 18mm;
  display: flex; align-items: center; justify-content: space-between;
  background: #0E0E0E; border-bottom: 1px solid rgba(105,240,174,0.18);
  font-size: 8.5pt; color: rgba(255,255,255,0.60);
}
.header-bar .brand { color: #69F0AE; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; }
.footer {
  position: absolute; bottom: 6mm; left: 18mm; right: 18mm;
  display: flex; justify-content: space-between;
  font-size: 8pt; color: rgba(255,255,255,0.50);
  border-top: 1px solid rgba(255,255,255,0.08); padding-top: 3mm;
}

.slide-body { margin-top: 12mm; height: calc(100% - 26mm); }
.kicker {
  display: inline-block; color: #69F0AE; font-size: 10pt; letter-spacing: 0.15em;
  text-transform: uppercase; font-weight: 600; padding-bottom: 2mm;
  border-bottom: 2px solid #69F0AE; margin-bottom: 5mm;
}

/* Cover */
.cover { display: flex; flex-direction: column; justify-content: space-between; padding: 30mm 24mm; }
.cover .title { font-size: 48pt; line-height: 1.05; font-weight: 800; color: #FFFFFF; }
.cover .title em { font-style: normal; color: #69F0AE; }
.cover .meta {
  display: flex; gap: 18mm; margin-top: 18mm;
  border-top: 2px solid #69F0AE; padding-top: 6mm;
}
.cover .meta div .label { font-size: 9pt; color: rgba(255,255,255,0.60); text-transform: uppercase; letter-spacing: 0.1em; }
.cover .meta div .value { font-size: 14pt; color: #FFFFFF; margin-top: 1mm; }

/* Cards */
.card-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5mm; margin-top: 5mm; }
.card {
  background: #1D1D1D; border-radius: 6px; padding: 5mm;
  border: 1px solid rgba(255,255,255,0.08);
}
.card .label { color: rgba(255,255,255,0.60); font-size: 8pt; text-transform: uppercase; letter-spacing: 0.12em; }
.card .value { font-family: 'JetBrains Mono', monospace; font-size: 18pt; font-weight: 700; margin-top: 2mm; }
.card .value.profit { color: #00E676; }
.card .value.loss { color: #FF5252; }

/* Tables */
table { width: 100%; border-collapse: collapse; font-size: 9.5pt; margin-top: 3mm; }
thead th {
  background: #242424; color: rgba(255,255,255,0.80);
  padding: 2.2mm 3mm; text-align: left; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em; font-size: 8pt;
  border-bottom: 1px solid rgba(105,240,174,0.22);
}
tbody td {
  padding: 2.2mm 3mm; border-bottom: 1px solid rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.85);
}
td.num, th.num { text-align: right; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
td.profit { color: #00E676; }
td.loss { color: #FF5252; }
tbody tr:last-child td { border-bottom: none; }

/* Chart blocks */
.chart-wrap { margin-top: 3mm; background: #1D1D1D; border-radius: 6px; padding: 4mm; border: 1px solid rgba(255,255,255,0.08); }
.chart-wrap img { width: 100%; height: auto; display: block; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; }

/* Guide pages */
.guide-page { background: #FAFAF7; border-radius: 4px; padding: 4mm; }
.guide-page img { width: 100%; height: auto; display: block; border-radius: 2px; }
.guide-caption { margin-top: 2mm; font-size: 8pt; color: rgba(255,255,255,0.55); text-align: center; font-style: italic; }

/* Rec cards */
.rec { background: #1D1D1D; border-radius: 6px; padding: 5mm; border-left: 4px solid #69F0AE; margin-bottom: 3mm; }
.rec.high { border-left-color: #FFB74D; }
.rec.low { border-left-color: #03DAC6; }
.rec .rec-head { display: flex; justify-content: space-between; align-items: flex-start; }
.rec .rec-title { font-weight: 700; color: #FFFFFF; font-size: 12pt; }
.rec .rec-badge {
  font-size: 7.5pt; padding: 1mm 2.4mm; background: #00C853; color: #000;
  text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; border-radius: 2px;
}
.rec.high .rec-badge { background: #FFB74D; }
.rec.low .rec-badge { background: #03DAC6; }
.rec .rec-action { color: #69F0AE; font-size: 8.5pt; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 1mm; }
.rec .rec-rationale { color: rgba(255,255,255,0.80); font-size: 9.5pt; margin-top: 2mm; line-height: 1.45; }
.rec .rec-tickers { color: rgba(255,255,255,0.55); font-size: 8.5pt; margin-top: 1mm; font-family: 'JetBrains Mono', monospace; }

/* Bullets */
ul.exec { margin: 0; padding-left: 4mm; }
ul.exec li { font-size: 11pt; line-height: 1.55; margin-bottom: 2mm; color: rgba(255,255,255,0.90); }
ul.exec li::marker { color: #69F0AE; }

ul.actions { margin: 0; padding-left: 5mm; counter-reset: ai; list-style: none; }
ul.actions li {
  counter-increment: ai; position: relative; padding-left: 8mm;
  font-size: 10.5pt; color: rgba(255,255,255,0.90); margin-bottom: 3mm; line-height: 1.5;
}
ul.actions li::before {
  content: counter(ai, decimal-leading-zero);
  position: absolute; left: 0; top: 0;
  color: #69F0AE; font-family: 'JetBrains Mono', monospace; font-weight: 700;
}
"""


def _header(client_name: str, slide_label: str) -> str:
    return (
        f'<div class="header-bar">'
        f'  <span class="brand">QuantSeras · Wealth Review</span>'
        f'  <span>{escape(client_name)} · {escape(slide_label)}</span>'
        f'</div>'
    )


def _footer(slide_num: int, total: int, as_of: str) -> str:
    return (
        f'<div class="footer">'
        f'  <span>Confidential — for addressee only</span>'
        f'  <span class="mono">{as_of} · {slide_num:02d} / {total:02d}</span>'
        f'</div>'
    )


def _fmt_money(x: float) -> str:
    return f"${x:,.0f}"


def _fmt_pct(x: float) -> str:
    return f"{x:+.2f}%"


def _slide_cover(client: ClientProfile, as_of: str, benchmark: str) -> str:
    return f"""
<section class="slide cover">
  <div>
    <div class="kicker">Quarterly Review · {escape(as_of)}</div>
    <h1 class="title">Personalized<br/><em>Wealth Review</em></h1>
    <p class="muted" style="margin-top: 8mm; max-width: 180mm;">
      A bespoke portfolio &amp; market review prepared for this account,
      grounded in the latest Guide to the Markets.
    </p>
  </div>
  <div class="meta">
    <div><div class="label">Prepared for</div><div class="value">{escape(client.name)}</div></div>
    <div><div class="label">Risk profile</div><div class="value">{escape(client.risk_profile.title())}</div></div>
    <div><div class="label">Goal</div><div class="value">{escape(client.goal[:38])}</div></div>
    <div><div class="label">Benchmark</div><div class="value mono">{escape(benchmark)}</div></div>
  </div>
</section>
"""


def _slide_executive(client_name: str, kpi_img: str, narrative: AdvisorNarrative, as_of: str, n: int, total: int) -> str:
    bullets = "\n".join(f"<li>{escape(b)}</li>" for b in narrative.executive_summary)
    return f"""
<section class="slide">
  {_header(client_name, "Executive Summary")}
  <div class="slide-body">
    <div class="kicker">01 · Executive Summary</div>
    <h2>Where we stand this quarter</h2>
    <img src="{kpi_img}" style="width: 100%; max-height: 42mm; margin: 4mm 0;" />
    <ul class="exec">{bullets}</ul>
  </div>
  {_footer(n, total, as_of)}
</section>
"""


def _slide_holdings(client_name: str, metrics: PortfolioMetrics, as_of: str, n: int, total: int) -> str:
    rows = "\n".join(
        f"<tr>"
        f"<td><b>{escape(h.ticker)}</b></td>"
        f"<td>{escape(h.sector or '—')}</td>"
        f"<td class='num'>{h.shares:g}</td>"
        f"<td class='num'>${h.avg_cost:,.2f}</td>"
        f"<td class='num'>${h.current_price:,.2f}</td>"
        f"<td class='num'>${h.market_value:,.0f}</td>"
        f"<td class='num'>{h.allocation_pct:.1f}%</td>"
        f"<td class='num {'profit' if h.unrealized_pnl_pct >= 0 else 'loss'}'>{h.unrealized_pnl_pct:+.1f}%</td>"
        f"</tr>"
        for h in metrics.holdings
    )
    return f"""
<section class="slide">
  {_header(client_name, "Positions")}
  <div class="slide-body">
    <div class="kicker">02 · Positions</div>
    <h2>Holdings &amp; unrealized P&amp;L</h2>
    <p class="muted">{metrics.n_holdings} positions · cash ${metrics.cash:,.0f} · total ${metrics.total_with_cash:,.0f}</p>
    <table>
      <thead>
        <tr><th>Ticker</th><th>Sector</th><th class="num">Shares</th><th class="num">Avg cost</th><th class="num">Price</th><th class="num">Market value</th><th class="num">Weight</th><th class="num">P&amp;L %</th></tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  {_footer(n, total, as_of)}
</section>
"""


def _slide_allocation(client_name: str, sector_pie: str, pnl_bar: str, as_of: str, n: int, total: int) -> str:
    return f"""
<section class="slide">
  {_header(client_name, "Allocation & P&L")}
  <div class="slide-body">
    <div class="kicker">03 · Allocation &amp; risk</div>
    <h2>Where your money sits — and where it's working</h2>
    <div class="two-col" style="margin-top: 6mm;">
      <div class="chart-wrap"><img src="{sector_pie}" /></div>
      <div class="chart-wrap"><img src="{pnl_bar}" /></div>
    </div>
  </div>
  {_footer(n, total, as_of)}
</section>
"""


def _slide_portfolio_commentary(client_name: str, narrative: AdvisorNarrative, metrics: PortfolioMetrics, as_of: str, n: int, total: int) -> str:
    return f"""
<section class="slide">
  {_header(client_name, "Portfolio view")}
  <div class="slide-body">
    <div class="kicker">04 · Portfolio commentary</div>
    <h2>Reading the positioning</h2>
    <p style="margin-top: 4mm; font-size: 11pt; max-width: 240mm;">{escape(narrative.portfolio_commentary)}</p>
    <div class="card-grid" style="margin-top: 8mm;">
      <div class="card"><div class="label">Holdings</div><div class="value">{metrics.n_holdings}</div></div>
      <div class="card"><div class="label">Top-1 weight</div><div class="value">{metrics.concentration_top1:.1f}%</div></div>
      <div class="card"><div class="label">Top-5 weight</div><div class="value">{metrics.concentration_top5:.1f}%</div></div>
      <div class="card"><div class="label">Cash %</div><div class="value">{(100 * metrics.cash / metrics.total_with_cash) if metrics.total_with_cash else 0:.1f}%</div></div>
    </div>
  </div>
  {_footer(n, total, as_of)}
</section>
"""


def _slide_market_commentary(client_name: str, narrative: AdvisorNarrative, as_of: str, n: int, total: int) -> str:
    paragraphs = "\n".join(f"<p>{escape(p)}</p>" for p in narrative.market_commentary.split("\n") if p.strip())
    return f"""
<section class="slide">
  {_header(client_name, "Market context")}
  <div class="slide-body">
    <div class="kicker">05 · Market commentary</div>
    <h2>What matters for you right now</h2>
    <div style="margin-top: 6mm; max-width: 240mm; font-size: 11pt;">{paragraphs}</div>
  </div>
  {_footer(n, total, as_of)}
</section>
"""


def _slide_guide(client_name: str, page_num: int, title: str, data_uri: str, as_of: str, n: int, total: int) -> str:
    return f"""
<section class="slide">
  {_header(client_name, f"Guide · p.{page_num}")}
  <div class="slide-body" style="display: flex; flex-direction: column;">
    <div class="kicker">Market context</div>
    <h2>{escape(title)}</h2>
    <div class="guide-page" style="margin-top: 4mm; flex: 1; display: flex; flex-direction: column; justify-content: center;">
      <img src="{data_uri}" />
    </div>
    <div class="guide-caption">Source: J.P. Morgan — Guide to the Markets (page {page_num})</div>
  </div>
  {_footer(n, total, as_of)}
</section>
"""


def _slide_recommendations(client_name: str, narrative: AdvisorNarrative, as_of: str, n: int, total: int) -> str:
    recs = []
    for r in narrative.recommendations:
        tickers = f"<div class='rec-tickers'>{escape(', '.join(r.tickers))}</div>" if r.tickers else ""
        recs.append(f"""
          <div class="rec {r.priority}">
            <div class="rec-head">
              <div class="rec-title">{escape(r.title)}</div>
              <div class="rec-badge">{escape(r.priority)}</div>
            </div>
            <div class="rec-action">{escape(r.action)}</div>
            <div class="rec-rationale">{escape(r.rationale)}</div>
            {tickers}
          </div>
        """)
    return f"""
<section class="slide">
  {_header(client_name, "Recommendations")}
  <div class="slide-body">
    <div class="kicker">06 · Recommendations</div>
    <h2>Proposed moves</h2>
    <div style="margin-top: 4mm;">{''.join(recs)}</div>
  </div>
  {_footer(n, total, as_of)}
</section>
"""


def _slide_actions(client_name: str, narrative: AdvisorNarrative, as_of: str, n: int, total: int) -> str:
    items = "\n".join(f"<li>{escape(a)}</li>" for a in narrative.action_items)
    return f"""
<section class="slide">
  {_header(client_name, "Next steps")}
  <div class="slide-body">
    <div class="kicker">07 · Action items &amp; next steps</div>
    <h2>What happens from here</h2>
    <ul class="actions" style="margin-top: 8mm; max-width: 220mm;">{items}</ul>
    <p style="margin-top: 18mm; color: rgba(255,255,255,0.80); font-size: 11pt; max-width: 220mm; border-left: 3px solid #69F0AE; padding-left: 6mm;">
      {escape(narrative.closing_note)}
    </p>
  </div>
  {_footer(n, total, as_of)}
</section>
"""


def build_deck_html(
    client: ClientProfile,
    metrics: PortfolioMetrics,
    narrative: AdvisorNarrative,
    guide_pages: list[int],
    as_of_date: str,
) -> tuple[str, list[dict]]:
    """Return (html_string, selected_guide_pages_meta)."""
    sector_chart = charts.bar_sector(metrics.allocation_by_sector)
    pnl_chart = charts.bar_pnl(metrics)
    kpi_img = charts.kpi_strip(metrics)

    # Count total slides up front for footer numbering
    n_guide = len(guide_pages)
    # cover, exec, holdings, allocation, portfolio-commentary, market-commentary, N guide, rec, actions
    total = 8 + n_guide

    # Build guide page meta
    selected_meta: list[dict] = []
    guide_slides = []
    for pg in guide_pages:
        try:
            data_uri = guide_extractor.get_page_data_uri(pg)
        except Exception as e:
            data_uri = ""
            print(f"[guide] page {pg} failed: {e}")
        info = guide_extractor.GUIDE_INDEX.get(pg, {})
        title = info.get("title") or f"Market context · page {pg}"
        selected_meta.append({"page": pg, "title": title})
        if data_uri:
            guide_slides.append((pg, title, data_uri))

    slides_html: list[str] = []
    idx = 1
    slides_html.append(_slide_cover(client, as_of_date, metrics.benchmark)); idx += 1
    slides_html.append(_slide_executive(client.name, kpi_img, narrative, as_of_date, idx, total)); idx += 1
    slides_html.append(_slide_holdings(client.name, metrics, as_of_date, idx, total)); idx += 1
    slides_html.append(_slide_allocation(client.name, sector_chart, pnl_chart, as_of_date, idx, total)); idx += 1
    slides_html.append(_slide_portfolio_commentary(client.name, narrative, metrics, as_of_date, idx, total)); idx += 1
    slides_html.append(_slide_market_commentary(client.name, narrative, as_of_date, idx, total)); idx += 1
    for pg, title, data_uri in guide_slides:
        slides_html.append(_slide_guide(client.name, pg, title, data_uri, as_of_date, idx, total)); idx += 1
    slides_html.append(_slide_recommendations(client.name, narrative, as_of_date, idx, total)); idx += 1
    slides_html.append(_slide_actions(client.name, narrative, as_of_date, idx, total)); idx += 1

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Wealth Review — {escape(client.name)}</title>
<style>{BASE_CSS}</style></head>
<body>{''.join(slides_html)}</body></html>"""
    return html, selected_meta


def render_pdf(html: str, out_path: Path) -> int:
    """Render HTML to PDF and return file size in bytes."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(Path(settings.output_dir))).write_pdf(str(out_path))
    return out_path.stat().st_size
