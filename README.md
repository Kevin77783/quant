# 多市场股票量化交易系统

这是一个面向实盘研究流程的 Python 量化系统骨架，覆盖 A 股、港股、美股的行情接入、技术指标、因子打分、策略信号、回测、风控工具和命令行入口。核心功能不依赖网络，默认可用 `data/sample_prices.csv` 直接运行；安装可选依赖后可接入在线行情。

## 快速开始

推荐使用 Conda：

```bash
conda env create -f environment.yml
conda activate quant
python -m quant_system.cli doctor
python -m quant_system.cli analyze --symbol 000001.SZ --market cn --data-file data/sample_prices.csv
python -m quant_system.cli backtest --symbol AAPL --market us --data-file data/sample_prices.csv --strategy ma
python -m quant_system.cli screen --config configs/default.yaml --data-file data/sample_prices.csv
python -m quant_system.cli portfolio --config configs/default.yaml --data-file data/sample_prices.csv
python -m quant_system.cli compare --config configs/default.yaml --data-file data/sample_prices.csv
python -m quant_system.cli alerts --config configs/default.yaml --data-file data/sample_prices.csv --include-all
python -m quant_system.cli optimize --symbol AAPL --market us --data-file data/sample_prices.csv
python examples/basic_workflow.py
```

如果环境已经存在，更新即可：

```bash
conda env update -f environment.yml --prune
conda activate quant
pip install -e ".[dev]"
```

也可以使用普通虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m quant_system.cli doctor
python -m quant_system.cli analyze --symbol 000001.SZ --market cn --data-file data/sample_prices.csv
python -m quant_system.cli backtest --symbol AAPL --market us --data-file data/sample_prices.csv --strategy ma
python -m quant_system.cli screen --config configs/default.yaml --data-file data/sample_prices.csv
python examples/basic_workflow.py
```

如果需要在线行情：

```bash
conda activate quant
python -m quant_system.cli analyze --symbol 000001.SZ --market cn --provider auto
python -m quant_system.cli analyze --symbol 0700.HK --market hk --provider auto
python -m quant_system.cli analyze --symbol AAPL --market us --provider yahoo
```

Conda 环境已经包含 `akshare`、`yfinance` 和 Streamlit。普通虚拟环境如需在线行情，运行 `pip install -e ".[data,dev]"`。

`--provider auto` 会优先尝试在线源，成功后写入 `data/raw/` 和 `data/processed/`；在线源不可用时再读取缓存，最后才回退到 `--data-file` 指定的本地 CSV。要强制在线美股数据，用 `--provider yahoo`；要强制本地样例数据，用 `--provider csv`。

## 支持市场与代码格式

| 市场 | `--market` | 示例代码 | 默认在线源 |
|---|---:|---|---|
| A 股 | `cn` | `000001.SZ`, `600519.SH`, `430047.BJ` | `akshare` |
| 港股 | `hk` | `0700.HK`, `9988.HK` | `yfinance`，备选 `akshare` |
| 美股 | `us` | `AAPL`, `MSFT`, `SPY` | `yfinance` |

## 主要能力

- 数据层：统一 OHLCV 字段，支持本地 CSV、AkShare、Yahoo Finance，在线源失败时会给出清晰错误。
- 数据缓存：在线数据自动写入 `data/raw/` 和 `data/processed/`，便于复现实验和减少重复请求。
- 数据校验：检查缺失字段、无效日期、非正价格、负成交量、OHLC 高低价关系错误。
- 分析层：收益率、均线、EMA、RSI、MACD、布林带、ATR、波动率、回撤、夏普等指标。
- 多因子：趋势、20/60 日动量、波动率、流动性、RSI 平衡、MACD、ATR、回撤综合打分。
- 策略层：均线交叉、RSI 均值回归、Donchian 突破，策略输出统一为目标仓位。
- 回测层：下一交易日执行信号，包含佣金、滑点、换手成本、权益曲线、交易明细和绩效指标。
- 组合回测：按多因子分数定期选 Top N，支持等权和逆波动率加权。
- 多标的对比：输出标准化走势、风险收益摘要和收益相关性矩阵。
- 预警扫描：按综合分、RSI、回撤、20 日动量和趋势扫描股票池。
- 参数优化：对均线交叉策略做参数网格搜索，并用热力图查看稳定区域。
- 风控层：波动率目标仓位、固定风险预算仓位、Kelly 上限、最大回撤熔断工具。
- 报告：单票分析、单票回测、组合回测均可输出 CSV/JSON/HTML。
- CLI：`doctor`、`analyze`、`backtest`、`screen`、`portfolio`、`compare`、`alerts`、`optimize`。
- Web UI：提供 Streamlit 页面，适合快速交互式分析。
- CI：GitHub Actions 自动运行测试和 `quant doctor`。

## 详细文档

- [项目组织说明](docs/PROJECT_STRUCTURE.md)：解释目录结构、模块职责、数据流、命令入口和扩展方式。
- [金融指标说明](docs/FINANCIAL_INDICATORS.md)：解释技术指标、因子、绩效指标、风险指标和策略信号。
- [前后端架构说明](docs/FRONTEND_BACKEND_ARCHITECTURE.md)：解释当前 Streamlit 工作台架构，以及未来 FastAPI + React 的演进边界。

## 常用命令

单票分析：

```bash
python -m quant_system.cli analyze \
  --symbol 000001.SZ \
  --market cn \
  --data-file data/sample_prices.csv \
  --output reports/000001_analysis.json \
  --html-report reports/000001_analysis.html
