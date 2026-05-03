from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Mapping

import pandas as pd


def write_analysis_html(report: Mapping[str, object], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    signals = pd.DataFrame([report.get("signals", {})]).T.reset_index()
    signals.columns = ["signal", "value"]
    performance = pd.DataFrame([report.get("performance", {})]).T.reset_index()
    performance.columns = ["metric", "value"]
    body = f"""
    <h1>{escape(str(report.get("symbol", "")))} Analysis</h1>
    <p class="muted">{escape(str(report.get("market", "")))} | {escape(str(report.get("date", "")))}</p>
    <section class="cards">
      <div><span>Close</span><strong>{float(report.get("close", 0.0)):.4f}</strong></div>
      <div><span>Trend</span><strong>{escape(str(report.get("trend", "")))}</strong></div>
      <div><span>Score</span><strong>{float(report.get("score", 0.0)):.2f}/100</strong></div>
    </section>
    <h2>Signals</h2>
    {signals.to_html(index=False, classes="table", border=0)}
    <h2>Performance</h2>
    {performance.to_html(index=False, classes="table", border=0)}
    """
    path.write_text(_page("Stock Analysis", body), encoding="utf-8")
    return path


def write_backtest_html(
    equity_curve: pd.DataFrame,
    metrics: Mapping[str, float],
    output_path: str | Path,
    title: str = "Backtest Report",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics_table = pd.DataFrame([metrics]).T.reset_index()
    metrics_table.columns = ["metric", "value"]
    body = f"""
    <h1>{escape(title)}</h1>
    <section class="cards">
      <div><span>Total Return</span><strong>{metrics.get("total_return", 0.0):.2%}</strong></div>
      <div><span>Sharpe</span><strong>{metrics.get("sharpe", 0.0):.2f}</strong></div>
      <div><span>Max Drawdown</span><strong>{metrics.get("max_drawdown", 0.0):.2%}</strong></div>
    </section>
    <h2>Equity Curve</h2>
    {_svg_line(equity_curve["equity"], color="#2563eb")}
    <h2>Drawdown</h2>
    {_svg_line(equity_curve["drawdown"], color="#dc2626")}
    <h2>Metrics</h2>
    {metrics_table.to_html(index=False, classes="table", border=0)}
    """
    path.write_text(_page(title, body), encoding="utf-8")
    return path


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #111827; }}
    h1 {{ margin-bottom: 4px; }}
    h2 {{ margin-top: 28px; }}
    .muted {{ color: #6b7280; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 20px 0; }}
    .cards div {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }}
    .cards span {{ display: block; color: #6b7280; font-size: 13px; }}
    .cards strong {{ display: block; margin-top: 6px; font-size: 22px; }}
    .table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
    .table th, .table td {{ border-bottom: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; }}
    .table th {{ background: #f9fafb; }}
    svg {{ width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""


def _svg_line(series: pd.Series, color: str = "#2563eb", width: int = 900, height: int = 260) -> str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return "<p>No data.</p>"
    min_value = float(values.min())
    max_value = float(values.max())
    value_range = max(max_value - min_value, 1e-12)
    x_step = width / max(len(values) - 1, 1)
    points = []
    for index, value in enumerate(values):
        x = index * x_step
        y = height - ((float(value) - min_value) / value_range) * (height - 24) - 12
        points.append(f"{x:.2f},{y:.2f}")
    polyline = " ".join(points)
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="line chart">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{polyline}" />'
        "</svg>"
    )

