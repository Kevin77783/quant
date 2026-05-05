# 前后端架构说明

本文档说明本项目当前为什么采用 Streamlit 工作台，以及未来在多用户、生产部署、实盘接入时应该如何演进。

## 当前推荐架构

当前项目处在量化研究和个人/小团队使用阶段，推荐架构是：

```text
Streamlit UI
  -> quant_system.workflows
  -> quant_system.data / analysis / strategies / backtest / risk
  -> CSV / cache / online providers
```

也就是说，前端是 `apps/streamlit_app.py`，后端能力集中在 `src/quant_system/` 这个 Python 包里。

这种架构适合当前任务，因为：

- 量化研究主要依赖 Python 数据栈，Streamlit 可以直接调用 Pandas、Plotly 和回测函数。
- A 股、港股、美股的数据接入和分析逻辑还在快速变化，单体 Python 工作台迭代成本最低。
- 本地研究不需要用户登录、权限系统、异步任务队列和复杂部署。
- 图表、表格、参数控件、文件输出都能在一个进程内完成。

## 当前模块分工

```text
apps/streamlit_app.py
  负责页面布局、控件、交互状态、调用后端函数、展示图表。

src/quant_system/workflows.py
  负责构建数据源对象，是 UI、CLI 和未来 API 可以共享的服务层入口。

src/quant_system/data/
  负责 CSV、AkShare、Yahoo Finance、缓存和数据标准化。

src/quant_system/analysis/
  负责指标、因子、绩效和选股排名。

src/quant_system/backtest/
  负责单票回测和组合回测。

src/quant_system/visualization.py
  负责 Plotly 图表构建，包括 K 线、因子、净值、回撤、选股散点、组合权重。

src/quant_system/risk/
  负责仓位和风险工具。
```

这个分工的原则是：页面只做展示和交互，金融计算尽量放在 `quant_system` 包里。

## 为什么不是直接上 React + FastAPI

React + FastAPI 更适合生产化平台，但对当前阶段不是最优第一步。

它的优势：

- 前端交互可以做得更精细
- 多用户权限、登录、审计更容易拆分
- 后端可以独立部署和扩容
- 可以接 Celery、Redis、数据库和对象存储

它的成本：

- 需要维护前端工程、后端 API、接口契约和构建流程
- Pandas DataFrame、Plotly 图表、回测对象需要额外序列化
- 研究阶段频繁改指标和策略时，前后端同步成本高
- 本地个人使用会变重

因此当前更适合先把研究系统打磨好，等功能稳定后再拆服务。

## 什么时候应该升级到 FastAPI + React

出现以下需求时，可以考虑升级：

- 多人同时使用
- 需要账号、权限、团队空间
- 需要保存用户自定义股票池、策略参数和报告
- 需要长时间批量任务
- 需要任务队列和进度条
- 需要对接数据库
- 需要部署到服务器
- 需要实盘交易、审批、审计日志
- 需要移动端或复杂前端交互

## 未来生产化架构建议

如果升级，建议采用：

```text
React / Next.js Frontend
  -> FastAPI Backend
  -> quant_system Core Package
  -> Task Queue
  -> PostgreSQL
  -> Redis
  -> Object Storage
  -> Data Providers
```

推荐拆分：

```text
frontend/
  React or Next.js

backend/
  FastAPI routes
  auth
  task APIs

src/quant_system/
  保持当前核心量化包
```

关键原则：

- 不要把金融计算写进 React。
- 不要把 Streamlit 页面逻辑迁移成核心业务逻辑。
- `quant_system` 应继续作为可测试的纯 Python 核心包。
- API 层只做请求解析、任务调度、权限和结果返回。

## 当前 Streamlit 页面设计

当前页面是工作台，不是营销首页。

主要分为三块：

1. `Single Stock`

单只股票分析，支持：

- A 股、港股、美股市场选择
- CSV、auto、Yahoo、AkShare 数据源
- 日线、周线、月线 K 线
- K 线、成交量、RSI、MACD
- 多因子评分
- 单票策略回测
- 风险仓位计算
- 原始指标数据查看

2. `Universe Screen`

多市场选股，支持：

- 从配置文件读取股票池
- 按市场筛选
- 多因子排名
- 分数和波动率散点图
- 跳过失败股票并展示原因

3. `Portfolio Backtest`

组合回测，支持：

- Top N 选股
- 定期调仓
- 等权或逆波动率加权
- 净值和回撤图
- 组合权重图
- 调仓日志

## K 线频率设计

用户提到“不需要频次太高”，所以当前支持：

```text
Daily
Weekly
Monthly
```

本地 CSV 数据会通过 `resample_ohlcv()` 重采样。

在线数据可以使用：

```text
1d
1wk
1mo
```

这比分钟线更适合中长期量化分析，也能降低数据量、网络请求和界面渲染压力。

## 数据源策略

当前数据源选择：

```text
csv      强制本地 CSV
auto     优先在线，失败后缓存，再回退本地 CSV
yahoo    强制 Yahoo Finance
akshare  强制 AkShare
```

主要覆盖：

- A 股：优先 AkShare
- 港股：Yahoo Finance 或 AkShare
- 美股：Yahoo Finance

## 缓存策略

在线数据会写入：

```text
data/raw/
data/processed/
```

这样做的原因：

- 降低重复请求
- 在线源失败时还能继续分析
- 便于复现实验
- 保留原始数据和标准化数据

## 可视化技术选择

当前使用：

```text
Streamlit + Plotly
```

Plotly 用于：

- K 线图
- 成交量柱状图
- RSI
- MACD
- 净值和回撤
- 选股散点图
- 组合权重面积图

相比静态图片，Plotly 支持缩放、悬停查看和图例切换，适合量化分析。

## 开发建议

新增页面能力时，推荐顺序：

1. 先在 `src/quant_system/` 中实现纯函数或类
2. 加测试
3. 再在 `apps/streamlit_app.py` 中接入
4. 如果 CLI 也需要，再接入 `src/quant_system/cli.py`
5. 更新 README 和文档

这样可以避免把核心逻辑困在 UI 代码里。

