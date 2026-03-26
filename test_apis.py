import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import finnhub
from openai import OpenAI

load_dotenv()

# ── Finnhub ──────────────────────────────────────────────────────────────────

def test_finnhub():
    print("=" * 60)
    print("FINNHUB API TEST — AAPL")
    print("=" * 60)

    client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
    symbol = "AAPL"

    # 1. Company profile
    profile = client.company_profile2(symbol=symbol)
    print("\n[1] Company Profile:")
    print(json.dumps(profile, indent=2))

    # 2. Basic financials / fundamentals
    metrics = client.company_basic_financials(symbol, "all")
    # Print only metric keys to keep output manageable
    metric_keys = list(metrics.get("metric", {}).keys())[:20]
    print("\n[2] Basic Financials (first 20 metric keys):")
    print(json.dumps(metric_keys, indent=2))
    print(f"    ... total {len(metrics.get('metric', {}))} metrics available")

    # 3. News — last 7 days
    today = datetime.today().strftime("%Y-%m-%d")
    week_ago = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    news = client.company_news(symbol, _from=week_ago, to=today)
    print(f"\n[3] Company News ({week_ago} → {today}): {len(news)} articles")
    for article in news[:3]:
        print(f"  - [{article.get('datetime', '')}] {article.get('headline', '')[:80]}")

    print("\nFinnhub test PASSED\n")


# ── DashScope via OpenAI-compatible mode ─────────────────────────────────────

def test_dashscope():
    print("=" * 60)
    print("DASHSCOPE (qwen-plus) API TEST")
    print("=" * 60)

    client = OpenAI(
        api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    response = client.chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": "你好，请用一句话介绍自己"}],
    )

    reply = response.choices[0].message.content
    print(f"\nModel reply: {reply}")
    print(f"\nUsage: {response.usage}")
    print("\nDashScope test PASSED\n")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_finnhub()
    test_dashscope()
