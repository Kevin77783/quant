# 项目组织说明

本文档解释本项目的目录结构、主要模块职责、数据流、命令入口和扩展方式。目标是让后续开发者能快速知道“代码在哪里、每一层负责什么、应该从哪里改”。

## 总览

项目采用标准 Python 包结构：

```text
quant/
  README.md
  pyproject.toml
  environment.yml
  pytest.ini
  configs/
  data/
  docs/
  examples/
  apps/
  reports/
  src/quant_system/
  tests/
  .github/workflows/
```

核心代码都放在 `src/quant_system/`。这种 `src` 布局比把包直接放在项目根目录更稳，能避免测试时意外导入当前目录下的临时文件。

## 根目录文件

### `README.md`

项目首页文档，负责告诉用户如何安装、如何运行常用命令、支持哪些市场和数据源。它适合作为快速开始入口，不承载过多实现细节。

### `pyproject.toml`

Python 项目元数据和依赖声明。

关键内容：

```toml
[project]
name = "multi-market-quant-system"

[project.optional-dependencies]
data = ["akshare", "yfinance"]
dev = ["pytest"]
app = ["streamlit"]

[project.scripts]
quant = "quant_system.cli:main"
```

其中 `quant = "quant_system.cli:main"` 表示安装项目后，可以直接在命令行运行：

```bash
quant doctor
quant analyze ...
```

它实际调用的是 `src/quant_system/cli.py` 里的 `main()` 函数。

### `environment.yml`

Conda 环境定义文件。当前环境名是：

```yaml
name: quant
```

创建或更新环境：

```bash
conda env create -f environment.yml
conda env update -f environment.yml --prune
conda activate quant
```

该环境会安装核心分析依赖、开发测试依赖、在线数据依赖和 Streamlit UI 依赖。

### `pytest.ini`

测试配置文件。主要指定：

```ini
pythonpath = src
testpaths = tests
```

这样运行 `pytest` 时，测试能正确导入 `src/quant_system`。

### `.gitignore`

排除本地运行产物，例如：

- `__pycache__/`
- `.pytest_cache/`
- `.venv/`
- `reports/*`
- `data/raw/*`
- `data/processed/*`

注意：`reports/.gitkeep`、`data/raw/.gitkeep`、`data/processed/.gitkeep` 会被保留，用来让空目录进入 Git。

## 配置目录：`configs/`

### `configs/default.yaml`

默认运行配置，包括：

- 数据源配置
- 回测初始资金、手续费、滑点
- 策略参数
- 多市场股票池
- 组合回测参数

示意：

```yaml
data:
  provider: auto
  local_file: data/sample_prices.csv
  cache_dir: data
  use_cache: true

backtest:
  initial_cash: 100000
  commission_bps: 2.0
  slippage_bps: 1.0

universe:
  cn:
    - symbol: 000001.SZ
      name: 平安银行
  hk:
    - symbol: 0700.HK
      name: 腾讯控股
  us:
    - symbol: AAPL
      name: Apple
```

### `configs/universe.example.yaml`

更完整的股票池示例。适合用户复制后改成自己的研究股票池。

## 数据目录：`data/`

### `data/sample_prices.csv`

本地样例行情数据。用于无网络环境下跑通分析、选股和回测流程。

字段要求：

```text
date,symbol,market,open,high,low,close,volume
```

### `data/raw/`

在线数据原始缓存目录。`--provider auto`、`--provider yahoo`、`--provider akshare` 拉到数据后，会写入这里。

### `data/processed/`

标准化后的数据缓存目录。系统再次运行时，如果在线源不可用，可以从这里读取缓存。

## 文档目录：`docs/`

### `docs/PROJECT_STRUCTURE.md`

也就是本文档，说明项目结构和扩展方式。

### `docs/FINANCIAL_INDICATORS.md`

解释项目中的金融指标、因子、回测指标和风险指标。

## 示例目录：`examples/`

### `examples/basic_workflow.py`

最小 API 使用示例。它演示如何在 Python 代码里：

1. 读取数据
2. 做单票分析
3. 跑单票策略回测
4. 做多市场选股
5. 跑组合回测

运行：

```bash
python examples/basic_workflow.py
```

## 应用目录：`apps/`

### `apps/streamlit_app.py`

Streamlit 图形界面。适合不想写命令的交互式使用场景。

运行：

```bash
streamlit run apps/streamlit_app.py
```

