"""
Data fetcher module — pulls company data from Finnhub and yfinance.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import finnhub
import yfinance as yf

load_dotenv()

_finnhub_client = None


def _get_client() -> finnhub.Client:
    global _finnhub_client
    if _finnhub_client is None:
        _finnhub_client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
    return _finnhub_client


def _get_yf(ticker: str) -> yf.Ticker:
    """Return a fresh yfinance Ticker — no shared cache to avoid thread contention."""
    return yf.Ticker(ticker)


def _fetch_logo_b64(website: str) -> str:
    """
    Download the company favicon from their official website and return as
    a base64 data URI so the logo is self-contained in the HTML file.
    Tries /favicon.ico first; if 404, parses HTML to find the <link rel="icon">
    path. Falls back to empty string if unreachable.
    """
    if not website:
        return ""
    try:
        import urllib.request, base64, re as _re
        from urllib.parse import urlparse, urljoin

        base_url = website if "://" in website else "https://" + website
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        headers = {"User-Agent": "Mozilla/5.0"}

        def _download(url: str) -> bytes | None:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = resp.read()
                return data if len(data) > 200 else None
            except Exception:
                return None

        def _encode(data: bytes) -> str:
            b64 = base64.b64encode(data).decode()
            # guess mime from magic bytes
            mime = "image/png" if data[:4] == b"\x89PNG" else "image/x-icon"
            return f"data:{mime};base64,{b64}"

        # 1. Try /favicon.ico
        data = _download(f"{origin}/favicon.ico")
        if data:
            return _encode(data)

        # 2. Parse HTML homepage for <link rel="icon"> / <link rel="shortcut icon">
        try:
            req = urllib.request.Request(base_url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read(16384).decode("utf-8", errors="ignore")
            icon_paths = _re.findall(
                r'<link[^>]+rel=["\'](?:shortcut )?icon["\'][^>]+href=["\']([^"\']+)',
                html, _re.I,
            )
            icon_paths += _re.findall(
                r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\'](?:shortcut )?icon["\']',
                html, _re.I,
            )
            for path in icon_paths:
                url = path if path.startswith("http") else urljoin(origin + "/", path.lstrip("/"))
                data = _download(url)
                if data:
                    return _encode(data)
        except Exception:
            pass

    except Exception:
        pass
    return ""


# ── Market detection ──────────────────────────────────────────────────────────

def detect_market(ticker: str) -> str:
    """
    Return "CN", "HK", or "US" based on ticker format.
    Pure digits: 6-digit → A-share (CN), 4-5 digit → H-share (HK).
    Already-suffixed tickers (.SS/.SZ/.HK) respected as-is.
    """
    t = ticker.upper().strip()
    if t.endswith((".SS", ".SZ")):
        return "CN"
    if t.endswith(".HK"):
        return "HK"
    if t.isdigit():
        if len(t) == 6:
            return "CN"
        if len(t) <= 5:
            return "HK"
    return "US"


def normalize_ticker(ticker: str) -> str:
    """
    Add the correct exchange suffix for numeric tickers.
    6-digit A-share: first digit 6 → .SS, else → .SZ
    4-5 digit H-share: pad to 4 digits + .HK
    US/already-suffixed: return uppercase unchanged.
    """
    t = ticker.upper().strip()
    market = detect_market(t)
    if market == "CN" and t.isdigit():
        return f"{t}.SS" if t.startswith("6") else f"{t}.SZ"
    if market == "HK" and t.isdigit():
        return f"{t.zfill(4)}.HK"
    return t


# ── 1. Company profile ────────────────────────────────────────────────────────

def fetch_company_profile(ticker: str) -> dict:
    print(f"  [profile] Fetching company profile for {ticker}...")
    market = detect_market(ticker)

    # Try Finnhub first (works well for US, partial for HK)
    try:
        raw = _get_client().company_profile2(symbol=ticker)
        if raw and raw.get("name"):
            website = raw.get("weburl", "")
            logo = raw.get("logo") or _fetch_logo_b64(website)
            return {
                "name":               raw.get("name"),
                "industry":           raw.get("finnhubIndustry"),
                "exchange":           raw.get("exchange"),
                "currency":           raw.get("currency"),
                "country":            raw.get("country"),
                "ipo":                raw.get("ipo"),
                "market_cap":         raw.get("marketCapitalization"),
                "shares_outstanding": raw.get("shareOutstanding"),
                "website":            website,
                "logo":               logo,
                "phone":              raw.get("phone"),
            }
    except Exception:
        pass

    # Fallback: yfinance .info (reliable for HK; A-shares limited)
    try:
        info = _get_yf(ticker).info or {}
        mktcap_m = None
        if info.get("marketCap"):
            # Keep in the stock's native currency (HKD/CNY/USD).
            # Division by 1e6 → millions (same unit as Finnhub's marketCapitalization).
            mktcap_m = round(info["marketCap"] / 1e6, 2)
        exchange_map = {
            "HKG": "Hong Kong Stock Exchange",
            "SHH": "Shanghai Stock Exchange",
            "SHZ": "Shenzhen Stock Exchange",
        }
        exch_raw = info.get("exchange", "")
        return {
            "name":              info.get("longName") or info.get("shortName", ticker),
            "industry":          info.get("industry", ""),
            "exchange":          exchange_map.get(exch_raw, exch_raw),
            "currency":          info.get("currency", ""),
            "country":           info.get("country", "HK" if market == "HK" else "CN"),
            "ipo":               None,
            "market_cap":        mktcap_m,
            "shares_outstanding":info.get("sharesOutstanding"),
            "website":           info.get("website", ""),
            "logo":              _fetch_logo_b64(info.get("website", "")),
            "phone":             "",
        }
    except Exception as e:
        print(f"  [profile] ERROR: {e}")
        return {}


# ── 2. Financials ─────────────────────────────────────────────────────────────

def fetch_financials(ticker: str) -> dict:
    print(f"  [financials] Fetching fundamentals for {ticker}...")
    result = {}

    # Finnhub basic financials
    try:
        raw = _get_client().company_basic_financials(ticker, "all")
        m = raw.get("metric", {})
        result["finnhub_metrics"] = {
            "pe_ttm": m.get("peNormalizedAnnual"),
            "pb": m.get("pbAnnual"),
            "ps_ttm": m.get("psTTM"),
            "ev_ebitda": m.get("currentEv/freeCashFlowTTM"),
            "eps_ttm": m.get("epsNormalizedAnnual"),
            "roe_ttm": m.get("roeTTM"),
            "roa_ttm": m.get("roaTTM"),
            "debt_equity": m.get("totalDebt/totalEquityAnnual"),
            "current_ratio": m.get("currentRatioAnnual"),
            "gross_margin_ttm": m.get("grossMarginTTM"),
            "net_margin_ttm": m.get("netProfitMarginTTM"),
            "revenue_growth_3y": m.get("revenueGrowth3Y"),
            "eps_growth_3y": m.get("epsGrowth3Y"),
            "52w_high": m.get("52WeekHigh"),
            "52w_low": m.get("52WeekLow"),
            "52w_return": m.get("52WeekPriceReturnDaily"),
            "beta": m.get("beta"),
            "dividend_yield": m.get("dividendYieldIndicatedAnnual"),
        }
    except Exception as e:
        print(f"  [financials] Finnhub ERROR: {e}")
        result["finnhub_metrics"] = {}

    # yfinance financial statements
    try:
        yf_ticker = _get_yf(ticker)

        # Income statement — latest period (rows=metrics, cols=dates)
        income = yf_ticker.financials
        if income is not None and not income.empty:
            col = income.columns[0]
            result["income_statement"] = {
                "period": str(col.date()) if hasattr(col, "date") else str(col),
                "total_revenue": _safe_val(income, ("Total Revenue", col)),
                "gross_profit": _safe_val(income, ("Gross Profit", col)),
                "operating_income": _safe_val(income, ("Operating Income", col)),
                "net_income": _safe_val(income, ("Net Income", col)),
                "ebitda": _safe_val(income, ("EBITDA", col)),
            }
        else:
            result["income_statement"] = {}

        # Balance sheet — latest period
        bs = yf_ticker.balance_sheet
        if bs is not None and not bs.empty:
            col = bs.columns[0]
            result["balance_sheet"] = {
                "period": str(col.date()) if hasattr(col, "date") else str(col),
                "total_assets": _safe_val(bs, ("Total Assets", col)),
                "total_liabilities": _safe_val(bs, ("Total Liabilities Net Minority Interest", col)),
                "stockholders_equity": _safe_val(bs, ("Stockholders Equity", col)),
                "cash_and_equivalents": _safe_val(bs, ("Cash And Cash Equivalents", col)),
                "total_debt": _safe_val(bs, ("Total Debt", col)),
            }
        else:
            result["balance_sheet"] = {}

    except Exception as e:
        print(f"  [financials] yfinance ERROR: {e}")
        result["income_statement"] = {}
        result["balance_sheet"] = {}

    # Supplement finnhub_metrics with yfinance .info when Finnhub returned nothing
    # (A/H stocks: Finnhub 403; keeps US stocks unchanged since they already have data)
    fm = result.get("finnhub_metrics", {})
    if not any(v is not None for v in fm.values()):
        try:
            info = _get_yf(ticker).info or {}
            def _pct(v):
                """Convert decimal ratio to percentage. If yfinance already returned
                a percentage (> 1), use as-is to avoid double-multiplication."""
                if v is None:
                    return None
                return round(v, 2) if abs(v) > 1 else round(v * 100, 2)
            result["finnhub_metrics"] = {
                "pe_ttm":            info.get("trailingPE"),
                "pb":                info.get("priceToBook"),
                "ps_ttm":            None,
                "ev_ebitda":         info.get("enterpriseToEbitda"),
                "eps_ttm":           info.get("trailingEps"),
                "roe_ttm":           _pct(info.get("returnOnEquity")),
                "roa_ttm":           _pct(info.get("returnOnAssets")),
                "debt_equity":       info.get("debtToEquity"),
                "current_ratio":     info.get("currentRatio"),
                "gross_margin_ttm":  _pct(info.get("grossMargins")),
                "net_margin_ttm":    _pct(info.get("profitMargins")),
                "revenue_growth_3y": None,
                "eps_growth_3y":     None,
                "52w_high":          info.get("fiftyTwoWeekHigh"),
                "52w_low":           info.get("fiftyTwoWeekLow"),
                "52w_return":        None,
                "beta":              info.get("beta"),
                "dividend_yield":    _pct(info.get("dividendYield")),
            }
        except Exception as e:
            print(f"  [financials] yfinance metrics fallback ERROR: {e}")

    return result


def _safe_val(df_or_series, key):
    """key is either a plain string (Series lookup) or (row_label, col_label) for DataFrame."""
    try:
        if isinstance(key, tuple):
            row_label, col_label = key
            v = df_or_series.loc[row_label, col_label]
        else:
            v = df_or_series.get(key)
        if v is None:
            return None
        import pandas as pd
        if pd.isna(v):
            return None
        return float(v)
    except Exception:
        return None


# ── 3. News ───────────────────────────────────────────────────────────────────

def _fetch_news_cn(code: str, days: int = 7) -> list[dict]:
    """A-share news via akshare (no API key required)."""
    try:
        import akshare as ak
        # code should be bare 6-digit number, e.g. "600519"
        bare = code.split(".")[0]
        df = ak.stock_news_em(symbol=bare)
        if df is None or df.empty:
            return []
        cutoff = datetime.now() - timedelta(days=days)
        results = []
        for _, row in df.iterrows():
            dt_str = str(row.get("发布时间", ""))
            try:
                dt = datetime.strptime(dt_str[:16], "%Y-%m-%d %H:%M")
                if dt < cutoff:
                    continue
            except Exception:
                pass
            headline = str(row.get("新闻标题", ""))
            summary  = str(row.get("新闻内容", ""))[:300]
            results.append({
                "datetime": dt_str[:16],
                "headline": headline,
                "summary":  summary,
                "source":   str(row.get("文章来源", "")),
                "url":      str(row.get("新闻链接", "")),
            })
        return results[:15]
    except Exception as e:
        print(f"  [news] akshare ERROR: {e}")
        return []


def _fetch_news_hk(ticker: str, days: int = 7) -> list[dict]:
    """HK stock news via yfinance .news."""
    try:
        raw_news = _get_yf(ticker).news or []
        cutoff_ts = (datetime.now() - timedelta(days=days)).timestamp()
        results = []
        for item in raw_news:
            content = item.get("content", {})
            pub_ts = content.get("pubDate", "")
            try:
                from datetime import timezone as _tz
                dt_obj = datetime.fromisoformat(pub_ts.replace("Z", "+00:00"))
                if dt_obj.timestamp() < cutoff_ts:
                    continue
                dt_str = dt_obj.astimezone(_tz(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
            except Exception:
                dt_str = pub_ts[:16]
            title = content.get("title", "")
            summary = content.get("summary", "")[:300]
            provider = content.get("provider", {})
            source = provider.get("displayName", "") if isinstance(provider, dict) else ""
            url = ""
            for link in content.get("canonicalUrl", {}).get("url", ""):
                url = link
                break
            if not url:
                url = content.get("clickThroughUrl", {}).get("url", "") if isinstance(content.get("clickThroughUrl"), dict) else ""
            results.append({
                "datetime": dt_str,
                "headline": title,
                "summary":  summary,
                "source":   source,
                "url":      url,
            })
        return results[:15]
    except Exception as e:
        print(f"  [news] yfinance HK ERROR: {e}")
        return []


def fetch_news(ticker: str, days: int = 7) -> list[dict]:
    print(f"  [news] Fetching last {days} days of news for {ticker}...")
    market = detect_market(ticker)
    if market == "CN":
        return _fetch_news_cn(ticker, days)
    if market == "HK":
        return _fetch_news_hk(ticker, days)
    # US: Finnhub
    try:
        today = datetime.today().strftime("%Y-%m-%d")
        from_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        raw = _get_client().company_news(ticker, _from=from_date, to=today)
        articles = []
        for item in raw:
            articles.append({
                "datetime": datetime.fromtimestamp(item["datetime"]).strftime("%Y-%m-%d %H:%M")
                            if item.get("datetime") else None,
                "headline": item.get("headline"),
                "summary": item.get("summary"),
                "source": item.get("source"),
                "url": item.get("url"),
            })
        return articles
    except Exception as e:
        print(f"  [news] ERROR: {e}")
        return []


# ── 4. Earnings ───────────────────────────────────────────────────────────────

def fetch_earnings(ticker: str) -> list[dict]:
    print(f"  [earnings] Fetching earnings surprises for {ticker}...")
    try:
        raw = _get_client().company_earnings(ticker, limit=4)
        result = []
        for q in raw:
            actual = q.get("actual")
            estimate = q.get("estimate")
            if actual is not None and estimate is not None and estimate != 0:
                beat = "beat" if actual >= estimate else "miss"
                surprise_pct = round((actual - estimate) / abs(estimate) * 100, 2)
            else:
                beat = "n/a"
                surprise_pct = None
            result.append({
                "period": q.get("period"),
                "actual_eps": actual,
                "estimated_eps": estimate,
                "result": beat,
                "surprise_pct": surprise_pct,
            })
        return result
    except Exception as e:
        print(f"  [earnings] ERROR: {e}")
        return []


# ── 5. Peers ──────────────────────────────────────────────────────────────────

def _fetch_peers_cn(ticker: str) -> list[str]:
    """
    A-share sector peers via akshare.
    1. Get the stock's industry from stock_individual_info_em.
    2. Pull all stocks in that industry from stock_board_industry_cons_em.
    3. Return up to 8 peer codes (excluding self).
    """
    try:
        import akshare as ak
        bare = ticker.split(".")[0]

        # Step 1: get industry name for this stock
        info_df = ak.stock_individual_info_em(symbol=bare)
        industry = None
        if info_df is not None and not info_df.empty:
            for _, row in info_df.iterrows():
                if str(row.iloc[0]) in ("行业", "所属行业"):
                    industry = str(row.iloc[1])
                    break

        if not industry:
            return []

        # Step 2: get all stocks in the same industry
        cons_df = ak.stock_board_industry_cons_em(symbol=industry)
        if cons_df is None or cons_df.empty:
            return []

        peers = []
        for _, row in cons_df.iterrows():
            code = str(row.get("代码", "")).strip()
            if code and code != bare:
                peers.append(code)
            if len(peers) >= 8:
                break
        return peers
    except Exception as e:
        print(f"  [peers] akshare ERROR: {e}")
        return []


def fetch_peers(ticker: str) -> list[str]:
    print(f"  [peers] Fetching peer companies for {ticker}...")
    market = detect_market(ticker)
    if market == "CN":
        return _fetch_peers_cn(ticker)
    if market == "HK":
        return []   # no reliable free source for HK peers
    # US: Finnhub
    try:
        return _get_client().company_peers(ticker)
    except Exception as e:
        print(f"  [peers] ERROR: {e}")
        return []


# ── 6. Price target ───────────────────────────────────────────────────────────

def fetch_price_target(ticker: str) -> dict:
    print(f"  [price_target] Fetching analyst price target for {ticker}...")
    try:
        info = _get_yf(ticker).info or {}
        mean   = info.get("targetMeanPrice")
        median = info.get("targetMedianPrice")
        high   = info.get("targetHighPrice")
        low    = info.get("targetLowPrice")
        if not mean:
            print(f"  [price_target] No data available for {ticker}")
            return {}
        return {
            "target_mean":    round(mean,   2),
            "target_median":  round(median, 2) if median else None,
            "target_high":    round(high,   2) if high   else None,
            "target_low":     round(low,    2) if low    else None,
            "analyst_count":  info.get("numberOfAnalystOpinions"),
            "recommendation": info.get("recommendationKey"),
        }
    except Exception as e:
        print(f"  [price_target] ERROR: {e}")
        return {}


# ── 7. Price history ──────────────────────────────────────────────────────────

def fetch_price_history(ticker: str, months: int = 3) -> list[dict]:
    print(f"  [price] Fetching {months}-month price history for {ticker}...")
    try:
        period_map = {1: "1mo", 2: "2mo", 3: "3mo", 6: "6mo", 12: "1y"}
        period = period_map.get(months, f"{months}mo")
        df = _get_yf(ticker).history(period=period)
        if df.empty:
            return []
        records = []
        for date, row in df.iterrows():
            records.append({
                "date": str(date.date()),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })
        return records
    except Exception as e:
        print(f"  [price] ERROR: {e}")
        return []


# ── 8. Fetch all ──────────────────────────────────────────────────────────────

def fetch_all(ticker: str) -> dict:
    ticker = normalize_ticker(ticker)
    market = detect_market(ticker)
    print(f"\nFetching all data for {ticker} (market: {market})...")

    tasks = {
        "profile":       lambda: fetch_company_profile(ticker),
        "financials":    lambda: fetch_financials(ticker),
        "news":          lambda: fetch_news(ticker),
        "earnings":      lambda: fetch_earnings(ticker),
        "peers":         lambda: fetch_peers(ticker),
        "price_target":  lambda: fetch_price_target(ticker),
        "price_history": lambda: fetch_price_history(ticker),
    }

    results: dict = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): key for key, fn in tasks.items()}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    return {
        "ticker": ticker,
        "fetched_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **results,
    }


# ── CLI test ──────────────────────────────────────────────────────────────────

def _summarize(data: dict, indent: int = 0) -> None:
    pad = "  " * indent
    for k, v in data.items():
        if isinstance(v, list):
            print(f"{pad}{k}: [{len(v)} items]")
        elif isinstance(v, dict):
            print(f"{pad}{k}:")
            _summarize(v, indent + 1)
        else:
            print(f"{pad}{k}: {v}")


if __name__ == "__main__":
    result = fetch_all("AAPL")
    print("\n--- Data structure summary ---")
    _summarize(result)
