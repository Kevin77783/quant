from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_system.analysis import analyze_prices, screen_universe
from quant_system.backtest import BacktestConfig, BacktestEngine, PortfolioBacktestConfig, PortfolioBacktestEngine
from quant_system.config import load_yaml, parse_universe, parse_universe_argument
from quant_system.data import DataProvider
from quant_system.reporting import write_analysis_html, write_backtest_html
from quant_system.strategies import build_strategy
from quant_system.workflows import ProviderSettings, build_data_provider


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
    try:
        return int(args.func(args))
    except Exception as exc:
        parser.exit(2, f"error: {exc}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quant",
        description="Multi-market stock quant analysis and backtesting CLI.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable info-level runtime logs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check runtime dependencies and optional data providers.")
    doctor.set_defaults(func=cmd_doctor)

    analyze = subparsers.add_parser("analyze", help="Analyze one stock.")
    add_data_args(analyze)
    analyze.add_argument("--symbol", required=True, help="Stock symbol, for example 000001.SZ, 0700.HK, AAPL.")
    analyze.add_argument("--market", required=True, choices=["cn", "hk", "us"], help="Market code.")
    analyze.add_argument("--risk-free-rate", type=float, default=0.0)
    analyze.add_argument("--output", help="Optional JSON output path.")
    analyze.add_argument("--html-report", help="Optional HTML analysis report path.")
    analyze.set_defaults(func=cmd_analyze)

    backtest = subparsers.add_parser("backtest", help="Backtest one stock strategy.")
    add_data_args(backtest)
    add_strategy_args(backtest)
    backtest.add_argument("--symbol", required=True)
    backtest.add_argument("--market", required=True, choices=["cn", "hk", "us"])
    backtest.add_argument("--initial-cash", type=float, default=100000.0)
    backtest.add_argument("--commission-bps", type=float, default=2.0)
    backtest.add_argument("--slippage-bps", type=float, default=1.0)
    backtest.add_argument("--risk-free-rate", type=float, default=0.0)
    backtest.add_argument("--output-dir", default="reports/backtest", help="Directory for CSV outputs.")
    backtest.add_argument("--html-report", help="Optional HTML report path.")
    backtest.set_defaults(func=cmd_backtest)

    portfolio = subparsers.add_parser("portfolio", help="Backtest a factor-ranked multi-stock portfolio.")
    add_data_args(portfolio)
    portfolio.add_argument("--config", default="configs/default.yaml", help="YAML config with universe.")
    portfolio.add_argument(
        "--universe",
        default="",
        help="Override config universe. Format: 000001.SZ:cn,0700.HK:hk,AAPL:us",
    )
    portfolio.add_argument("--top-n", type=int, default=None, help="Number of stocks held after each rebalance.")
    portfolio.add_argument("--rebalance-frequency", type=int, default=None, help="Trading-day rebalance interval.")
    portfolio.add_argument("--weighting", choices=["equal", "inverse_vol"], default=None)
    portfolio.add_argument("--initial-cash", type=float, default=None)
    portfolio.add_argument("--commission-bps", type=float, default=None)
    portfolio.add_argument("--slippage-bps", type=float, default=None)
    portfolio.add_argument("--risk-free-rate", type=float, default=None)
    portfolio.add_argument("--output-dir", default="reports/portfolio", help="Directory for portfolio CSV outputs.")
    portfolio.add_argument("--html-report", help="Optional HTML report path.")
    portfolio.set_defaults(func=cmd_portfolio)

    screen = subparsers.add_parser("screen", help="Rank a multi-market stock universe.")
    add_data_args(screen)
    screen.add_argument("--config", default="configs/default.yaml", help="YAML config with universe.")
    screen.add_argument(
        "--universe",
        default="",
        help="Override config universe. Format: 000001.SZ:cn,0700.HK:hk,AAPL:us",
    )
    screen.add_argument("--top", type=int, default=10)
    screen.add_argument("--output", help="Optional CSV output path.")
    screen.set_defaults(func=cmd_screen)
    return parser


