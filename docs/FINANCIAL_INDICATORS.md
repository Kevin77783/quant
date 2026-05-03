# 金融指标说明

本文档解释项目中出现的技术指标、因子、绩效指标、风险指标和策略信号。它不是投资建议，而是帮助理解系统输出。

## 基础行情字段

### Date

交易日期。

在项目中字段名为：

```text
date
```

所有行情进入系统后都会转成 `datetime`，并按日期排序。

### Symbol

股票代码。

示例：

```text
000001.SZ
0700.HK
AAPL
```

### Market

市场。

项目支持：

```text
cn  A 股
hk  港股
us  美股
```

### OHLC

OHLC 是四个价格字段：

- `open`：开盘价
- `high`：最高价
- `low`：最低价
- `close`：收盘价

项目会校验：

- 价格必须大于 0
- `high` 不能小于 `low`
- `open` 和 `close` 不能超出 `high/low` 区间

### Volume

成交量。

项目要求成交量不能为负。成交量为 0 不一定非法，例如停牌、无成交或某些数据源缺失，但分析时应谨慎。

## 收益率指标

### Simple Return

字段：

```text
return
```

公式：

```text
return_t = close_t / close_{t-1} - 1
```

含义：

表示当日相对前一交易日的涨跌幅。

例子：

如果昨天收盘价是 100，今天收盘价是 103：

```text
return = 103 / 100 - 1 = 3%
```

### Log Return

字段：

```text
log_return
```

公式：

```text
log_return_t = ln(close_t / close_{t-1})
```

含义：

对数收益率在数学上更容易累加，常用于统计建模、波动率估计和风险模型。

普通用户看 `return` 更直观，研究和建模时 `log_return` 更常用。

## 趋势指标

### SMA

字段示例：

```text
sma_5
sma_20
sma_60
```

SMA 是简单移动平均线。

公式：

```text
SMA_N = 最近 N 个收盘价的算术平均值
```

含义：

它用来平滑价格波动，观察中短期趋势。

常见理解：

- 收盘价高于均线：价格处于相对强势
- 收盘价低于均线：价格处于相对弱势
- 短均线上穿长均线：趋势可能转强
- 短均线下穿长均线：趋势可能转弱

项目中的均线交叉策略使用短期 SMA 和长期 SMA 判断持仓。

### EMA

字段示例：

```text
ema_20
ema_60
```

EMA 是指数移动平均线。

含义：

相比 SMA，EMA 对近期价格变化更敏感。

适用场景：

- 判断趋势变化
- 配合 MACD
- 对短期价格变化更敏感的策略

### Momentum

字段示例：

```text
momentum_20
momentum_60
```

公式：

```text
momentum_N = close_t / close_{t-N} - 1
```

含义：

表示过去 N 个交易日的累计涨跌幅。

例如 `momentum_20_pct = 15.21` 表示近 20 个交易日上涨约 15.21%。

解读：

- 正值越大：近期上涨动能越强
- 负值越小：近期下跌动能越强
- 很高的动量可能意味着趋势强，也可能意味着短期过热

## 波动率指标

### Volatility

字段示例：

```text
volatility_20
volatility_60
```

公式简化：

```text
volatility_N = std(return, N) * sqrt(252)
```

这里乘以 `sqrt(252)` 是为了年化，假设一年约 252 个交易日。

含义：

波动率衡量价格变化的不稳定程度。

解读：

- 波动率高：价格大起大落，风险更高
- 波动率低：价格更平稳，但也可能缺少机会

注意：

波动率不是方向指标。高波动不代表会涨，也不代表会跌，只代表不稳定。

### ATR

字段：

```text
atr
atr_pct
```

ATR 是 Average True Range，平均真实波幅。

True Range 取以下三者最大值：

```text
high - low
abs(high - previous_close)
abs(low - previous_close)
```

ATR 是 True Range 的移动平均。

`atr_pct` 是：

```text
atr_pct = atr / close
```

含义：

ATR 衡量价格每日波动幅度。它比普通最高价减最低价更全面，因为考虑了跳空。

用途：

- 设置止损距离
- 估计仓位风险
- 判断当前价格波动是否异常

## 动量震荡指标

### RSI

字段：

```text
rsi
```

RSI 是 Relative Strength Index，相对强弱指标。

范围：

```text
0 到 100
```

常见解读：