当前页面支持：

- 单票分析
- 单票回测
- 多市场选股
- 组合回测

## 报告目录：`reports/`

命令行输出的 CSV、JSON、HTML 报告默认写到这里。

示例：

```bash
quant backtest \
  --symbol AAPL \
  --market us \
  --provider yahoo \
  --output-dir reports/aapl_ma \
  --html-report reports/aapl_ma/report.html
```

`reports/` 下的运行产物不会提交到 Git。

## 核心包：`src/quant_system/`

### `src/quant_system/__init__.py`

包入口，定义版本号并导出常用对象。

### `src/quant_system/models.py`

基础模型和数据标准化逻辑。

主要内容：

- `Market`：支持市场枚举，包含 `cn`、`hk`、`us`
- `Security`：证券对象，包含 `symbol`、`market`、`name`
- `normalize_symbol()`：股票代码标准化
- `normalize_ohlcv()`：行情字段标准化
- `validate_ohlcv()`：行情数据校验

这里是数据进入系统后的第一道安全关。所有数据源最终都应该转换成统一的 OHLCV 格式。

### `src/quant_system/config.py`

配置读取和股票池解析。

主要内容：

- `load_yaml()`：读取 YAML 配置
- `parse_universe()`：解析配置文件中的股票池
- `parse_universe_argument()`：解析命令行传入的股票池

支持两种股票池形式：

```yaml
universe:
  - symbol: AAPL
    market: us
```

也支持按市场分组：

```yaml
universe:
  us:
    - symbol: AAPL
      name: Apple
```

### `src/quant_system/cli.py`

命令行入口。

已支持命令：

```bash
quant doctor
quant analyze
quant backtest
quant screen
quant portfolio
```

主要职责：

- 解析命令行参数
- 创建数据源对象
- 调用分析、回测、选股、组合回测模块
- 输出终端结果
- 写入 JSON、CSV、HTML 报告

如果要新增一个命令，通常从这里的 `build_parser()` 和对应的 `cmd_xxx()` 开始。

### `src/quant_system/data/`

数据层。

#### `data/providers.py`

主要类：

- `DataProvider`：数据源抽象基类
- `CSVDataProvider`：本地 CSV 数据源
- `AkShareProvider`：A 股和港股在线数据源
- `YahooFinanceProvider`：美股和港股在线数据源
- `DataCache`：缓存读写
- `CachedDataProvider`：给在线数据源包一层缓存
- `AutoDataProvider`：自动选择数据源

`AutoDataProvider` 当前逻辑：

1. 优先尝试在线数据源
2. 在线成功后写入 `data/raw/` 和 `data/processed/`
3. 在线失败时读取缓存
4. 缓存也失败时回退到本地 CSV

这个逻辑可以避免用户写了 `--provider auto` 却意外读到样例数据。

### `src/quant_system/analysis/`

分析层。

#### `analysis/indicators.py`

计算技术指标：

- 简单收益率
- 对数收益率
- SMA
- EMA
- Momentum
- Volatility
- RSI
- MACD
- Bollinger Bands
- ATR
- Drawdown

#### `analysis/factors.py`

多因子评分逻辑。

主要输出：

- `trend_score`
- `momentum_20_pct`
- `momentum_60_pct`
- `volatility_20`
- `liquidity_score`
- `rsi_balance_score`
- `macd_hist`
- `atr_pct`
- `drawdown`
- `composite_score`

#### `analysis/performance.py`

绩效指标：

- 总收益率
- 年化收益率
- 年化波动率
- 夏普比率
- 最大回撤
- Calmar
- 胜率
- 最好/最差单日收益

#### `analysis/report.py`

面向用户的分析报告和选股排名。

主要函数：

- `analyze_prices()`：单只股票分析
- `screen_universe()`：多市场股票池打分排序

### `src/quant_system/strategies/`

策略层。

#### `strategies/core.py`

已有策略：

- `MovingAverageCrossStrategy`：均线交叉策略
- `RSIMeanReversionStrategy`：RSI 均值回归策略
- `DonchianBreakoutStrategy`：Donchian 通道突破策略
- `build_strategy()`：根据名称创建策略

所有策略统一输出 `target_weight`，即目标仓位。回测引擎不关心策略内部逻辑，只读取目标仓位。

### `src/quant_system/backtest/`

回测层。

#### `backtest/engine.py`

单股票回测引擎。

特点：

