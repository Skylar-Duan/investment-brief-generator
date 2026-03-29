# Investment Brief Generator — 开发工作日志

---

## V1（初始版本）

**完成时间：** 2026-03 早期
**GitHub 标签：** V1 已发布

### 核心功能
- 美股全流程：公司简介、财务数据、新闻、盈利惊喜、同业、分析师目标价、价格走势
- Finnhub API（美股）+ yfinance（价格/财务补充）+ DashScope/Qwen 分析
- Jinja2 HTML 报告模板（深蓝/白金融风格）
- `--lang cn` 中文输出，含本地中文公司名映射 + LLM fallback
- 并行数据拉取（ThreadPoolExecutor）
- 文件命名：`{date}_{ticker}_brief_{cn|en}_{run:02d}.html`

### V1 已知问题
- 港股/A股：Finnhub 返回 403，大部分数据缺失
- 公司图标：使用 Clearbit（`logo.clearbit.com`），DNS 完全不可解析
- 市值统一显示美元，A股/港股未换算本地货币
- 52周高低：部分市场无数据
- A股/港股 无新闻、无同业数据
- `logo_initial` 用 `ticker[0]`，港股显示"0"，A股显示"6"

---

## V2（当前版本）

**完成时间：** 2026-03-29
**项目路径：** `C:\Users\dbwen\Desktop\开发log\0. AI Engineering\Claude Code\project code\investment-brief-generator`

### 新增 / 修复内容

#### 1. 多市场支持（A股 / 港股 / 美股）
- `detect_market(ticker)`：6位数字→CN，≤5位数字→HK，其余→US
- `normalize_ticker(ticker)`：自动补后缀（.SS/.SZ/.HK）
- 6位首位6→.SS（上交所），其余→.SZ（深交所）

#### 2. 公司图标修复（`_fetch_logo_b64`）
- 彻底替换 Clearbit（DNS 失效）
- 新逻辑：
  1. 先尝试 `domain/favicon.ico`
  2. 404 时解析网站首页 HTML，查找 `<link rel="icon">` 路径
  3. 找到后下载并转为 base64 data URI 内嵌至 HTML
- 修复 `logo_initial`：改用 `(cn_name or company_name)[0]`，中文公司显示"腾""贵"而非"0""6"

#### 3. akshare 接入（A股，无需 API Key）
- `_fetch_news_cn(code, days)`：调用 `ak.stock_news_em()`，返回最近 N 天新闻
- `_fetch_peers_cn(ticker)`：
  1. `ak.stock_individual_info_em()` 获取行业分类
  2. `ak.stock_board_industry_cons_em()` 获取同行业股票列表
  3. 返回最多8家同业公司代码
- `fetch_news` / `fetch_peers` 按市场路由：CN→akshare，HK→yfinance，US→Finnhub

#### 4. 港股新闻（yfinance）
- `_fetch_news_hk(ticker, days)`：调用 yfinance `.news`，解析 content 结构，转换为统一格式

#### 5. 财务指标补全（A/H股 yfinance fallback）
- Finnhub 对 A/H 返回 403 时，改从 yfinance `.info` 补充：
  PE、PB、EV/EBITDA、ROE、ROA、毛利率、净利率、负债率、52周高低、Beta、股息率
- 52周高低：直接用 yfinance `.info["fiftyTwoWeekHigh/Low"]`（盘中价，行业标准），不再从收盘价计算

#### 6. 多币种货币符号
- `data_fetcher.py`：A/H股市值不再换算为美元，直接保留本地货币（HKD/CNY）百万单位
- `report_generator.py`：新增 `_CURRENCY_SYMBOL` 映射，根据 `profile.currency` 确定符号
- `templates/report.html`：所有硬编码 `$` 替换为 `{{ currency_symbol }}`
  - 覆盖：当前价格、市值、52周高低、分析师目标价、EPS 财报表格
- 效果：
  - 美股 → `$`（USD）
  - 港股 → `HK$`（HKD）
  - A股 → `¥`（CNY）

#### 7. 其他修复
- **股息率数据异常**：yfinance 对部分中国股票以百分比返回（如 3.65），`_pct()` 改为：值>1 时直接使用，≤1 时×100
- **线程竞争**：移除 `_yf_cache` 共享缓存，`_get_yf()` 每次返回新 `yf.Ticker` 对象
- **CST 时区**：生成时间戳统一为北京/香港时间（UTC+8）
- **Earnings 空状态**：模板用 `{% if earnings or sections.earnings_review %}` 条件包裹，无数据时整块自动隐藏
- **动态 System Prompt**：`_build_system_prompt(data)` 仅在有 earnings 数据时才在 prompt 中包含财报回顾章节指令

---

## 当前状态（V2）

### 各市场能力对比

| 功能 | 美股 | 港股 | A股 |
|---|---|---|---|
| 公司简介 | ✅ Finnhub | ✅ yfinance | ✅ yfinance |
| 公司图标 | ✅ favicon | ✅ favicon | ✅ favicon（HTML解析） |
| 财务指标 | ✅ Finnhub | ✅ yfinance fallback | ✅ yfinance fallback |
| 52周高低 | ✅ | ✅ | ✅ |
| 价格走势 | ✅ yfinance | ✅ yfinance | ✅ yfinance |
| 新闻 | ✅ Finnhub | ✅ yfinance | ✅ akshare |
| 同业公司 | ✅ Finnhub | ❌（无免费源） | ✅ akshare |
| 盈利惊喜 | ✅ Finnhub | ❌ Finnhub 403 | ❌ Finnhub 403 |
| 分析师目标价 | ✅ yfinance | ✅ yfinance（部分） | ❌ 无数据 |
| 货币符号 | $ USD | HK$ HKD | ¥ CNY |

### API 费用参考（qwen-plus）
- 美股（含新闻+盈利）：~$0.0018/篇
- 港股/A股：~$0.0014/篇

### 待优化（已知 backlog）
- 港股同业（无可靠免费数据源）
- A股/港股 EPS 盈利惊喜（季报历史）
- A股分析师评级（akshare `stock_analyst_forecast_em` 待测试）
- 图标 timeout 偶发失败（部分企业网站海外访问慢）
