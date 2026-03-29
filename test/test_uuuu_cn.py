"""
Full-pipeline test for UUUU with --lang cn.
Real API calls (Finnhub + yfinance + DashScope), output saved to test/.

Usage: python test/test_uuuu_cn.py
"""

import sys, os
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.data_fetcher import fetch_all
from src.analyzer import generate_brief
from jinja2 import Environment, FileSystemLoader
import markdown, re
from src.report_generator import (
    _parse_sections, _build_metrics_cards,
    _INDUSTRY_ZH, _EXCHANGE_ZH, _COUNTRY_ZH,
)

TICKER = "UUUU"
LANG   = "cn"
MODEL  = "qwen-plus"

# 1. Fetch
data = fetch_all(TICKER)

# 2. Generate brief
brief_text, cn_name = generate_brief(data, model=MODEL, lang=LANG)

# 3. Render to test/ (bypass normal output/ path)
profile  = data.get("profile", {})
fin_m    = data.get("financials", {}).get("finnhub_metrics", {})
prices   = data.get("price_history", [])
earnings = data.get("earnings", [])
peers    = data.get("peers", [])
pt       = data.get("price_target", {})

now      = datetime.now(tz=timezone.utc)
date_str = now.strftime("%Y-%m-%d")

price_change_3m = None
if len(prices) >= 2:
    price_change_3m = round(
        (prices[-1]["close"] - prices[0]["close"]) / prices[0]["close"] * 100, 1
    )

mktcap_b = f"{profile['market_cap'] / 1000:.1f}" if profile.get("market_cap") else None
w52h = fin_m.get("52w_high")
w52l = fin_m.get("52w_low")

context = dict(
    ticker           = TICKER,
    lang             = LANG,
    company_name     = profile.get("name", TICKER),
    cn_name          = cn_name,
    industry         = _INDUSTRY_ZH.get(profile.get("industry",""), profile.get("industry","—")) or "—",
    exchange         = _EXCHANGE_ZH.get(profile.get("exchange",""), profile.get("exchange","—")) or "—",
    country          = _COUNTRY_ZH.get(profile.get("country",""),  profile.get("country","—"))  or "—",
    logo_url         = profile.get("logo", ""),
    generated_date   = now.strftime("%Y-%m-%d %H:%M UTC"),
    generated_year   = now.year,
    data_date        = data.get("fetched_at", date_str)[:10],
    model_name       = MODEL,
    current_price    = prices[-1]["close"] if prices else None,
    market_cap       = mktcap_b,
    pe_ttm           = f"{fin_m['pe_ttm']:.1f}" if fin_m.get("pe_ttm") else None,
    week52_range     = f"${w52l} – ${w52h}" if w52h and w52l else None,
    week52_high      = w52h,
    week52_low       = w52l,
    price_change_3m  = price_change_3m,
    price_history    = prices,
    earnings         = earnings,
    peers            = peers,
    metrics          = _build_metrics_cards(data),
    sections         = _parse_sections(brief_text),
    price_target     = pt,
)

template_dir = str(Path(__file__).parent.parent / "templates")
env      = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
html     = env.get_template("report.html").render(**context)

out_html = Path(__file__).parent / f"{date_str}_{TICKER}_cn_test.html"
out_md   = Path(__file__).parent / f"{date_str}_{TICKER}_cn_test.md"

out_html.write_text(html, encoding="utf-8")
out_md.write_text(
    f"# Investment Brief: {TICKER}\n\n"
    f"**Company:** {profile.get('name', TICKER)}  \n"
    f"**Chinese Name:** {cn_name or '(none)'}  \n"
    f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}  \n"
    f"**Model:** {MODEL}  \n\n---\n\n{brief_text}",
    encoding="utf-8"
)

print(f"\nHTML: {out_html}")
print(f"MD  : {out_md}")
print(f"Chinese name resolved: {cn_name or '(none — kept English)'}")
