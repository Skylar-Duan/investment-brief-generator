# Investment Brief Generator

AI-powered investment brief generator — one-click company research reports for US, Hong Kong, and A-share equities, powered by Qwen LLM and market data APIs.

---

## What It Does

Generates a structured, analyst-style investment brief for any listed stock in seconds. Instead of manually pulling data from multiple sources, this tool fetches everything automatically and uses an LLM to synthesize it into a clean, readable report.

**Output includes:**
- Executive summary and investment thesis
- Key valuation metrics (P/E, P/B, ROE, margins)
- Recent news and catalysts
- Earnings history (beat/miss vs. estimate, last 4 quarters)
- Analyst price target consensus
- Risk factors and forward outlook
- 3-month price chart

Supports both English and Simplified Chinese output.

---

## Market Coverage (V2)

| Feature | US Equities | HK Stocks | A-Shares (CN) |
|---------|-------------|-----------|---------------|
| Company profile | ✅ Finnhub | ✅ yfinance | ✅ yfinance |
| Company logo | ✅ favicon | ✅ favicon | ✅ favicon |
| Key metrics | ✅ Finnhub | ✅ yfinance | ✅ yfinance |
| 52-week high/low | ✅ | ✅ | ✅ |
| Price history | ✅ yfinance | ✅ yfinance | ✅ yfinance |
| News | ✅ Finnhub | ✅ yfinance | ✅ akshare |
| Peer companies | ✅ Finnhub | ❌ | ✅ akshare |
| Earnings surprises | ✅ Finnhub | ❌ | ❌ |
| Analyst price target | ✅ yfinance | ✅ yfinance (partial) | ❌ |
| Currency display | $ USD | HK$ HKD | ¥ CNY |

**Ticker input:** numeric tickers are auto-detected and suffixed.
- `600519` → `600519.SS` (Shanghai)
- `000858` → `000858.SZ` (Shenzhen)
- `0700` or `700` → `0700.HK` (Hong Kong)
- `AAPL`, `TSLA` → US (no change)

---

## Architecture

```
main.py
├── src/data_fetcher.py     → Pulls data (Finnhub / yfinance / akshare), parallel fetch
├── src/analyzer.py         → Sends structured data to Qwen LLM, returns brief
└── src/report_generator.py → Renders HTML + Markdown report via Jinja2
```

Data flow: `ticker input → detect market → fetch (parallel) → LLM analysis → HTML/MD report`

The LLM is only involved in the analysis step. All data fetching and report rendering is deterministic Python logic.

---

## Data Sources

| Source | Used For |
|--------|----------|
| [Finnhub](https://finnhub.io) | US: profile, metrics, earnings, news, peers, price targets |
| [yfinance](https://github.com/ranaroussi/yfinance) | All markets: price history, financials; HK/CN: profile, metrics fallback, news |
| [akshare](https://github.com/jindaxiang/akshare) | A-shares: news, peer companies (no API key required) |

All sources are **free tier** — no paid subscription required.

---

## Cost

Using Qwen-Plus (Alibaba DashScope):

| | Cost |
|---|---|
| US report (with earnings + news) | ~$0.0018 USD |
| HK / A-share report | ~$0.0014 USD |
| 20-stock watchlist | ~$0.03–0.04 USD |

---

## Usage

**Single ticker:**
```bash
python main.py AAPL
python main.py TSLA --lang cn
python main.py 0700          # HKEX: Tencent
python main.py 600519        # SSE: Kweichow Moutai
```

**Multiple tickers:**
```bash
python main.py AAPL MSFT NVDA
```

**Watchlist file:**
```bash
python main.py --watchlist watchlist.txt
python main.py --watchlist watchlist.txt --lang cn
```

Reports are saved to `output/<TICKER>/` as both `.html` and `.md`.

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/Skylar-Duan/investment-brief-generator.git
cd investment-brief-generator
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Configure API keys**

Create a `.env` file in the project root:
```
FINNHUB_API_KEY=your_finnhub_key
DASHSCOPE_API_KEY=your_dashscope_key
```

Get your keys:
- Finnhub: https://finnhub.io (free tier)
- DashScope (Qwen): https://dashscope.aliyuncs.com

**4. Run**
```bash
python main.py AAPL
```

---

## Watchlist Format

Plain text file, one ticker per line. Lines starting with `#` are ignored.

```
# US
AAPL
MSFT
# HK
0700
# A-share
600519
```

---

## Known Limitations

- HK peer companies: no reliable free data source
- A-share / HK earnings surprises: Finnhub 403 for non-US tickers
- A-share analyst price targets: no free data source
- Logo download may timeout for sites with slow international access

---

## Built With

- [Finnhub Python Client](https://github.com/Finnhub-Stock-API/finnhub-python)
- [yfinance](https://github.com/ranaroussi/yfinance)
- [akshare](https://github.com/jindaxiang/akshare)
- [Jinja2](https://jinja.palletsprojects.com/)
- [python-markdown](https://python-markdown.github.io/)
- Qwen-Plus via [DashScope](https://dashscope.aliyuncs.com)

Built with Claude (Anthropic).
