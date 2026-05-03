# 多市场股票量化交易系统

这是一个面向实盘研究流程的 Python 量化系统骨架，覆盖 A 股、港股、美股的行情接入、技术指标、因子打分、策略信号、回测、风控工具和命令行入口。核心功能不依赖网络，默认可用 `data/sample_prices.csv` 直接运行；安装可选依赖后可接入在线行情。

## 快速开始

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
pip install -e ".[data,dev]"
python -m quant_system.cli analyze --symbol 000001.SZ --market cn --provider auto
python -m quant_system.cli analyze --symbol 0700.HK --market hk --provider auto
python -m quant_system.cli analyze --symbol AAPL --market us --provider auto
```

## 支持市场与代码格式

| 市场 | `--market` | 示例代码 | 默认在线源 |
|---|---:|---|---|
| A 股 | `cn` | `000001.SZ`, `600519.SH`, `430047.BJ` | `akshare` |
| 港股 | `hk` | `0700.HK`, `9988.HK` | `yfinance`，备选 `akshare` |
| 美股 | `us` | `AAPL`, `MSFT`, `SPY` | `yfinance` |

## 主要能力

- 数据层：统一 OHLCV 字段，支持本地 CSV、AkShare、Yahoo Finance，在线源失败时会给出清晰错误。
- 分析层：收益率、均线、EMA、RSI、MACD、布林带、ATR、波动率、回撤、夏普等指标。
- 策略层：均线交叉、RSI 均值回归、Donchian 突破，策略输出统一为目标仓位。
- 回测层：下一交易日执行信号，包含佣金、滑点、换手成本、权益曲线、交易明细和绩效指标。
- 风控层：波动率目标仓位、固定风险预算仓位、Kelly 上限、最大回撤熔断工具。
- CLI：`analyze`、`backtest`、`screen`、`doctor` 四个常用入口。

## 常用命令

单票分析：

```bash
python -m quant_system.cli analyze \
  --symbol 000001.SZ \
  --market cn \
  --data-file data/sample_prices.csv \
  --output reports/000001_analysis.json
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
  --output-dir reports/aapl_ma
```

多市场选股：

```bash
python -m quant_system.cli screen \
  --config configs/default.yaml \
  --data-file data/sample_prices.csv \
  --top 10
```

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
  analysis/    指标、绩效、单票报告、选股打分
  strategies/  策略信号
  backtest/    向量化回测引擎
  risk/        仓位和风险控制工具
  cli.py       命令行入口
configs/       默认配置
data/          示例行情
examples/      最小 API 调用示例
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