- RSI < 30：可能超卖
- RSI 约 50：中性
- RSI > 70：偏强，也可能超买
- RSI > 80：非常强，但短期过热风险较高

项目中的 `RSIMeanReversionStrategy` 使用 RSI：

- RSI 低于 oversold：买入
- RSI 高于 overbought：清仓

注意：

强趋势行情中，RSI 可以长时间处在高位或低位。不能只因为 RSI 高就判断一定会跌。

### RSI Balance Score

字段：

```text
rsi_balance_score
```

这是项目自定义因子，不是经典金融指标。

目的：

不是简单奖励 RSI 越高越好，而是区分“健康强势”和“短期过热”。

项目逻辑大致为：

- RSI 45 到 60：较健康，分数高
- RSI 60 到 70：偏强，略加分
- RSI 过高或过低：扣分

例子：

如果 RSI 是 83.88，说明趋势很强，但项目会认为短期过热，因此 `rsi_balance_score` 可能是负数。

## MACD

字段：

```text
macd
macd_signal
macd_hist
```

MACD 通常由三部分组成：

- `macd`：快 EMA 减慢 EMA
- `macd_signal`：MACD 的信号线
- `macd_hist`：MACD 与信号线的差

常见参数：

```text
fast = 12
slow = 26
signal = 9
```

解读：

- `macd_hist > 0`：短期动能强于中期动能
- `macd_hist < 0`：短期动能偏弱
- 柱状图扩大：动能增强
- 柱状图收缩：动能减弱

注意：

MACD 是趋势跟随指标，震荡行情中容易出现频繁假信号。

## 布林带

字段：

```text
bb_mid
bb_upper
bb_lower
bb_width
```

公式：

```text
bb_mid = N 日均线
bb_upper = bb_mid + 2 * 标准差
bb_lower = bb_mid - 2 * 标准差
bb_width = (bb_upper - bb_lower) / bb_mid
```

含义：

布林带描述价格相对自身波动范围的位置。

常见解读：

- 价格接近上轨：走势强，或短期偏热
- 价格接近下轨：走势弱，或短期偏冷
- 带宽变大：波动扩大
- 带宽变小：波动收缩

## 回撤指标

### Drawdown

字段：

```text
drawdown
```

公式：

```text
drawdown_t = current_value / historical_peak - 1
```

含义：

表示当前价格或净值距离历史高点跌了多少。

例子：

如果历史最高净值是 100，现在是 90：

```text
drawdown = 90 / 100 - 1 = -10%
```

解读：

- `drawdown = 0`：当前处在历史新高
- `drawdown = -0.1`：从高点回撤 10%

### Max Drawdown

字段：

```text
max_drawdown
```

含义：

一段时间内最大的高点到低点跌幅。

它是衡量策略风险的重要指标，因为投资者通常很关心“最难受的时候会亏多少”。

## 流动性指标

### Turnover Proxy

字段：

```text
turnover_proxy
```

公式：

```text
turnover_proxy = close * volume
```

含义：

这是一个简化的成交额近似值。它不是严格成交额，因为真实成交额应使用逐笔或成交金额字段，但在只有 OHLCV 时可以作为流动性代理。

解读：

- 数值越大，说明该股票成交更活跃
- 流动性高的股票通常更容易交易
- 流动性低的股票可能面临较大冲击成本

### Liquidity Score

字段：

```text
liquidity_score
```

项目自定义因子。

它基于 `turnover_proxy` 做对数缩放，范围大致在：

```text
-1 到 1
```

含义：

流动性越好，得分越高。

注意：

不同市场成交量单位可能不完全一致，因此跨市场比较时只能作为近似参考。

## 综合因子评分

### Trend Score

字段：

```text
trend_score
```

项目自定义趋势因子。

它主要观察：

- 收盘价是否高于 `sma_20`
- 收盘价是否高于 `sma_60`
- 收盘价是否高于 `ema_20`

解读：

- 越接近 1：趋势越强
- 越接近 -1：趋势越弱
- 接近 0：趋势不明显

### Composite Score

在用户输出中显示为：

```text
score
```

范围：

```text
0 到 100
```

它是项目自定义多因子综合评分，综合考虑：

- 趋势
- 20 日动量
- 60 日动量
- 波动率
- 流动性
- RSI 是否健康
- MACD 动能
- 当前回撤

解读：

