"""
LLM analysis module — converts raw data into a structured investment brief.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# qwen-plus pricing (USD per 1K tokens, as of 2025)
_PRICE_INPUT = 0.0004
_PRICE_OUTPUT = 0.0012

# Local ticker → Chinese name table (Plan B: zero-cost lookup)
_CN_NAME_MAP = {
    "AAPL": "苹果公司", "MSFT": "微软", "GOOGL": "谷歌", "GOOG": "谷歌",
    "AMZN": "亚马逊", "TSLA": "特斯拉", "NVDA": "英伟达", "META": "Meta",
    "AVGO": "博通", "INTC": "英特尔", "QCOM": "高通", "AMD": "超威半导体",
    "CSCO": "思科", "TXN": "德州仪器", "MU": "美光科技", "AMAT": "应用材料",
    "LRCX": "泛林集团", "ASML": "阿斯麦", "TSM": "台积电", "ARM": "Arm Holdings",
    "BABA": "阿里巴巴", "JD": "京东", "PDD": "拼多多", "BIDU": "百度",
    "NIO": "蔚来", "LI": "理想汽车", "XPEV": "小鹏汽车",
    "JPM": "摩根大通", "BAC": "美国银行", "GS": "高盛", "MS": "摩根士丹利",
    "WMT": "沃尔玛", "COST": "好市多", "MCD": "麦当劳", "SBUX": "星巴克",
    "KO": "可口可乐", "PEP": "百事可乐", "DIS": "迪士尼",
    "PFE": "辉瑞", "JNJ": "强生", "AMGN": "安进",
    "V": "Visa", "MA": "万事达", "PYPL": "PayPal",
    "BA": "波音", "GE": "通用电气", "GM": "通用汽车", "F": "福特汽车",
    "UBER": "优步", "NFLX": "奈飞", "ADBE": "Adobe", "CRM": "Salesforce",
    "IBM": "IBM", "HPQ": "惠普", "DELL": "戴尔",
    "PLTR": "Palantir", "SNOW": "Snowflake",
}

_SYSTEM_PROMPT_TEMPLATE = """\
You are a professional equity research analyst. Given structured company data,
produce a concise investment brief in the following exact sections. Be factual, analytical, and direct.

Output format (use these exact section headers):

## Executive Summary
2-3 sentences capturing the investment thesis and current situation.

## Key Metrics
List the most important valuation and performance metrics. Compare PE and ROE to industry peers where possible.

## Recent Catalysts
3-5 bullet points of key recent developments from news and earnings that could drive the stock.

## Risk Factors
3-5 bullet points of the most significant risks investors should monitor.
{earnings_section}
## Outlook
One paragraph with a balanced forward-looking assessment based on all available data."""

_EARNINGS_SECTION = """\

