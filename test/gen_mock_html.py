"""
Mock HTML generator — zero API calls, renders template with fabricated data.
Usage: python test/gen_mock_html.py
Output: test/mock_NVDA_cn.html
"""

import sys, os
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from jinja2 import Environment, FileSystemLoader
import markdown, re
from datetime import datetime, timezone

# ── Mock data ─────────────────────────────────────────────────────────────────

TICKER   = "NVDA"
CN_NAME  = "英伟达"
LANG     = "cn"

MOCK_DATA = {
    "ticker": TICKER,
    "fetched_at": "2026-03-26T08:00:00Z",
    "profile": {
        "name": "NVIDIA Corporation",
        "industry": "Semiconductors",
        "exchange": "NASDAQ NMS - GLOBAL MARKET",
        "country": "US",
        "market_cap": 2_850_000,   # $M → $2.85T
        "shares_outstanding": 24_440,
        "website": "https://www.nvidia.com",
        "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/NVDA.png",
        "ipo": "1999-01-22",
    },
    "financials": {
        "finnhub_metrics": {
            "pe_ttm": 35.2,
            "pb": 28.6,
            "ps_ttm": 19.4,
            "eps_ttm": 2.94,
            "roe_ttm": 91.5,
            "roa_ttm": 32.1,
            "gross_margin_ttm": 74.6,
            "net_margin_ttm": 55.0,
            "debt_equity": 0.41,
            "current_ratio": 4.17,
            "52w_high": 153.13,
            "52w_low": 75.61,
            "52w_return": 28.4,
            "beta": 1.82,
            "dividend_yield": 0.03,
            "revenue_growth_3y": 68.2,
            "eps_growth_3y": 112.5,
        },
        "income_statement": {
            "period": "2025-01-26",
            "total_revenue":  130_497_000_000,
            "gross_profit":    97_330_000_000,
            "operating_income": 81_530_000_000,
            "net_income":      72_880_000_000,
            "ebitda":          84_200_000_000,
        },
        "balance_sheet": {
            "period": "2025-01-26",
            "total_assets":         111_600_000_000,
            "total_liabilities":     39_500_000_000,
            "stockholders_equity":   72_100_000_000,
            "cash_and_equivalents":  34_800_000_000,
            "total_debt":            8_460_000_000,
        },
    },
    "price_history": [
        {"date": "2025-12-26", "close": 128.30, "volume": 180_000_000},
        {"date": "2026-01-10", "close": 134.20, "volume": 210_000_000},
        {"date": "2026-01-24", "close": 119.80, "volume": 320_000_000},
        {"date": "2026-02-07", "close": 125.50, "volume": 195_000_000},
        {"date": "2026-02-21", "close": 131.90, "volume": 175_000_000},
        {"date": "2026-03-07", "close": 112.40, "volume": 280_000_000},
        {"date": "2026-03-14", "close": 108.60, "volume": 310_000_000},
        {"date": "2026-03-21", "close": 110.21, "volume": 265_000_000},
        {"date": "2026-03-26", "close": 113.26, "volume": 230_000_000},
    ],
    "earnings": [
        {"period": "2025-10-31", "actual_eps": 0.81, "estimated_eps": 0.75, "result": "beat", "surprise_pct": 8.0},
        {"period": "2025-07-31", "actual_eps": 0.68, "estimated_eps": 0.64, "result": "beat", "surprise_pct": 6.3},
        {"period": "2025-04-30", "actual_eps": 0.76, "estimated_eps": 0.88, "result": "miss", "surprise_pct": -13.6},
        {"period": "2025-01-31", "actual_eps": 0.89, "estimated_eps": 0.85, "result": "beat", "surprise_pct": 4.7},
    ],
    "peers": ["AMD", "INTC", "QCOM", "AVGO", "TSM", "AMAT", "MU", "ARM"],
    "price_target": {
        "last_updated": "2026-03-25",
        "symbol": "NVDA",
        "target_high":   195.00,
        "target_low":     98.00,
        "target_mean":   156.40,
        "target_median": 158.00,
    },
    "news": [],
}

# ── Mock brief text (LLM output format, Chinese content) ──────────────────────