- 80 以上：样本中综合表现较强
- 60 到 80：偏强或中性偏强
- 40 到 60：中性
- 40 以下：偏弱

注意：

该分数是研究排序工具，不是买入建议。它没有考虑估值、基本面、财报、宏观、消息面和交易限制。

## 绩效指标

### Total Return

字段：

```text
total_return
```

公式：

```text
total_return = final_equity / initial_equity - 1
```

含义：

整个区间累计收益率。

例子：

`0.221244` 表示累计收益约 22.12%。

### Annual Return

字段：

```text
annual_return
```

含义：

把区间收益换算成年化收益。

注意：

如果样本时间很短，年化收益可能非常夸张。例如只用一个多月的数据，年化结果不能当作长期预期。

### Annual Volatility

字段：

```text
annual_volatility
```

含义：

收益率的年化标准差，衡量净值波动程度。

解读：

- 高年化波动：收益曲线更不稳定
- 低年化波动：收益曲线更平滑

### Sharpe Ratio

字段：

```text
sharpe
```

公式简化：

```text
sharpe = 年化超额收益 / 年化波动率
```

含义：

夏普比率衡量每承担一单位波动风险，获得多少收益。

解读：

- 越高越好
- 小于 0：收益不如无风险利率或表现较差
- 1 左右：可接受
- 2 以上：较好
- 很高的值要检查样本是否过短、是否过拟合

### Calmar Ratio

字段：

```text
calmar
```

公式：

```text
calmar = annual_return / abs(max_drawdown)
```

含义：

衡量年化收益相对于最大回撤的表现。

相比夏普，Calmar 更关注最大亏损压力。

### Win Rate

字段：

```text
win_rate
```

含义：

上涨日或盈利日占比。

注意：

胜率高不一定赚钱。如果每次亏损很大、每次盈利很小，策略仍可能亏损。

### Best Day / Worst Day

字段：

```text
best_day
worst_day
```

含义：

区间内最好和最差的单日收益。

用途：

- 判断极端单日波动
- 观察策略是否对尾部风险敏感

## 回测指标

### Equity

字段：

```text
equity
```

含义：

策略净值或账户权益。

单票回测和组合回测都会输出权益曲线。

### Benchmark Equity

字段：

```text
benchmark_equity
```

含义：

基准净值。

在单票回测中，基准通常是买入并持有该股票。

在组合回测中，基准是可加载股票的等权组合。

### Excess Total Return

字段：

```text
excess_total_return
```

公式：

```text
策略总收益 - 基准总收益
```

含义：

衡量策略是否跑赢基准。

### Position

字段：

```text
position
```

含义：

实际持仓权重。

项目的单票回测使用下一交易日执行信号：

```text
今天生成 target_weight，明天变成 position
```

这样可以减少未来函数问题。

### Target Weight

字段：

```text
target_weight
```

含义：

策略希望持有的目标仓位。

例如：

- `1.0`：满仓
- `0.5`：半仓
- `0.0`：空仓

当前策略是多头策略，仓位会限制在 0 到 1 之间。

### Turnover

字段：

```text
turnover
avg_turnover
```

含义：

换手率，表示仓位变化幅度。

例子：

如果从 0% 仓位变成 100% 仓位：

```text
turnover = 1.0
```

换手率越高，交易成本越高，也越容易受到滑点影响。

### Commission Bps

配置字段：

```text
commission_bps
```

含义：

手续费，单位是 bps。

1 bps 等于：

```text
0.01%
```

例如 `commission_bps = 2.0`，表示手续费约 0.02%。

### Slippage Bps

配置字段：

```text
slippage_bps
```

含义：

滑点，单位也是 bps。

滑点表示真实成交价格相对理想价格的损耗。

项目中交易成本简化为：

```text
cost = turnover * (commission_bps + slippage_bps) / 10000
```

## 策略指标和信号

### Moving Average Cross

策略名：

```text
ma
```

逻辑：

```text
短期均线 > 长期均线：持仓
短期均线 <= 长期均线：空仓
```

常用参数：

```bash
--short-window 5
--long-window 20
```

优点：

- 简单
- 顺趋势
- 容易解释

缺点：

- 震荡行情容易频繁进出
- 信号滞后

### RSI Mean Reversion

策略名：

```text
rsi
```

逻辑：

```text
RSI <= oversold：买入
RSI >= overbought：卖出
```

