# Investment Brief Generator

AI-powered investment brief generator — one-click company research reports for US equities, powered by Qwen LLM and market data APIs.

---

## What It Does

Generates a structured, analyst-style investment brief for any US-listed stock in seconds. Instead of manually pulling data from multiple sources, this tool fetches everything automatically and uses an LLM to synthesize it into a clean, readable report.

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

## Architecture

```
main.py
├── src/data_fetcher.py     → Pulls data from Finnhub API + yfinance
├── src/analyzer.py         → Sends structured data to Qwen LLM, returns brief
└── src/report_generator.py → Renders HTML + Markdown report via Jinja2
```

Data flow: `ticker input → fetch → LLM analysis → HTML/MD report`

The LLM is only involved in the analysis step. All data fetching and report rendering is deterministic Python logic.

---

## Data Sources

| Source | Data |
|--------|------|
| [Finnhub](https://finnhub.io) | Company profile, key metrics, earnings, news, analyst price targets, peers |
| [yfinance](https://github.com/ranaroussi/yfinance) | Financial statements, price history |

Both sources are **free tier** — no paid subscription required.

---

## Cost

Using Qwen3-Plus (Alibaba DashScope):

| | Cost |
|---|---|
| Single report | ~$0.002 USD |
| 20-stock watchlist | ~$0.04 USD |

Significantly cheaper than GPT-4 for the same task.

---

## Usage

**Single ticker:**
```bash
python main.py AAPL
python main.py TSLA --lang cn
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
# My watchlist
AAPL
MSFT
NVDA
TSLA
```

---

## Current Limitations

- US equities only (Hong Kong / A-share support planned)
- News limited to last 7 days via Finnhub free tier
- Price target data availability varies by ticker

---

## Built With

- [Finnhub Python Client](https://github.com/Finnhub-Stock-API/finnhub-python)
- [yfinance](https://github.com/ranaroussi/yfinance)
- [Jinja2](https://jinja.palletsprojects.com/)
- [python-markdown](https://python-markdown.github.io/)
- Qwen3-Plus via [DashScope](https://dashscope.aliyuncs.com)

Built with Claude (Anthropic).