def add_data_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", choices=["csv", "auto", "akshare", "yahoo"], default="csv")
    parser.add_argument("--data-file", default="data/sample_prices.csv", help="CSV file or directory for local data.")
    parser.add_argument("--cache-dir", default="data", help="Root directory containing raw/processed data caches.")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache read/write for online providers.")
    parser.add_argument("--start", help="Start date, for example 2025-01-01.")
    parser.add_argument("--end", help="End date, for example 2025-12-31.")
    parser.add_argument("--adjust", default="qfq", help="Adjustment mode for online providers.")
    parser.add_argument("--interval", default="1d", help="Bar interval.")


def add_strategy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--strategy", choices=["ma", "rsi", "breakout"], default="ma")
    parser.add_argument("--short-window", type=int, default=5)
    parser.add_argument("--long-window", type=int, default=20)
    parser.add_argument("--window", type=int, default=20, help="Window used by breakout strategy.")
    parser.add_argument("--oversold", type=float, default=30.0)
    parser.add_argument("--overbought", type=float, default=70.0)
    parser.add_argument("--max-weight", type=float, default=1.0)


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = {
        "numpy": _import_status("numpy"),
        "pandas": _import_status("pandas"),
        "yaml": _import_status("yaml"),
        "akshare": _import_status("akshare"),
        "yfinance": _import_status("yfinance"),
        "streamlit": _import_status("streamlit"),
        "plotly": _import_status("plotly"),
    }
    print("Runtime check")
    for name, status in checks.items():
        print(f"  {name:<8} {status}")
    print("\nCore workflow works offline with --provider csv and data/sample_prices.csv.")
    if checks["akshare"].startswith("missing") or checks["yfinance"].startswith("missing"):
        print("Online A/HK/US data requires optional packages: pip install -e '.[data]'.")
    else:
        print("Online data providers are installed. Use --provider auto/yahoo/akshare.")
    if checks["streamlit"].startswith("missing") or checks["plotly"].startswith("missing"):
        print("Streamlit UI requires: pip install -e '.[app]'.")
    else:
        print("Streamlit UI is installed. Run: streamlit run apps/streamlit_app.py")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    provider = build_provider(args.provider, args.data_file, args.cache_dir, not args.no_cache)
    prices = provider.get_history(
        args.symbol,
        args.market,
        start=args.start,
        end=args.end,
        adjust=args.adjust,
        interval=args.interval,
    )
    report = analyze_prices(prices, risk_free_rate=args.risk_free_rate)
    print_analysis(report)
    if args.output:
        write_json(args.output, report)
        print(f"\nWrote {args.output}")
    if args.html_report:
        write_analysis_html(report, args.html_report)
        print(f"Wrote {args.html_report}")
    return 0


def cmd_backtest(args: argparse.Namespace) -> int:
    provider = build_provider(args.provider, args.data_file, args.cache_dir, not args.no_cache)
    prices = provider.get_history(
        args.symbol,
        args.market,
        start=args.start,
        end=args.end,
        adjust=args.adjust,
        interval=args.interval,
    )
    strategy = build_strategy(
        args.strategy,
        short_window=args.short_window,
        long_window=args.long_window,
        window=args.window,
        oversold=args.oversold,
        overbought=args.overbought,
        max_weight=args.max_weight,
    )
    engine = BacktestEngine(
        BacktestConfig(
            initial_cash=args.initial_cash,
            commission_bps=args.commission_bps,
            slippage_bps=args.slippage_bps,
            risk_free_rate=args.risk_free_rate,
        )
    )
    result = engine.run(prices, strategy)
    result.save(args.output_dir)
    if args.html_report:
        write_backtest_html(result.equity_curve, result.metrics, args.html_report, title=f"{args.symbol} Backtest")
    print(f"Backtest: {args.symbol} {args.market} strategy={strategy.name}")
    print_metrics(result.metrics)
    print(f"Trades: {len(result.trades)}")
    print(f"Wrote {args.output_dir}")
    if args.html_report:
        print(f"Wrote {args.html_report}")
    return 0


