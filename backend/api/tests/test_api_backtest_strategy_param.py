import io

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _make_csv(prices):
    lines = ["date,close"]
    for i, p in enumerate(prices, start=1):
        lines.append(f"2023-01-{i:02d},{p}")
    return "\n".join(lines) + "\n"


def test_backtest_rsi_ok_200():
    csv = _make_csv([100, 101, 102, 101, 100, 99, 100])
    files = {"csv": ("prices.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    resp = client.post(
        "/api/v1/backtest?strategy=rsi&period=14&overbought=70&oversold=30",
        files=files,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "equity_curve" in body and "pnl" in body and "drawdown" in body and "sharpe" in body


def test_backtest_unknown_strategy_400():
    csv = _make_csv([100, 101, 102, 103])
    files = {"csv": ("prices.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    resp = client.post("/api/v1/backtest?strategy=unknown", files=files)
    assert resp.status_code == 400
    body = resp.json()
    assert "detail" in body and "Unsupported strategy" in body["detail"]