```

回测：

```bash
python -m quant_system.cli backtest \
  --symbol AAPL \
  --market us \
  --data-file data/sample_prices.csv \
  --strategy ma \
  --short-window 5 \
  --long-window 20 \
  --initial-cash 100000 \
  --output-dir reports/aapl_ma \
  --html-report reports/aapl_ma/report.html
```

多市场选股：

```bash
python -m quant_system.cli screen \
  --config configs/default.yaml \
  --data-file data/sample_prices.csv \
  --top 10
```

组合回测：

```bash
python -m quant_system.cli portfolio \
  --config configs/default.yaml \
  --data-file data/sample_prices.csv \
  --top-n 3 \
  --rebalance-frequency 5 \
  --weighting equal \
  --output-dir reports/portfolio \
  --html-report reports/portfolio/report.html
```

多标的对比：

```bash
python -m quant_system.cli compare \
  --config configs/default.yaml \
  --data-file data/sample_prices.csv \
  --output-dir reports/compare
```

预警扫描：

```bash
python -m quant_system.cli alerts \
  --config configs/default.yaml \
  --data-file data/sample_prices.csv \
  --include-all \
  --output reports/alerts.csv
```

均线参数优化：

```bash
python -m quant_system.cli optimize \
  --symbol AAPL \
  --market us \
  --data-file data/sample_prices.csv \
  --short-windows 3,5,10 \
  --long-windows 20,40,60 \
  --rank-metric sharpe \
  --output reports/aapl_optimize.csv
```

Streamlit 页面：

```bash
streamlit run apps/streamlit_app.py
```

页面支持日线、周线、月线 K 线，覆盖 A 股、港股、美股的单票分析、策略参数优化、多标的对比、预警扫描、多市场选股和组合回测。

## 本地 CSV 格式

CSV 至少包含这些字段：

```text
date,symbol,market,open,high,low,close,volume
```

字段名也兼容常见中文行情列名，例如 `日期`、`开盘`、`最高`、`最低`、`收盘`、`成交量`。

## 项目结构

```text
src/quant_system/
  data/        行情源适配和 OHLCV 标准化
  analysis/    指标、绩效、单票报告、选股打分、对比、预警
  strategies/  策略信号
  backtest/    单票回测、组合回测和参数优化
  risk/        仓位和风险控制工具
  cli.py       命令行入口
configs/       默认配置
data/          示例行情
examples/      最小 API 调用示例
environment.yml Conda 环境定义
apps/          Streamlit 应用
.github/       GitHub Actions CI
tests/         单元测试
reports/       CLI 输出目录
```

## 开发验证

```bash
pytest
python -m quant_system.cli doctor
python -m quant_system.cli backtest --symbol AAPL --market us --data-file data/sample_prices.csv
```

本项目是研究与工程框架，不构成投资建议。接入券商交易、实盘下单、权限控制、风控审批和审计日志应作为单独生产化模块处理。
