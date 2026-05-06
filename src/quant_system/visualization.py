from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from quant_system.analysis.indicators import add_indicators
from quant_system.models import normalize_ohlcv


def make_candlestick_figure(prices: pd.DataFrame, title: str = "Price") -> go.Figure:
    """Build an interactive candlestick chart with volume, RSI, and MACD."""

    data = add_indicators(normalize_ohlcv(prices))
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.52, 0.16, 0.16, 0.16],
        vertical_spacing=0.03,
        subplot_titles=(title, "Volume", "RSI", "MACD"),
    )
    fig.add_trace(
        go.Candlestick(
            x=data["date"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            name="K Line",
            increasing_line_color="#16a34a",
            decreasing_line_color="#dc2626",
        ),
        row=1,
        col=1,
    )
    for column, color in (("sma_5", "#2563eb"), ("sma_20", "#f59e0b"), ("sma_60", "#7c3aed")):
        if column in data:
            fig.add_trace(go.Scatter(x=data["date"], y=data[column], name=column.upper(), line=dict(width=1.6, color=color)), row=1, col=1)

    up = data["close"] >= data["open"]
    volume_colors = up.map({True: "#16a34a", False: "#dc2626"}).tolist()
    fig.add_trace(go.Bar(x=data["date"], y=data["volume"], name="Volume", marker_color=volume_colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=data["date"], y=data["rsi"], name="RSI", line=dict(color="#0891b2", width=1.6)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#dc2626", row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#16a34a", row=3, col=1)
    fig.add_trace(go.Scatter(x=data["date"], y=data["macd"], name="MACD", line=dict(color="#2563eb", width=1.4)), row=4, col=1)
    fig.add_trace(
        go.Scatter(x=data["date"], y=data["macd_signal"], name="Signal", line=dict(color="#f59e0b", width=1.4)),
        row=4,
        col=1,
    )
    macd_colors = (data["macd_hist"] >= 0).map({True: "#16a34a", False: "#dc2626"}).tolist()
    fig.add_trace(go.Bar(x=data["date"], y=data["macd_hist"], name="Hist", marker_color=macd_colors), row=4, col=1)
    return _style_figure(fig, height=760, show_rangeslider=False)


def make_factor_bar(signals: dict[str, float]) -> go.Figure:
    keys = [
        "trend_score",
        "momentum_20_pct",
        "momentum_60_pct",
        "volatility_20",
        "liquidity_score",
        "rsi_balance_score",
        "macd_hist",
        "atr_pct",
        "drawdown",
    ]
    frame = pd.DataFrame({"factor": keys, "value": [signals.get(key, 0.0) for key in keys]})
    colors = ["#16a34a" if value >= 0 else "#dc2626" for value in frame["value"]]
    fig = go.Figure(go.Bar(x=frame["value"], y=frame["factor"], orientation="h", marker_color=colors))
    fig.update_layout(title="Factor Snapshot", height=380)
    return _style_figure(fig)


def make_score_gauge(score: float) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#2563eb"},
                "steps": [
                    {"range": [0, 40], "color": "#fee2e2"},
                    {"range": [40, 70], "color": "#fef3c7"},
                    {"range": [70, 100], "color": "#dcfce7"},
                ],
            },
        )
    )
    fig.update_layout(height=260, margin=dict(l=16, r=16, t=20, b=16))
    return fig


def make_equity_drawdown_figure(equity_curve: pd.DataFrame, title: str = "Equity and Drawdown") -> go.Figure:
    data = equity_curve.copy()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=data["date"], y=data["equity"], name="Strategy", line=dict(color="#2563eb", width=2)), row=1, col=1)
    if "benchmark_equity" in data:
        fig.add_trace(
            go.Scatter(x=data["date"], y=data["benchmark_equity"], name="Benchmark", line=dict(color="#64748b", width=1.8)),
            row=1,
            col=1,
        )
    fig.add_trace(
        go.Scatter(x=data["date"], y=data["drawdown"], name="Drawdown", fill="tozeroy", line=dict(color="#dc2626", width=1.5)),
        row=2,
        col=1,
    )
    fig.update_layout(title=title, height=520)
    return _style_figure(fig)