常用参数：

```bash
--oversold 30
--overbought 70
```

适用场景：

更适合震荡或均值回归明显的股票。

风险：

趋势下跌时，RSI 低可能不是机会，而是弱势延续。

### Donchian Breakout

策略名：

```text
breakout
```

逻辑：

```text
收盘价突破过去 N 日最高价：买入
收盘价跌破过去 N 日最低价：卖出
```

适用场景：

趋势突破策略，适合捕捉中长期行情。

缺点：

假突破会造成亏损。

## 组合回测指标

### Top N

参数：

```text
top_n
```

含义：

每次调仓时，选择综合分数最高的 N 只股票。

### Rebalance Frequency

参数：

```text
rebalance_frequency
```

含义：

每隔多少个交易日调仓一次。

例如：

```text
rebalance_frequency = 5
```

表示大约每 5 个交易日重新选股和调仓。

### Weighting

参数：

```text
weighting
```

当前支持：

```text
equal
inverse_vol
```

`equal`：

每只入选股票权重相同。

`inverse_vol`：

波动率越低，权重越高。目的是降低组合整体波动。

### Rebalance Count

字段：

```text
rebalance_count
```

含义：

回测期间实际调仓次数。

### Loaded Symbols / Failed Symbols

字段：

```text
loaded_symbols
failed_symbols
```

含义：

组合回测中成功加载和失败跳过的股票数量。

如果用样例 CSV，而配置里有样例 CSV 不包含的股票，就会看到 `failed_symbols > 0`。

## 风控指标和工具

### Fixed Fraction Position

函数：

```python
fixed_fraction_position()
```

含义：

根据账户资金、单笔风险预算和止损距离计算买入股数。

例子：

如果账户 100000，单笔最多亏 2%，止损距离 8%，价格 50：

```text
可承受亏损 = 100000 * 2% = 2000
每股风险 = 50 * 8% = 4
股数 = 2000 / 4 = 500
```

### Volatility Target Weight

函数：

```python
volatility_target_weight()
```

含义：

根据历史波动率调整仓位，让组合接近目标波动率。

逻辑：

- 实际波动率高：降低仓位
- 实际波动率低：提高仓位

### Kelly Fraction

函数：

```python
kelly_fraction()
```

Kelly 公式用于估计理论最优下注比例。

项目中使用了上限 `cap`，避免仓位过大。

注意：

Kelly 对胜率和盈亏比估计非常敏感，实务中通常只使用半 Kelly 或更保守的比例。

### Drawdown Kill Switch

函数：

```python
apply_drawdown_kill_switch()
```

含义：

当权益曲线回撤超过阈值时，把后续目标仓位降为 0。

用途：

模拟最大回撤风控线。

## 如何理解一次 `analyze` 输出

示例：

```text
AAPL (us) 2025-02-12
  close        221.9000
  trend        bullish
  score        83.35/100
Signals
  trend_score        1.0
  momentum_20_pct    15.21
  volatility_20      0.1645
  rsi                83.88
  macd_hist          1.2292
  drawdown           0.0
Performance
  total_return       0.221244
  sharpe             11.084386
```

解读：

- `close`：最后一个交易日收盘价
- `trend bullish`：趋势偏多
- `score 83.35`：多因子综合分较高
- `momentum_20_pct 15.21`：近 20 日涨幅较强
- `rsi 83.88`：趋势强，但可能短期过热
- `drawdown 0.0`：处在样本期高点
- `total_return 0.221244`：样本期累计收益约 22.12%
- `sharpe 11.08`：很高，但如果样本很短，需要谨慎

## 重要注意事项

1. 指标不是预测机器。

技术指标只是描述历史价格和成交量的方式，不保证未来走势。

2. 样本期越短，绩效指标越不稳定。

短期数据的年化收益和夏普可能被严重放大。

3. 回测不是实盘。

真实交易会受到盘口深度、涨跌停、停牌、税费、融资融券限制、交易规则和下单延迟影响。

4. 多因子分数用于排序，不等于买入建议。

当前系统没有纳入估值、财务质量、盈利预测、宏观变量、新闻事件和行业约束。

5. 跨市场比较要谨慎。

A 股、港股、美股的交易制度、成交量单位、交易时间和数据质量不同，跨市场分数更适合做初筛，而不是最终投资决策。

