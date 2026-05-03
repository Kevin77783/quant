from quant_system.analysis import analyze_prices
from quant_system.data import CSVDataProvider
from quant_system.reporting import write_analysis_html


def test_write_analysis_html_creates_report(tmp_path) -> None:
    prices = CSVDataProvider("data/sample_prices.csv").get_history("AAPL", "us")
    report = analyze_prices(prices)
    output = tmp_path / "analysis.html"

    write_analysis_html(report, output)

    assert output.exists()
    assert "AAPL Analysis" in output.read_text(encoding="utf-8")