def make_screen_scatter(ranked: pd.DataFrame) -> go.Figure:
    if ranked.empty:
        fig = go.Figure()
        fig.add_annotation(text="No securities match the current filters.", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Score vs Volatility", height=460, xaxis_title="20D Volatility", yaxis_title="Score")
        return _style_figure(fig)
    fig = go.Figure(
        go.Scatter(
            x=ranked["volatility_20"],
            y=ranked["score"],
            mode="markers+text",
            text=ranked["symbol"],
            textposition="top center",
            marker=dict(
                size=(ranked["liquidity_score"].clip(lower=-1) + 1.2) * 14,
                color=ranked["momentum_20_pct"],
                colorscale="RdYlGn",
                showscale=True,
                colorbar=dict(title="Mom 20%"),
                line=dict(width=1, color="#334155"),
            ),
            customdata=ranked[["market", "trend", "rsi"]],
            hovertemplate="symbol=%{text}<br>market=%{customdata[0]}<br>score=%{y:.2f}<br>vol=%{x:.2%}<br>trend=%{customdata[1]}<br>rsi=%{customdata[2]:.2f}<extra></extra>",
        )
    )
    fig.update_layout(title="Score vs Volatility", height=460, xaxis_title="20D Volatility", yaxis_title="Score")
    return _style_figure(fig)


def make_weights_figure(weights: pd.DataFrame) -> go.Figure:
    data = weights.copy()
    date = data.pop("date")
    fig = go.Figure()
    for column in data.columns:
        fig.add_trace(go.Scatter(x=date, y=data[column], mode="lines", stackgroup="one", name=column))
    fig.update_layout(title="Portfolio Weights", height=420, yaxis_tickformat=".0%")
    return _style_figure(fig)


def make_normalized_performance_figure(normalized: pd.DataFrame) -> go.Figure:
    data = normalized.copy()
    date = data.pop("date")
    fig = go.Figure()
    for column in data.columns:
        fig.add_trace(go.Scatter(x=date, y=data[column], mode="lines", name=column, line=dict(width=2)))
    fig.update_layout(title="Normalized Performance", height=460, yaxis_title="Base 100")
    return _style_figure(fig)


def make_correlation_heatmap(correlation: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Heatmap(
            z=correlation.values,
            x=correlation.columns,
            y=correlation.index,
            zmin=-1,
            zmax=1,
            colorscale="RdBu",
            reversescale=True,
            colorbar=dict(title="Corr"),
            hovertemplate="%{y} vs %{x}<br>corr=%{z:.2f}<extra></extra>",
        )
    )
    fig.update_layout(title="Return Correlation", height=460)
    return _style_figure(fig)


def make_risk_return_scatter(summary: pd.DataFrame) -> go.Figure:
    if summary.empty:
        fig = go.Figure()
        fig.add_annotation(text="No comparison data.", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Risk / Return", height=430)
        return _style_figure(fig)
    fig = go.Figure(
        go.Scatter(
            x=summary["annual_volatility"],
            y=summary["total_return"],
            mode="markers+text",
            text=summary["symbol"],
            textposition="top center",
            marker=dict(
                size=(summary["sharpe"].clip(lower=-1, upper=3) + 1.5) * 10,
                color=summary["max_drawdown"],
                colorscale="RdYlGn",
                showscale=True,
                colorbar=dict(title="Max DD"),
                line=dict(color="#334155", width=1),
            ),
            customdata=summary[["market", "sharpe", "win_rate"]],
            hovertemplate="symbol=%{text}<br>market=%{customdata[0]}<br>return=%{y:.2%}<br>vol=%{x:.2%}<br>sharpe=%{customdata[1]:.2f}<br>win=%{customdata[2]:.2%}<extra></extra>",
        )
    )
    fig.update_layout(title="Risk / Return", height=430, xaxis_title="Annual Volatility", yaxis_title="Total Return")
    return _style_figure(fig)


def make_optimization_heatmap(results: pd.DataFrame, metric: str = "sharpe") -> go.Figure:
    pivot = results.pivot(index="long_window", columns="short_window", values=metric).sort_index(ascending=False)
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="Viridis",
            colorbar=dict(title=metric),
            hovertemplate="short=%{x}<br>long=%{y}<br>" + metric + "=%{z:.4f}<extra></extra>",
        )
    )
    fig.update_layout(title=f"MA Optimization: {metric}", height=430, xaxis_title="Short Window", yaxis_title="Long Window")
    return _style_figure(fig)


def make_alerts_bar(alerts: pd.DataFrame) -> go.Figure:
    if alerts.empty:
        fig = go.Figure()
        fig.add_annotation(text="No alerts triggered.", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Alerts", height=360)
        return _style_figure(fig)
    fig = go.Figure(
        go.Bar(
            x=alerts["symbol"],
            y=alerts["trigger_count"],
            marker_color=alerts["score"],
            marker_colorscale="RdYlGn",
            text=alerts["alerts"],
            hovertemplate="%{x}<br>triggers=%{y}<br>%{text}<extra></extra>",
        )
    )
    fig.update_layout(title="Alert Trigger Count", height=360, xaxis_title="Symbol", yaxis_title="Triggers")
    return _style_figure(fig)


def _style_figure(fig: go.Figure, height: int | None = None, show_rangeslider: bool = False) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=28, r=28, t=48, b=28),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        hovermode="x unified",
    )
    if height is not None:
        fig.update_layout(height=height)
    fig.update_xaxes(showgrid=False, rangeslider_visible=show_rangeslider)
    fig.update_yaxes(gridcolor="#e5e7eb", zerolinecolor="#cbd5e1")
    return fig