def cmd_portfolio(args: argparse.Namespace) -> int:
    config = load_yaml(args.config) if args.config else {}
    universe = parse_universe_argument(args.universe) if args.universe else parse_universe(config)
    if not universe:
        raise ValueError("Universe is empty. Use --config or --universe.")
    data_config = config.get("data", {})
    backtest_config = config.get("backtest", {})
    portfolio_config = config.get("portfolio", {})
    provider = build_provider(
        args.provider or data_config.get("provider", "csv"),
        args.data_file or data_config.get("local_file"),
        args.cache_dir or data_config.get("cache_dir", "data"),
        not args.no_cache,
    )
    engine = PortfolioBacktestEngine(
        PortfolioBacktestConfig(
            initial_cash=_coalesce(args.initial_cash, backtest_config.get("initial_cash", 100000.0)),
            commission_bps=_coalesce(args.commission_bps, backtest_config.get("commission_bps", 2.0)),
            slippage_bps=_coalesce(args.slippage_bps, backtest_config.get("slippage_bps", 1.0)),
            risk_free_rate=_coalesce(args.risk_free_rate, backtest_config.get("risk_free_rate", 0.0)),
            top_n=int(_coalesce(args.top_n, portfolio_config.get("top_n", 5))),
            rebalance_frequency=int(_coalesce(args.rebalance_frequency, portfolio_config.get("rebalance_frequency", 20))),
            weighting=str(_coalesce(args.weighting, portfolio_config.get("weighting", "equal"))),
        )
    )
    result = engine.run(universe, provider, start=args.start, end=args.end)
    result.save(args.output_dir)
    if args.html_report:
        write_backtest_html(result.equity_curve, result.metrics, args.html_report, title="Portfolio Backtest")
    print("Portfolio backtest")
    print_metrics(result.metrics)
    print(f"Rebalances: {int(result.metrics.get('rebalance_count', 0))}")
    print(f"Loaded symbols: {int(result.metrics.get('loaded_symbols', 0))}")
    print(f"Failed symbols: {int(result.metrics.get('failed_symbols', 0))}")
    print(f"Wrote {args.output_dir}")
    if args.html_report:
        print(f"Wrote {args.html_report}")
    return 0


def cmd_screen(args: argparse.Namespace) -> int:
    config = load_yaml(args.config) if args.config else {}
    universe = parse_universe_argument(args.universe) if args.universe else parse_universe(config)
    if not universe:
        raise ValueError("Universe is empty. Use --config or --universe.")
    data_config = config.get("data", {})
    provider_name = args.provider or data_config.get("provider", "csv")
    local_file = args.data_file or data_config.get("local_file")
    provider = build_provider(provider_name, local_file, args.cache_dir, not args.no_cache)
    ranked = screen_universe(universe, provider, start=args.start, end=args.end, top=args.top)
    print(ranked.drop(columns=["turnover_proxy"]).to_string(index=False))
    failures = ranked.attrs.get("failures", [])
    if failures:
        print("\nSkipped:")
        for failure in failures:
            print(f"  {failure}")
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        ranked.to_csv(args.output, index=False)
        print(f"\nWrote {args.output}")
    return 0


def build_provider(
    name: str,
    data_file: str | None,
    cache_dir: str = "data",
    use_cache: bool = True,
) -> DataProvider:
    return build_data_provider(
        ProviderSettings(provider=name, data_file=data_file, cache_dir=cache_dir, use_cache=use_cache)
    )


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _coalesce(value: Any, fallback: Any) -> Any:
    return fallback if value is None else value


def print_analysis(report: dict[str, Any]) -> None:
    print(f"{report['symbol']} ({report['market']}) {report['date']}")
    print(f"  close        {report['close']:.4f}")
    print(f"  trend        {report['trend']}")
    print(f"  score        {report['score']:.2f}/100")
    print("Signals")
    for key, value in report["signals"].items():
        print(f"  {key:<18} {value}")
    print("Performance")
    print_metrics(report["performance"])


def print_metrics(metrics: dict[str, float]) -> None:
    preferred = [
        "total_return",
        "annual_return",
        "annual_volatility",
        "sharpe",
        "max_drawdown",
        "win_rate",
        "benchmark_total_return",
        "excess_total_return",
    ]
    for key in preferred:
        if key in metrics:
            print(f"  {key:<24} {metrics[key]: .6f}")


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        json.dump(_json_ready(payload), file, ensure_ascii=False, indent=2)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def _import_status(module: str) -> str:
    try:
        imported = __import__(module)
    except Exception:
        return "missing"
    version = getattr(imported, "__version__", "")
    return f"ok {version}".strip()


if __name__ == "__main__":
    raise SystemExit(main())
