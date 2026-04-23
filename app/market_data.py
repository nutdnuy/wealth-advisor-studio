"""Alpha Vantage client — GLOBAL_QUOTE for prices, OVERVIEW for sectors. File-cached with TTL."""
from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
import httpx
from app.config import settings

BASE_URL = "https://www.alphavantage.co/query"
_cache_dir = Path(settings.cache_dir)
_av_lock = asyncio.Lock()
_last_call_ts = 0.0


def _cache_path(kind: str, key: str) -> Path:
    safe = key.upper().replace("/", "_")
    return _cache_dir / f"{kind}_{safe}.json"


def _load_cache(kind: str, key: str) -> dict | None:
    p = _cache_path(kind, key)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except Exception:
        return None
    if time.time() - data.get("_ts", 0) > settings.price_cache_ttl_seconds and kind == "price":
        return None
    return data


def _save_cache(kind: str, key: str, data: dict) -> None:
    data = {**data, "_ts": time.time()}
    _cache_path(kind, key).write_text(json.dumps(data))


async def _av_get(params: dict) -> dict:
    """Rate-limited GET to Alpha Vantage (spaces calls by av_request_delay_seconds)."""
    global _last_call_ts
    if not settings.alpha_vantage_key:
        raise RuntimeError("WAS_ALPHA_VANTAGE_KEY is not set.")
    params = {**params, "apikey": settings.alpha_vantage_key}
    async with _av_lock:
        now = time.time()
        wait = settings.av_request_delay_seconds - (now - _last_call_ts)
        if wait > 0:
            await asyncio.sleep(wait)
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(BASE_URL, params=params)
            r.raise_for_status()
            data = r.json()
        _last_call_ts = time.time()
    if "Note" in data or "Information" in data:
        raise RuntimeError(data.get("Note") or data.get("Information"))
    return data


async def get_quote(ticker: str) -> dict:
    """Return { price: float, change: float, change_pct: float, ticker: str }."""
    cached = _load_cache("price", ticker)
    if cached:
        return cached
    raw = await _av_get({"function": "GLOBAL_QUOTE", "symbol": ticker})
    q = raw.get("Global Quote", {})
    if not q or not q.get("05. price"):
        raise RuntimeError(f"No quote for {ticker}")
    out = {
        "ticker": ticker,
        "price": float(q["05. price"]),
        "change": float(q.get("09. change", 0) or 0),
        "change_pct": float((q.get("10. change percent", "0%") or "0%").replace("%", "")),
    }
    _save_cache("price", ticker, out)
    return out


async def get_overview(ticker: str) -> dict:
    """Sector / industry / name — cached forever (rare to change)."""
    cached = _load_cache("overview", ticker)
    if cached:
        return cached
    raw = await _av_get({"function": "OVERVIEW", "symbol": ticker})
    out = {
        "ticker": ticker,
        "name": raw.get("Name") or ticker,
        "sector": raw.get("Sector") or "Unknown",
        "industry": raw.get("Industry") or "Unknown",
        "asset_class": "Equity",
    }
    _save_cache("overview", ticker, out)
    return out


async def fetch_bulk(
    tickers: list[str],
    *,
    include_overview: bool = True,
    overrides: dict[str, float] | None = None,
) -> dict[str, dict]:
    """Return { ticker → {price, sector, name, ...} } with partial-failure tolerance."""
    overrides = overrides or {}
    out: dict[str, dict] = {}
    for t in tickers:
        t = t.upper().strip()
        rec: dict = {"ticker": t, "price": None, "sector": "Unknown", "asset_class": "Equity", "error": None}
        if t in overrides:
            rec["price"] = overrides[t]
        else:
            try:
                q = await get_quote(t)
                rec["price"] = q["price"]
            except Exception as e:
                rec["error"] = str(e)
        if include_overview:
            try:
                o = await get_overview(t)
                rec.update({"sector": o["sector"], "name": o["name"], "asset_class": o["asset_class"]})
            except Exception as e:
                rec.setdefault("error", str(e))
        out[t] = rec
    return out