MOCK_BRIEF = """## Executive Summary
英伟达凭借在AI加速计算领域的垄断地位，FY2025营收同比增长114%至1305亿美元，净利润率高达55%，ROE达91.5%，展现出平台型护城河的极强盈利能力。然而，当前股价（$113.26）较52周高点已回撤26%，市场估值分歧加剧：一方押注Blackwell架构持续超周期出货，另一方担忧资本开支高峰期后需求侧的可见度不足。短期催化剂与长期结构性机会并存，但估值回落使风险回报比相对改善。

## Key Metrics
- **市盈率（TTM）**：35.2x，低于过去12个月平均（约45x），但仍高于半导体行业均值（约22x）
- **净资产收益率（ROE）**：91.5%，远超同业（AMD：16.2%，英特尔：-5.1%）
- **毛利率**：74.6%，创历史新高，反映Blackwell定价权与产品结构升级
- **净利润率**：55.0%，已超越主要科技巨头（苹果：24%，微软：36%）
- **52周区间**：$75.61 – $153.13，当前价$113.26处于区间中下段
- **分析师目标价均值**：$156.40（较现价上行空间约38%）

## Recent Catalysts
- **Blackwell GB200 NVL72机架持续超预期出货**：CoWoS-L封装产能提升打通供给瓶颈，H20出口管制影响边际收窄
- **大型云厂商资本开支上修**：微软、谷歌、亚马逊2026年AI基础设施预算合计超4000亿美元，NVDA约占数据中心GPU采购的80%以上
- **CUDA生态加速扩张**：NIM微服务平台月活开发者突破500万，软件护城河持续加深，形成不可逆的平台黏性
- **主权AI需求爆发**：沙特、阿联酋、日本、印度等国家级AI基础设施项目密集落地，驱动新一轮地缘需求
- **股票回购计划执行**：FY2025全年回购约195亿美元，维持每股价值提升信号

## Risk Factors
- **美国对华出口管制升级风险**：H20芯片若进入新一轮限制名单，将直接削减约15%的季度营收
- **云厂商资本开支周期性回摆**：2026年下半年若AI投资ROI未达预期，采购节奏或显著放缓
- **竞争格局演变**：AMD MI300X/MI350性能持续追近，谷歌TPU、亚马逊Trainium自研加速，侵蚀部分工作负载份额
- **估值压缩风险**：若宏观利率维持高位或科技股情绪逆转，当前35x PE仍有收缩空间
- **供应链集中度**：台积电CoWoS封装为单一关键节点，任何产能中断将导致季度出货大幅缺口

## Earnings Review
过去四个季度中三次超预期、一次未达预期（FY2026Q1 miss幅度-13.6%，主因数据中心客户消化库存阶段性放缓）。整体趋势：EPS从$0.68→$0.76→$0.81呈上行通道，Q1的miss属于节奏性扰动而非趋势逆转。分析师共识FY2026全年EPS约$3.80-$4.10，对应当前P/E约27-30x，估值已回落至相对合理区间。

## Outlook
综合来看，英伟达的结构性增长逻辑在12-18个月维度仍然成立：AI基础设施投资周期远未见顶，CUDA软件护城河构建的转换成本持续加深，Blackwell→Rubin的架构迭代节奏维持竞争隔离。当前股价较分析师目标价均值折价约28%，提供了较前期追高更优的入场性价比。主要观察指标：FY2026Q2（2026年5月）数据中心营收指引是否重回超预期轨道，以及美国对华AI芯片出口政策的进一步动向。维持积极中性判断，建议逢调整分批布局，止损参考$95关键支撑位。"""

# ── Render ─────────────────────────────────────────────────────────────────────

def parse_sections(brief_text: str) -> dict:
    section_map = {
        "executive summary": "executive_summary",
        "key metrics":       "key_metrics",
        "recent catalysts":  "recent_catalysts",
        "risk factors":      "risk_factors",
        "earnings review":   "earnings_review",
        "outlook":           "outlook",
    }
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

def build_metrics_cards(data: dict) -> list:
    m = data["financials"]["finnhub_metrics"]
    cards = []
    def card(label, value):
        if value is not None:
            cards.append({"label": label, "value": value, "sub": ""})
    card("P/E (TTM)",    f"{m['pe_ttm']:.1f}x")
    card("P/B",          f"{m['pb']:.1f}x")
    card("EPS (TTM)",    f"${m['eps_ttm']:.2f}")
    card("ROE (TTM)",    f"{m['roe_ttm']:.1f}%")
    card("毛利率",        f"{m['gross_margin_ttm']:.1f}%")
    card("净利润率",      f"{m['net_margin_ttm']:.1f}%")
    return cards

# Localise industry / exchange / country
from src.report_generator import _INDUSTRY_ZH, _EXCHANGE_ZH, _COUNTRY_ZH

profile  = MOCK_DATA["profile"]
fin_m    = MOCK_DATA["financials"]["finnhub_metrics"]
prices   = MOCK_DATA["price_history"]
earnings = MOCK_DATA["earnings"]
peers    = MOCK_DATA["peers"]
pt       = MOCK_DATA["price_target"]

now = datetime.now(tz=timezone.utc)
price_change_3m = round(
    (prices[-1]["close"] - prices[0]["close"]) / prices[0]["close"] * 100, 1
)

context = dict(
    ticker           = TICKER,
    lang             = LANG,
    company_name     = profile["name"],
    cn_name          = CN_NAME,
    industry         = _INDUSTRY_ZH.get(profile["industry"], profile["industry"]),
    exchange         = _EXCHANGE_ZH.get(profile["exchange"], profile["exchange"]),
    country          = _COUNTRY_ZH.get(profile["country"],  profile["country"]),
    logo_url         = profile["logo"],
    generated_date   = now.strftime("%Y-%m-%d %H:%M UTC"),
    generated_year   = now.year,
    data_date        = "2026-03-26",
    model_name       = "qwen-plus",
    current_price    = prices[-1]["close"],
    market_cap       = f"{profile['market_cap'] / 1_000:.1f}",
    pe_ttm           = f"{fin_m['pe_ttm']:.1f}",
    week52_range     = f"${fin_m['52w_low']} – ${fin_m['52w_high']}",
    week52_high      = fin_m["52w_high"],
    week52_low       = fin_m["52w_low"],
    price_change_3m  = price_change_3m,
    price_history    = prices,
    earnings         = earnings,
    peers            = peers,
    metrics          = build_metrics_cards(MOCK_DATA),
    sections         = parse_sections(MOCK_BRIEF),
    price_target     = pt,
)

template_dir = str(Path(__file__).parent.parent / "templates")
env      = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
template = env.get_template("report.html")
html     = template.render(**context)

out_path = Path(__file__).parent / "mock_NVDA_cn.html"
out_path.write_text(html, encoding="utf-8")
print(f"Generated: {out_path}")
