import io
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def _make_csv(prices):
    lines = ["date,close"]
    for i, p in enumerate(prices, start=1):
        lines.append(f"2023-01-{i:02d},{p}")
    return "\n".join(lines) + "\n"


def test_backtest_unsupported_strategy_param_400():
    csv = _make_csv([100, 101, 102, 103])
    files = {"csv": ("prices.csv", io.BytesIO(csv.encode("utf-8")), "text/csv")}
    resp = client.post("/backtest?sma_short=2&sma_long=3&strategy=rsi_reversion", files=files)
    assert resp.status_code == 400
    body = resp.json()
    assert "detail" in body and "non prise en charge" in body["detail"]