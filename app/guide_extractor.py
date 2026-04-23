"""Extract selected pages from Guide to the Markets PDF as high-res images."""
from __future__ import annotations
import base64
import hashlib
from io import BytesIO
from pathlib import Path
from pdf2image import convert_from_path
from pypdf import PdfReader
from app.config import settings

_CACHE = Path(settings.cache_dir) / "guide_pages"
_CACHE.mkdir(parents=True, exist_ok=True)


# Pre-curated page index (based on JPM Guide to the Markets structure).
# 1-indexed page → (title, summary_keywords)
GUIDE_INDEX: dict[int, dict] = {
    4:  {"title": "S&P 500 price index & historical drawdowns",             "tags": ["equity", "us", "valuation"]},
    5:  {"title": "S&P 500 forward P/E & valuation summary",                "tags": ["equity", "us", "valuation"]},
    6:  {"title": "Forward P/E vs subsequent returns",                      "tags": ["equity", "us", "valuation"]},
    7:  {"title": "S&P 500 EPS growth & profit margins",                    "tags": ["equity", "earnings"]},
    8:  {"title": "Top 10 concentration in S&P 500",                        "tags": ["equity", "concentration"]},
    18: {"title": "Fixed income yields & returns",                          "tags": ["fixed-income", "bonds", "yield"]},
    33: {"title": "International equities — valuation gap",                 "tags": ["international", "equity", "ex-us"]},
    45: {"title": "Inflation & interest rates",                             "tags": ["macro", "inflation", "rates"]},
    56: {"title": "Asset class returns (quilt chart)",                      "tags": ["asset-allocation", "returns"]},
    58: {"title": "Diversification & balanced portfolios",                  "tags": ["asset-allocation", "diversification"]},
}


def _total_pages() -> int:
    try:
        return len(PdfReader(settings.guide_pdf_path).pages)
    except Exception:
        return 0


def _key_for(page_num: int) -> str:
    pdf_path = settings.guide_pdf_path
    h = hashlib.md5(f"{pdf_path}:{page_num}".encode()).hexdigest()[:10]
    return f"p{page_num:03d}_{h}.png"


def get_page_image_bytes(page_num: int) -> bytes:
    """Return PNG bytes for a page (1-indexed). Cached on disk."""
    cache_path = _CACHE / _key_for(page_num)
    if cache_path.exists():
        return cache_path.read_bytes()
    imgs = convert_from_path(
        settings.guide_pdf_path,
        first_page=page_num,
        last_page=page_num,
        dpi=150,
    )
    if not imgs:
        raise RuntimeError(f"Could not render guide page {page_num}")
    buf = BytesIO()
    imgs[0].save(buf, format="PNG", optimize=True)
    data = buf.getvalue()
    cache_path.write_bytes(data)
    return data


def get_page_data_uri(page_num: int) -> str:
    b = get_page_image_bytes(page_num)
    return "data:image/png;base64," + base64.b64encode(b).decode()


def auto_select_pages(sector_allocation: dict[str, float], asset_class: dict[str, float]) -> list[int]:
    """Pick 3 most relevant guide pages based on portfolio tilt."""
    chosen: list[int] = []

    # Always include valuation + forward P/E if any equity exposure
    if asset_class.get("Equity", 0) > 10:
        chosen += [5, 6]  # Valuation summary + Forward P/E vs returns

    # If top-10 tech-ish concentration heavy → add top-10 slide
    tech = sector_allocation.get("Information Technology", 0) + sector_allocation.get("Communication Services", 0)
    if tech > 25:
        chosen.append(8)

    # If fixed income exposure → add bond slide
    if asset_class.get("Fixed Income", 0) > 5 or asset_class.get("Bond", 0) > 5:
        chosen.append(18)

    # Always add asset class returns / diversification as closer
    chosen.append(56)

    # De-dupe preserving order, cap at 4
    seen = set()
    out = []
    for p in chosen:
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
        if len(out) >= 4:
            break
    return out