- 多头策略
- 下一交易日执行信号
- 支持手续费和滑点
- 输出权益曲线、交易记录、策略信号、绩效指标

#### `backtest/portfolio.py`

组合回测引擎。

特点：

- 多股票池
- 按多因子分数选 Top N
- 定期调仓
- 支持等权和逆波动率加权
- 输出组合净值、权重、调仓日志和绩效指标

### `src/quant_system/risk/`

风险管理工具。

#### `risk/position.py`

主要函数：

- `fixed_fraction_position()`：固定风险预算仓位
- `volatility_target_weight()`：波动率目标仓位
- `kelly_fraction()`：Kelly 仓位上限
- `apply_drawdown_kill_switch()`：最大回撤熔断

这些函数目前是工具函数，还没有强制嵌入所有策略。后续实盘化时可以放到统一的组合风控层。

### `src/quant_system/reporting.py`

HTML 报告生成。

主要函数：

- `write_analysis_html()`：单票分析 HTML
- `write_backtest_html()`：单票或组合回测 HTML

当前实现使用纯 HTML/CSS/SVG，不依赖额外绘图库，部署和 CI 更简单。

## 测试目录：`tests/`

当前测试覆盖：

- 数据读取和代码标准化
- OHLCV 数据校验
- 缓存写入
- 指标计算
- 单票分析
- 单票回测
- 多市场选股
- 组合回测
- HTML 报告生成

运行：

```bash
pytest
```

或：

```bash
conda run -n quant pytest -p no:cacheprovider
```

## CI：`.github/workflows/ci.yml`

GitHub Actions 配置。

每次 push 或 pull request 会自动：

1. 安装 Python
2. 安装项目和测试依赖
3. 运行 `pytest`
4. 运行 `quant doctor`

## 典型数据流

### 单票分析

```text
CLI analyze
  -> build_provider()
  -> DataProvider.get_history()
  -> normalize_ohlcv()
  -> add_indicators()
  -> factor_snapshot()
  -> analyze_prices()
  -> terminal / JSON / HTML output
```

### 单票回测

```text
CLI backtest
  -> DataProvider.get_history()
  -> Strategy.generate_signals()
  -> BacktestEngine.run()
  -> calculate_performance()
  -> CSV / HTML output
```

### 多市场选股

```text
CLI screen
  -> load_yaml()
  -> parse_universe()
  -> provider.get_history() for each security
  -> add_indicators()
  -> factor_snapshot()
  -> score ranking
  -> terminal / CSV output
```

### 组合回测

```text
CLI portfolio
  -> load_yaml()
  -> parse_universe()
  -> provider.get_history() for each security
  -> factor_frame()
  -> periodic Top N selection
  -> portfolio weights
  -> portfolio equity curve
  -> CSV / HTML output
```

## 如何扩展

### 新增一个数据源

1. 在 `src/quant_system/data/providers.py` 新建类，继承 `DataProvider`
2. 实现 `get_history()`
3. 返回值必须经过 `normalize_ohlcv()`
4. 在 `build_provider()` 中加入命令行选项
5. 添加测试

### 新增一个技术指标

1. 在 `analysis/indicators.py` 中计算新列
2. 如需参与评分，在 `analysis/factors.py` 中加入因子逻辑
3. 在 `docs/FINANCIAL_INDICATORS.md` 中补说明
4. 添加测试

### 新增一个策略

1. 在 `strategies/core.py` 新建策略类，继承 `Strategy`
2. 实现 `generate_signals()`
3. 输出至少包含 `target_weight`
4. 在 `build_strategy()` 中注册名称
5. 添加回测测试

### 新增一个 CLI 命令

1. 在 `cli.py` 的 `build_parser()` 中添加 subparser
2. 编写 `cmd_xxx(args)`
3. 如果会产生文件，写到 `reports/` 或用户指定路径
4. 在 README 中补使用示例
5. 添加测试或至少手工验证命令

## 设计原则

- 数据源可替换：核心分析不依赖具体行情供应商
- 数据标准统一：进入分析层前统一成 OHLCV
- 策略输出统一：策略只输出目标仓位
- 回测与策略解耦：回测引擎不关心策略内部计算
- 离线可运行：样例数据保证无网络也能测试
- 在线可缓存：真实行情拉取后可复用
- 报告可落盘：CLI 输出不只停留在终端
- 测试覆盖核心路径：新增功能应补测试