## Earnings Review
Summarize the last 4 quarters of EPS performance (beat/miss vs. estimate), note the trend."""


def _build_system_prompt(data: dict) -> str:
    """Build system prompt, including Earnings Review only if data is available."""
    earnings_section = _EARNINGS_SECTION if data.get("earnings") else ""
    return _SYSTEM_PROMPT_TEMPLATE.format(earnings_section=earnings_section)


def _build_prompt(data: dict) -> str:
    """Assemble a compact, token-efficient prompt from the raw data dict."""
    lines = []
    ticker = data.get("ticker", "N/A")
    lines.append(f"COMPANY DATA FOR {ticker}")
    lines.append("=" * 50)

    # Profile
    p = data.get("profile", {})
    if p:
        lines.append("\n[COMPANY PROFILE]")
        lines.append(f"Name: {p.get('name')} | Industry: {p.get('industry')} | Exchange: {p.get('exchange')}")
        lines.append(f"Country: {p.get('country')} | IPO: {p.get('ipo')} | Website: {p.get('website')}")
        mktcap = p.get("market_cap")
        if mktcap:
            lines.append(f"Market Cap: ${mktcap:,.0f}M | Shares Outstanding: {p.get('shares_outstanding')}M")

    # Key metrics
    fin = data.get("financials", {})
    m = fin.get("finnhub_metrics", {})
    if m:
        lines.append("\n[KEY METRICS]")
        lines.append(f"P/E (TTM): {m.get('pe_ttm')} | P/B: {m.get('pb')} | P/S (TTM): {m.get('ps_ttm')}")
        lines.append(f"EPS (TTM): ${m.get('eps_ttm')} | ROE (TTM): {m.get('roe_ttm')}% | ROA (TTM): {m.get('roa_ttm')}%")
        lines.append(f"Gross Margin: {m.get('gross_margin_ttm')}% | Net Margin: {m.get('net_margin_ttm')}%")
        lines.append(f"Debt/Equity: {m.get('debt_equity')} | Current Ratio: {m.get('current_ratio')}")
        lines.append(f"52W High: ${m.get('52w_high')} | 52W Low: ${m.get('52w_low')} | 52W Return: {m.get('52w_return')}%")
        lines.append(f"Beta: {m.get('beta')} | Dividend Yield: {m.get('dividend_yield')}%")
        lines.append(f"Revenue Growth (3Y): {m.get('revenue_growth_3y')}% | EPS Growth (3Y): {m.get('eps_growth_3y')}%")

    # Income statement
    inc = fin.get("income_statement", {})
    if inc:
        lines.append("\n[INCOME STATEMENT (latest annual)]")
        def fmt_b(v):
            return f"${v/1e9:.1f}B" if v else "N/A"
        lines.append(f"Revenue: {fmt_b(inc.get('total_revenue'))} | Gross Profit: {fmt_b(inc.get('gross_profit'))}")
        lines.append(f"Operating Income: {fmt_b(inc.get('operating_income'))} | Net Income: {fmt_b(inc.get('net_income'))}")
        lines.append(f"EBITDA: {fmt_b(inc.get('ebitda'))} | Period: {inc.get('period')}")

    # Balance sheet
    bs = fin.get("balance_sheet", {})
    if bs:
        lines.append("\n[BALANCE SHEET (latest annual)]")
        def fmt_b(v):
            return f"${v/1e9:.1f}B" if v else "N/A"
        lines.append(f"Total Assets: {fmt_b(bs.get('total_assets'))} | Total Debt: {fmt_b(bs.get('total_debt'))}")
        lines.append(f"Stockholders Equity: {fmt_b(bs.get('stockholders_equity'))} | Cash: {fmt_b(bs.get('cash_and_equivalents'))}")

    # Price context
    prices = data.get("price_history", [])
    if prices:
        latest = prices[-1]
        oldest = prices[0]
        pct = ((latest["close"] - oldest["close"]) / oldest["close"] * 100)
        lines.append("\n[PRICE HISTORY]")
        lines.append(f"Current Price: ${latest['close']} ({latest['date']})")
        lines.append(f"3-Month Change: {pct:+.1f}% (from ${oldest['close']} on {oldest['date']})")

    # Earnings
    earnings = data.get("earnings", [])
    if earnings:
        lines.append("\n[EARNINGS (last 4 quarters)]")
        for q in earnings:
            beat_str = q.get("result", "n/a").upper()
            surp = q.get("surprise_pct")
            surp_str = f"({surp:+.1f}%)" if surp is not None else ""
            lines.append(
                f"  {q.get('period')}: Actual EPS ${q.get('actual_eps')} vs Est ${q.get('estimated_eps')} "
                f"-> {beat_str} {surp_str}"
            )

    # Price target
    pt = data.get("price_target", {})
    if pt and pt.get("target_mean"):
        lines.append("\n[ANALYST PRICE TARGET]")
        parts = [
            f"Mean: ${pt.get('target_mean')}",
            f"Median: ${pt.get('target_median')}",
            f"High: ${pt.get('target_high')}",
            f"Low: ${pt.get('target_low')}",
        ]
        if pt.get("analyst_count"):
            parts.append(f"Analysts: {pt['analyst_count']}")
        if pt.get("recommendation"):
            parts.append(f"Consensus: {pt['recommendation'].replace('_',' ')}")
        lines.append(" | ".join(parts))

    # Peers
    peers = data.get("peers", [])
    if peers:
        lines.append(f"\n[PEER COMPANIES]: {', '.join(peers[:8])}")

    # News — top 10 only
    news = data.get("news", [])[:10]
    if news:
        lines.append("\n[RECENT NEWS (latest 10 headlines)]")
        for i, article in enumerate(news, 1):
            headline = (article.get("headline") or "")[:120]
            summary = (article.get("summary") or "")[:150]
            date = article.get("datetime", "")[:10]
            lines.append(f"  {i}. [{date}] {headline}")
            if summary and summary.lower() != headline.lower():
                lines.append(f"     Summary: {summary}")

    return "\n".join(lines)


def generate_brief(data: dict, model: str = "qwen-plus", lang: str = "en") -> str:
    """
    Generate an investment brief from fetch_all() output.

    Args:
        lang: "en" (default) or "cn" — append Chinese instruction to system prompt.

    Returns the LLM's text output. Prints token usage and estimated cost.
    """
    client = OpenAI(
        api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    ticker = data.get("ticker", "UNKNOWN")
    cn_name = None
    base_prompt = _build_system_prompt(data)   # data-aware: includes Earnings Review only if data exists
    if lang == "cn":
        cn_name = _CN_NAME_MAP.get(ticker)
        lang_instruction = (
            "\n\nLANGUAGE INSTRUCTION (highest priority): "
            "Keep the exact English section headers (## Executive Summary, ## Key Metrics, etc.), "
            "but write ALL body content — every sentence, bullet point, and number explanation — in Simplified Chinese."
        )
        if cn_name:
            # Plan B: name known locally, no need to ask LLM
            system_prompt = base_prompt + lang_instruction
        else:
            # Plan C: ask LLM for Chinese name
            system_prompt = base_prompt + lang_instruction + (
                "\n\nADDITIONAL OUTPUT: Before the ## Executive Summary section, output exactly one line:\n"
                "CHINESE_NAME: [该公司在中文金融媒体中广泛使用的中文名称，如苹果、特斯拉、英伟达、博通。"
                "若该公司在中文环境中无公认中文名（如 Oracle、Energy Fuels Inc、Ryde Group Ltd），则直接输出英文原名。"
                "禁止强行翻译或自造名称。]"
            )
    else:
        system_prompt = base_prompt

    print(f"[analyzer] Building prompt for {ticker}...")
    user_prompt = _build_prompt(data)

    # Rough token estimate (1 token ≈ 4 chars for English)
    estimated_input = (len(user_prompt) + len(system_prompt)) // 4
    print(f"[analyzer] Estimated input tokens: ~{estimated_input}")
    if estimated_input > 3500:
        print(f"[analyzer] WARNING: prompt may exceed 3000 token target ({estimated_input} est.)")

    print(f"[analyzer] Calling {model}...")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    usage = response.usage
    input_tokens = usage.prompt_tokens
    output_tokens = usage.completion_tokens
    cost_usd = (input_tokens / 1000 * _PRICE_INPUT) + (output_tokens / 1000 * _PRICE_OUTPUT)

    print(f"[analyzer] Tokens — input: {input_tokens}, output: {output_tokens}, total: {input_tokens + output_tokens}")
    print(f"[analyzer] Estimated cost: ${cost_usd:.4f} USD")

    content = response.choices[0].message.content

    # Plan C: parse CHINESE_NAME line if we asked for it
    if lang == "cn" and cn_name is None:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("CHINESE_NAME:"):
                cn_name = line.strip().replace("CHINESE_NAME:", "").strip()
                lines.pop(i)
                while lines and not lines[0].strip():
                    lines.pop(0)
                content = "\n".join(lines)
                break

    return content, cn_name


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os
    # Force UTF-8 output on Windows to handle emoji/unicode from LLM
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from src.data_fetcher import fetch_all

    data = fetch_all("AAPL")
    print("\n" + "=" * 60)
    print("INVESTMENT BRIEF")
    print("=" * 60 + "\n")
    brief = generate_brief(data)
    print(brief)
