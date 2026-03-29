"""
Investment Brief Generator — main entry point.

Usage:
  python main.py AAPL
  python main.py AAPL TSLA MSFT
  python main.py --watchlist watchlist.txt
"""

import os
import sys
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from src.data_fetcher import fetch_all
from src.analyzer import generate_brief
from src.report_generator import generate_html_report


class DataError(Exception):
    """Raised when fetched data is insufficient to generate a report."""


def _check_env_keys() -> None:
    """Validate required API keys exist before processing any tickers."""
    missing = [k for k in ("DASHSCOPE_API_KEY", "FINNHUB_API_KEY") if not os.environ.get(k)]
    if missing:
        print(f"\nFATAL: Missing API key(s): {', '.join(missing)}")
        print("Create a .env file in the project root:")
        for k in missing:
            print(f"  {k}=your_key_here")
        sys.exit(1)


def process_ticker(ticker: str, model: str = "qwen-plus", lang: str = "en") -> dict:
    """Fetch, analyse, and render one ticker. Returns cost metadata."""
    print(f"\n{'='*60}")
    print(f"  Processing: {ticker.upper()}")
    print(f"{'='*60}")

    # 1. Fetch data
    data = fetch_all(ticker)

    # Validate: empty profile means invalid ticker or all APIs failed
    if not data.get("profile") or not data["profile"].get("name"):
        raise DataError(f"No company data found — invalid ticker or data source unavailable")

    # 2. Generate LLM brief (token/cost info printed inside)
    brief_text, cn_name = generate_brief(data, model=model, lang=lang)

    # 3. Render reports
    html_path, md_path = generate_html_report(
        ticker=ticker,
        brief_text=brief_text,
        data=data,
        model_name=model,
        lang=lang,
        cn_name=cn_name,
    )

    print(f"  HTML: {html_path}")
    print(f"  MD  : {md_path}")
    return {"ticker": ticker, "html": html_path, "md": md_path}


def load_watchlist(path: str) -> list[str]:
    tickers = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for t in line.split(","):
                t = t.strip().upper()
                if t:
                    tickers.append(t)
    return tickers


def main():
    parser = argparse.ArgumentParser(description="Investment Brief Generator")
    parser.add_argument("tickers", nargs="*", help="One or more ticker symbols")
    parser.add_argument("--watchlist", "-w", help="Path to watchlist .txt file")
    parser.add_argument("--model", default="qwen-plus", help="LLM model name (default: qwen-plus)")
    parser.add_argument("--lang", default="en", choices=["en", "cn"], help="Output language: en (default) or cn")
    args = parser.parse_args()

    # Build ticker list
    tickers = []
    if args.watchlist:
        wl_path = Path(args.watchlist)
        if not wl_path.exists():
            print(f"ERROR: watchlist file not found: {wl_path}")
            sys.exit(1)
        tickers = load_watchlist(str(wl_path))
        print(f"Loaded {len(tickers)} tickers from {wl_path}: {', '.join(tickers)}")
    if args.tickers:
        tickers += [t.upper() for t in args.tickers]

    if not tickers:
        parser.print_help()
        sys.exit(0)

    _check_env_keys()

    # Deduplicate while preserving order
    seen = set()
    tickers = [t for t in tickers if not (t in seen or seen.add(t))]

    print(f"\nGenerating briefs for {len(tickers)} ticker(s): {', '.join(tickers)}")

    results = []
    for ticker in tickers:
        try:
            r = process_ticker(ticker, model=args.model, lang=args.lang)
            results.append(r)
        except Exception as e:
            print(f"\n  ERROR processing {ticker}: {e}")
            results.append({"ticker": ticker, "error": str(e)})

    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    ok  = [r for r in results if "error" not in r]
    err = [r for r in results if "error" in r]
    for r in ok:
        print(f"  OK   {r['ticker']:8s}  {r['html']}")
    for r in err:
        print(f"  FAIL {r['ticker']:8s}  {r['error']}")
    print(f"\n  {len(ok)}/{len(results)} reports generated successfully.")


if __name__ == "__main__":
    main()
