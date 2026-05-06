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

建议阅读顺序：

1. 先看 `README.md`，了解如何安装和运行。
2. 再看 `src/quant_system/cli.py`，了解用户命令如何进入系统。
3. 然后看 `src/quant_system/workflows.py` 和 `src/quant_system/data/providers.py`，理解数据源如何创建。
4. 接着看 `analysis/`、`strategies/`、`backtest/`，理解分析、策略和回测的核心逻辑。
5. 最后看 `apps/streamlit_app.py`，理解图形界面如何复用后端模块。

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

### `docs/FRONTEND_BACKEND_ARCHITECTURE.md`

解释当前 Streamlit 工作台架构、前后端职责边界，以及未来升级到 FastAPI + React 的条件。

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
- 日线、周线、月线 K 线
- 单票回测
- 均线策略参数优化
- 多标的收益、风险和相关性对比
- 多标的预警扫描
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

常见输出：

- `analyze`：JSON 分析结果、HTML 单票报告
- `backtest`：`equity_curve.csv`、`trades.csv`、`signals.csv`、`metrics.csv`
- `portfolio`：组合净值、组合权重、调仓日志、组合指标
- `compare`：`summary.csv`、`normalized.csv`、`correlation.csv`
- `alerts`：预警扫描 CSV
- `optimize`：均线参数网格搜索 CSV

## 核心包：`src/quant_system/`

核心包当前按职责拆成这些文件：

```text
src/quant_system/
  __init__.py
  models.py                 市场、证券、OHLCV 标准化和校验
  config.py                 YAML 配置和股票池解析
  workflows.py              CLI/UI 共享的数据源构建入口
  timeframe.py              日线转周线/月线
  cli.py                    命令行入口
  reporting.py              HTML 报告输出
  visualization.py          Plotly 图表工厂
  data/
    providers.py            CSV、AkShare、Yahoo、缓存和自动数据源
  analysis/
    indicators.py           技术指标
    factors.py              多因子和综合评分
    performance.py          绩效和回撤指标
    report.py               单票分析和多市场选股
    compare.py              多标的对比和相关性
    alerts.py               多标的预警扫描
  strategies/
    core.py                 策略接口和内置策略
  backtest/
    engine.py               单票回测引擎
    portfolio.py            组合回测引擎
    optimize.py             均线策略参数优化
  risk/
    position.py             仓位和风险工具
```

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
quant compare
quant alerts
quant optimize
```

主要职责：

- 解析命令行参数
- 创建数据源对象
- 调用分析、回测、选股、组合回测、对比、预警和优化模块
- 输出终端结果
- 写入 JSON、CSV、HTML 报告

如果要新增一个命令，通常从这里的 `build_parser()` 和对应的 `cmd_xxx()` 开始。

各命令的定位：

- `doctor`：检查运行环境和可选依赖是否安装。
- `analyze`：分析单只股票，输出最新因子、趋势、综合评分和买入持有绩效。
- `backtest`：对单只股票运行一个策略，输出净值、交易明细、信号和绩效。
- `screen`：对股票池逐只打分，并按综合分排序。
- `portfolio`：按因子排名定期选股，做多标的组合回测。
- `compare`：比较股票池内标的的标准化走势、风险收益和收益相关性。
- `alerts`：扫描股票池中的高分、超买、超卖、回撤、弱动量、空头趋势等预警。
- `optimize`：网格搜索均线交叉策略参数，按夏普、收益或其他指标排序。

### `src/quant_system/workflows.py`

共享工作流入口。当前主要负责创建数据源对象，让 CLI、Streamlit 页面、示例脚本和未来 API 可以复用同一套 provider 构建逻辑。

### `src/quant_system/timeframe.py`

K 线频率处理工具。当前提供 `resample_ohlcv()`，用于把日线数据重采样成周线或月线。

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

#### `analysis/compare.py`

多标的对比分析。

主要输出：

- `normalized`：把每只股票起点统一成 100 的标准化净值走势
- `summary`：每只股票的收益、波动、夏普、最大回撤、胜率等摘要
- `correlation`：股票之间的日收益相关性矩阵
- `failures`：无法加载或计算的标的列表

这个模块服务于 CLI 的 `compare` 命令和 Streamlit 的 `Compare` 页面。

#### `analysis/alerts.py`

预警扫描模块。

主要对象：

- `AlertRule`：预警规则配置，包括最低分数、RSI 上下限、最大回撤阈值、20 日动量阈值等。
- `scan_alerts()`：遍历股票池，生成触发预警的标的表。

当前预警属于研究提示，不是交易信号。它帮助快速发现需要进一步人工检查的股票。

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

#### `backtest/optimize.py`

策略参数优化模块。

当前提供：

- `optimize_ma_strategy()`：对均线交叉策略做短均线、长均线参数网格搜索。

输出表包含：

- `short_window`
- `long_window`
- `total_return`
- `annual_return`
- `annual_volatility`
- `sharpe`
- `max_drawdown`
- `win_rate`
- `excess_total_return`
- `trades`

它用于快速比较不同均线组合的历史表现，但不能单独证明未来有效。参数优化结果需要配合样本外测试、滚动回测和交易成本敏感性分析。

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

### `src/quant_system/visualization.py`

Plotly 交互式图表构建模块。

当前提供：

- K 线、均线、成交量、RSI、MACD 组合图
- 因子条形图
- 综合评分仪表图
- 净值和回撤图
- 选股散点图
- 组合权重图
- 多标的标准化走势对比图
- 收益相关性热力图
- 风险收益散点图
- 均线参数优化热力图
- 预警触发数量柱状图

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
- 多标的对比
- 预警扫描
- 均线参数优化
- HTML 报告生成
- Plotly 图表构建

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

### 多标的对比

```text
CLI compare / Streamlit Compare
  -> load_yaml()
  -> parse_universe()
  -> provider.get_history() for each security
  -> close price alignment
  -> normalized base-100 performance
  -> calculate_performance()
  -> return correlation matrix
  -> summary.csv / normalized.csv / correlation.csv / Plotly charts
