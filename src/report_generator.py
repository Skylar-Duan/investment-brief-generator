"""
Report generator — renders data + LLM brief into HTML and Markdown files.
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import markdown

_INDUSTRY_ZH = {
    "Automobiles": "汽车", "Technology": "科技", "Software": "软件",
    "Semiconductors": "半导体", "Biotechnology": "生物科技", "Pharmaceuticals": "制药",
    "Financial Services": "金融服务", "Banks": "银行", "Insurance": "保险",
    "Real Estate": "房地产", "Energy": "能源", "Oil & Gas": "石油与天然气",
    "Utilities": "公用事业", "Consumer Cyclical": "消费周期", "Consumer Defensive": "消费必需",
    "Healthcare": "医疗健康", "Industrials": "工业", "Basic Materials": "基础材料",
    "Communication Services": "通信服务", "Retail": "零售", "Transportation": "运输",
    "Aerospace & Defense": "航空航天与国防", "Capital Markets": "资本市场",
    "Asset Management": "资产管理", "Media": "媒体", "Entertainment": "娱乐",
    "Food": "食品", "Beverages": "饮料", "Mining": "矿业", "Steel": "钢铁",
    "Chemicals": "化工", "Construction": "建筑", "Electric Utilities": "电力公用事业",
    "Internet & Direct Marketing Retail": "电子商务",
    "Interactive Media & Services": "互动媒体与服务", "IT Services": "IT服务",
    "Electronic Equipment": "电子设备", "Health Care Equipment": "医疗器械",
    "Specialty Retail": "专业零售", "Road & Rail": "道路与轨道运输", "Uranium": "铀矿",
}
_EXCHANGE_ZH = {
    "NASDAQ NMS - GLOBAL MARKET": "纳斯达克", "NASDAQ NMS - GLOBAL SELECT MARKET": "纳斯达克",
    "NASDAQ CAPITAL MARKET": "纳斯达克", "NASDAQ": "纳斯达克",
    "New York Stock Exchange": "纽约证券交易所", "NYSE": "纽约证券交易所",
    "NYSE MKT": "纽交所MKT", "NYSE ARCA": "纽交所ARCA", "NYSE American": "纽交所美国",
    "AMEX": "美国证券交易所", "OTC": "场外交易", "OTC Markets": "场外交易",
    "Toronto Stock Exchange": "多伦多证券交易所", "London Stock Exchange": "伦敦证券交易所",
    "Hong Kong Stock Exchange": "香港证券交易所",
}
_COUNTRY_ZH = {
    "US": "美国", "CN": "中国", "CA": "加拿大", "GB": "英国", "JP": "日本",
    "KR": "韩国", "DE": "德国", "FR": "法国", "AU": "澳大利亚", "SG": "新加坡",
    "HK": "中国香港", "TW": "中国台湾", "IN": "印度", "BR": "巴西",
    "IL": "以色列", "NL": "荷兰", "SE": "瑞典", "CH": "瑞士", "IE": "爱尔兰",
}


def _parse_sections(brief_text: str) -> dict:
    """Split LLM markdown output into per-section HTML strings."""
    section_map = {
        "executive summary": "executive_summary",
        "key metrics":       "key_metrics",
        "recent catalysts":  "recent_catalysts",
        "risk factors":      "risk_factors",
        "earnings review":   "earnings_review",
        "outlook":           "outlook",
    }
    # Split on ## headers
    parts = re.split(r"(?m)^##\s+", brief_text)
    result = {k: "" for k in section_map.values()}

    for part in parts:
        if not part.strip():
            continue
        first_line, _, body = part.partition("\n")
        key = first_line.strip().lower()
        for pattern, field in section_map.items():
            if pattern in key:
                result[field] = markdown.markdown(body.strip(), extensions=["nl2br"])
                break

    return result


def _build_metrics_cards(data: dict) -> list[dict]:
    """Build the top metric cards from raw data."""
    m = data.get("financials", {}).get("finnhub_metrics", {})
    cards = []
    def card(label, value, sub=None):
        if value is not None:
            cards.append({"label": label, "value": value, "sub": sub or ""})

    card("P/E (TTM)",     f"{m['pe_ttm']:.1f}x"       if m.get("pe_ttm")         else None)
    card("P/B",           f"{m['pb']:.1f}x"            if m.get("pb")             else None)
    card("EPS (TTM)",     f"${m['eps_ttm']:.2f}"       if m.get("eps_ttm")        else None)
    card("ROE (TTM)",     f"{m['roe_ttm']:.1f}%"       if m.get("roe_ttm")        else None)
    card("Gross Margin",  f"{m['gross_margin_ttm']:.1f}%" if m.get("gross_margin_ttm") else None)
    card("Net Margin",    f"{m['net_margin_ttm']:.1f}%"   if m.get("net_margin_ttm")   else None)
    return cards


def generate_html_report(
    ticker: str,
    brief_text: str,
    data: dict,
    model_name: str = "qwen-plus",
    lang: str = "en",
    cn_name: str | None = None,
    template_dir: str | None = None,
) -> tuple[str, str]:
    """
    Render the HTML report and save both HTML and Markdown versions.

    Returns (html_path, md_path).
    """
    ticker = ticker.upper()
    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    generated_date = now.strftime("%Y-%m-%d %H:%M UTC")

    # Output directory
    out_dir = Path(__file__).parent.parent / "output" / ticker
    out_dir.mkdir(parents=True, exist_ok=True)

    # Find next available run index for today to avoid overwriting
    lang_tag = "cn" if lang == "cn" else "en"
    run = 1
    while True:
        suffix = f"_{lang_tag}_{run:02d}"
        html_path = out_dir / f"{date_str}_{ticker}_brief{suffix}.html"
        md_path   = out_dir / f"{date_str}_{ticker}_brief{suffix}.md"
        if not html_path.exists() and not md_path.exists():
            break
        run += 1

    # ── Jinja2 template ──
    if template_dir is None:
        template_dir = str(Path(__file__).parent.parent / "templates")
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
    template = env.get_template("report.html")

    # Profile shortcut
    profile  = data.get("profile", {})
    fin_m    = data.get("financials", {}).get("finnhub_metrics", {})
    prices   = data.get("price_history", [])
    earnings = data.get("earnings", [])
    peers    = data.get("peers", [])

    # Localised display strings
    raw_industry = profile.get("industry", "")
    raw_exchange = profile.get("exchange", "")
    raw_country  = profile.get("country", "")
    if lang == "cn":
        industry_display = _INDUSTRY_ZH.get(raw_industry, raw_industry) or "—"
        exchange_display = _EXCHANGE_ZH.get(raw_exchange, raw_exchange) or "—"
        country_display  = _COUNTRY_ZH.get(raw_country,  raw_country)  or "—"
    else:
        industry_display = raw_industry or "—"
        exchange_display = raw_exchange or "—"
        country_display  = raw_country  or "—"

    # Price stats
    current_price   = prices[-1]["close"] if prices else None
    price_change_3m = None
    if len(prices) >= 2:
        price_change_3m = round(
            (prices[-1]["close"] - prices[0]["close"]) / prices[0]["close"] * 100, 1
        )

    # Market cap in billions
    mktcap_b = None
    if profile.get("market_cap"):
        mktcap_b = f"{profile['market_cap'] / 1000:.1f}"

    # 52W range
    w52h = fin_m.get("52w_high")
    w52l = fin_m.get("52w_low")
    week52_range = f"${w52l} – ${w52h}" if w52h and w52l else None

    context = dict(
        ticker           = ticker,
        lang             = lang,
        company_name     = profile.get("name", ticker),
        cn_name          = cn_name,
        industry         = industry_display,
        exchange         = exchange_display,
        country          = country_display,
        logo_url         = profile.get("logo", ""),
        generated_date  = generated_date,
        generated_year  = now.year,
        data_date       = data.get("fetched_at", date_str)[:10],
        model_name      = model_name,
        current_price   = current_price,
        market_cap      = mktcap_b,
        pe_ttm          = f"{fin_m['pe_ttm']:.1f}" if fin_m.get("pe_ttm") else None,
        week52_range    = week52_range,
        week52_high     = w52h,
        week52_low      = w52l,
        price_change_3m = price_change_3m,
        price_history   = prices,
        earnings        = earnings,
        peers           = peers,
        metrics         = _build_metrics_cards(data),
        sections        = _parse_sections(brief_text),
    )

    html_content = template.render(**context)

    # Save HTML
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Save Markdown
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Investment Brief: {ticker}\n\n")
        f.write(f"**Company:** {profile.get('name', ticker)}  \n")
        f.write(f"**Generated:** {generated_date}  \n")
        f.write(f"**Model:** {model_name}  \n\n")
        f.write("---\n\n")
        f.write(brief_text)

    return str(html_path), str(md_path)
