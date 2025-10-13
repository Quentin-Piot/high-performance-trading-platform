import io
import json

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def _make_csv(prices):
    lines = ["date,close"]
    for i, p in enumerate(prices, start=1):
        lines.append(f"2023-01-{i:02d},{p}")
    return "\n".join(lines) + "\n"


def test_backtest_ok_200():
    csv = _make_csv([100, 101, 102, 103, 104, 105])
    files = {"csv": ("prices.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    resp = client.post("/api/v1/backtest?sma_short=2&sma_long=3", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert "equity_curve" in body and "pnl" in body and "drawdown" in body and "sharpe" in body
    assert len(body["equity_curve"]) == 6


def test_backtest_invalid_params_400():
    csv = _make_csv([100, 99, 101, 100])
    files = {"csv": ("prices.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    # Test with missing strategy parameter - should return 400 for unsupported strategy
    resp = client.post("/api/v1/backtest?strategy=unknown_strategy", files=files)
    assert resp.status_code == 400
    body = resp.json()
    assert "detail" in body and isinstance(body["detail"], str)


def test_backtest_query_validation_422():
    csv = _make_csv([100, 101, 102])
    files = {"csv": ("prices.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    resp = client.post("/api/v1/backtest?sma_short=0&sma_long=3", files=files)
    assert resp.status_code == 422