"""
Data fetcher module — pulls company data from Finnhub and yfinance.
"""

import os
from datetime import datetime, timedelta
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


# ── 1. Company profile ────────────────────────────────────────────────────────

def fetch_company_profile(ticker: str) -> dict:
    print(f"  [profile] Fetching company profile for {ticker}...")
    try:
        raw = _get_client().company_profile2(symbol=ticker)
        return {
            "name": raw.get("name"),
            "industry": raw.get("finnhubIndustry"),
            "exchange": raw.get("exchange"),
            "currency": raw.get("currency"),
            "country": raw.get("country"),
            "ipo": raw.get("ipo"),
            "market_cap": raw.get("marketCapitalization"),
            "shares_outstanding": raw.get("shareOutstanding"),
            "website": raw.get("weburl"),
            "logo": raw.get("logo"),
            "phone": raw.get("phone"),
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
        yf_ticker = yf.Ticker(ticker)

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

def fetch_news(ticker: str, days: int = 7) -> list[dict]:
    print(f"  [news] Fetching last {days} days of news for {ticker}...")
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

def fetch_peers(ticker: str) -> list[str]:
    print(f"  [peers] Fetching peer companies for {ticker}...")
    try:
        return _get_client().company_peers(ticker)
    except Exception as e:
        print(f"  [peers] ERROR: {e}")
        return []


# ── 6. Price target ───────────────────────────────────────────────────────────

def fetch_price_target(ticker: str) -> dict:
    print(f"  [price_target] Fetching analyst price target for {ticker}...")
    try:
        raw = _get_client().price_target(ticker)
        return {
            "last_updated": raw.get("lastUpdated"),
            "symbol": raw.get("symbol"),
            "target_high": raw.get("targetHigh"),
            "target_low": raw.get("targetLow"),
            "target_mean": raw.get("targetMean"),
            "target_median": raw.get("targetMedian"),
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
        df = yf.Ticker(ticker).history(period=period)
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
    print(f"\nFetching all data for {ticker.upper()}...")
    ticker = ticker.upper()
    return {
        "ticker": ticker,
        "fetched_at": datetime.now(tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": fetch_company_profile(ticker),
        "financials": fetch_financials(ticker),
        "news": fetch_news(ticker),
        "earnings": fetch_earnings(ticker),
        "peers": fetch_peers(ticker),
        "price_target": fetch_price_target(ticker),
        "price_history": fetch_price_history(ticker),
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