```

### 预警扫描

```text
CLI alerts / Streamlit Alerts
  -> load_yaml()
  -> parse_universe()
  -> AlertRule thresholds
  -> provider.get_history() for each security
  -> analyze_prices()
  -> score / RSI / drawdown / momentum / trend checks
  -> terminal / CSV / alerts chart
```

### 均线参数优化

```text
CLI optimize / Single Stock Optimize tab
  -> DataProvider.get_history()
  -> short_window x long_window grid
  -> MovingAverageCrossStrategy()
  -> BacktestEngine.run() for each valid pair
  -> rank by sharpe / return / drawdown / chosen metric
  -> terminal / CSV / heatmap
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

### 新增一个 Streamlit 页面或标签

1. 优先把业务逻辑写在 `src/quant_system/`，不要直接塞进 `apps/streamlit_app.py`
2. 如果需要图表，在 `visualization.py` 中新增 `make_xxx_figure()` 函数
3. 在 `apps/streamlit_app.py` 中只负责控件、参数收集、调用后端函数和展示结果
4. 对纯后端函数补单元测试
5. 对页面至少做一次本地启动验证

### 新增一个金融指标说明

1. 在代码里确认字段名、公式和取值范围
2. 在 `docs/FINANCIAL_INDICATORS.md` 中说明含义、公式、常见解读和误区
3. 如果指标会参与 `composite_score`，需要说明它如何影响评分
4. 如果指标出现在 CLI 或 Streamlit 输出中，需要说明普通用户应该怎么看

## 设计原则

- 数据源可替换：核心分析不依赖具体行情供应商
- 数据标准统一：进入分析层前统一成 OHLCV
- 策略输出统一：策略只输出目标仓位
- 回测与策略解耦：回测引擎不关心策略内部计算
- 离线可运行：样例数据保证无网络也能测试
- 在线可缓存：真实行情拉取后可复用
- 报告可落盘：CLI 输出不只停留在终端
- 测试覆盖核心路径：新增功能应补测试
