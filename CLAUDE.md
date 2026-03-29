# Investment Brief Generator — Claude Session Log

## 项目概述
自动生成股票投资研究报告。输入 ticker，输出 HTML/Markdown 报告。
- 数据源：Finnhub API + yfinance
- LLM：阿里 Qwen-Plus（DashScope API）
- 成本：约 $0.002/份报告

## 核心命令
```bash
python main.py AAPL              # 单个，英文
python main.py AAPL --lang cn   # 中文
python main.py --watchlist watchlist.txt  # 批量
python test_apis.py              # 验证 API 连通性
```

## 文件结构
```
main.py                    # 入口（未修改）
src/data_fetcher.py        # Finnhub + yfinance 数据获取（未修改）
src/analyzer.py            # Qwen LLM 分析（未修改）
src/report_generator.py    # HTML/MD 渲染（未修改）
templates/report.html      # Jinja2 模板（未修改）
requirements.txt           # 依赖（加了 markdown）
.github/workflows/test.yml # CI 流水线（新增）
test-results/latest.log    # 最新 CI 运行结果（CI 自动写入）
ci-output/                 # 最新生成的报告 HTML（CI 自动写入）
```

## 本地运行前提
根目录需要 `.env` 文件（不提交 Git）：
```
FINNHUB_API_KEY=your_key
DASHSCOPE_API_KEY=your_key
```

## GitHub Actions CI
- 触发：push 到 main 或 claude/** 分支
- Secrets 配置在：repo Settings → Secrets → Actions
  - `FINNHUB_API_KEY`
  - `DASHSCOPE_API_KEY`
- 结果写入：`test-results/latest.log`（Claude 可直接读取）
- 报告写入：`ci-output/`（Claude 可直接读取 HTML）

## 已知限制
- Finnhub 免费账号无分析师目标价（403 错误，非致命，报告仍生成）
- Finnhub 免费档新闻限 7 天、rate limit 60次/分钟
- 批量处理多 ticker 无限速逻辑（未来可加 time.sleep）

## Session 历史（2026-03-28/29）
### 本次 session 做了什么
1. 项目评审：代码质量 8/10，架构清晰
2. 讨论了云端开发工作流（GitHub Actions + Codespaces）
3. 新增 GitHub Actions CI 流水线（`.github/workflows/test.yml`）
4. 修复 `requirements.txt` 漏写 `markdown` 依赖
5. 实现 CI 结果自动回写 repo，让 Claude 跨 session 可读
6. 完整跑通：API 测试 PASS + AAPL 报告生成 PASS

### 变更文件清单
| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `requirements.txt` | 修改 | 加了 `markdown` |
| `.github/workflows/test.yml` | 新增 | CI 流水线 |
| `CLAUDE.md` | 新增 | 本文件 |
| `test-results/latest.log` | 新增（CI生成） | 运行日志 |
| `ci-output/` | 新增（CI生成） | HTML 报告 |

### 未修改的源码文件
- `main.py`
- `src/data_fetcher.py`
- `src/analyzer.py`
- `src/report_generator.py`
- `templates/report.html`
- `.gitignore`
- `watchlist.txt`
- `test_apis.py`

## 下一步（待完成）
- [ ] 验证 `ci-output/` HTML 报告可被 Claude 正确读取
- [ ] 考虑把 main branch 合并这次 CI 配置
