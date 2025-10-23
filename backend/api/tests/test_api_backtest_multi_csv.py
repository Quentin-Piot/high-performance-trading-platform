import io

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _make_csv(prices, filename="prices.csv"):
    """Helper to create CSV content"""
    lines = ["date,close"]
    for i, price in enumerate(prices):
        lines.append(f"2023-01-{i + 1:02d},{price}")
    return "\n".join(lines)


def test_backtest_single_csv_backward_compatibility():
    """Test that single CSV still works as before"""
    csv_content = _make_csv([100, 101, 102, 103, 104])
    files = {"csv": ("prices.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}

    resp = client.post(
        "/api/v1/backtest?strategy=sma_crossover&sma_short=2&sma_long=3", files=files
    )
    assert resp.status_code == 200

    body = resp.json()
    # Should return single file format for backward compatibility
    assert "timestamps" in body
    assert "equity_curve" in body
    assert "pnl" in body
    assert "drawdown" in body
    assert "sharpe" in body
    assert "results" not in body  # Should not have multi-file format


def test_backtest_multiple_csv_files():
    """Test processing multiple CSV files"""
    csv1 = _make_csv([100, 101, 102, 103, 104])
    csv2 = _make_csv([200, 201, 202, 203, 204])
    csv3 = _make_csv([150, 151, 152, 153, 154])

    files = [
        ("csv", ("file1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")),
        ("csv", ("file2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")),
        ("csv", ("file3.csv", io.BytesIO(csv3.encode("utf-8")), "text/csv")),
    ]

    resp = client.post(
        "/api/v1/backtest?strategy=sma_crossover&sma_short=2&sma_long=3", files=files
    )
    assert resp.status_code == 200

    body = resp.json()
    # Should return multi-file format
    assert "results" in body
    assert len(body["results"]) == 3

    # Check each result has required fields
    for i, result in enumerate(body["results"]):
        assert "filename" in result
        assert "timestamps" in result
        assert "equity_curve" in result
        assert "pnl" in result
        assert "drawdown" in result
        assert "sharpe" in result
        assert result["filename"] == f"file{i + 1}.csv"


def test_backtest_multiple_csv_with_aggregated_metrics():
    """Test multiple CSV files with aggregated metrics"""
    csv1 = _make_csv([100, 101, 102, 103, 104])
    csv2 = _make_csv([200, 201, 202, 203, 204])

    files = [
        ("csv", ("file1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")),
        ("csv", ("file2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")),
    ]

    resp = client.post(
        "/api/v1/backtest?strategy=sma_crossover&sma_short=2&sma_long=3&include_aggregated=true",
        files=files,
    )
    assert resp.status_code == 200

    body = resp.json()
    assert "results" in body
    assert "aggregated_metrics" in body
    assert body["aggregated_metrics"] is not None

    # Check aggregated metrics structure
    agg = body["aggregated_metrics"]
    assert "average_pnl" in agg
    assert "average_sharpe" in agg
    assert "average_drawdown" in agg
    assert "total_files_processed" in agg
    assert agg["total_files_processed"] == 2


def test_backtest_single_csv_with_aggregated_flag():
    """Test single CSV with aggregated flag returns multi-file format"""
    csv_content = _make_csv([100, 101, 102, 103, 104])
    files = {"csv": ("prices.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}

    resp = client.post(
        "/api/v1/backtest?strategy=sma_crossover&sma_short=2&sma_long=3&include_aggregated=true",
        files=files,
    )
    assert resp.status_code == 200

    body = resp.json()
    # Should return multi-file format when aggregated is requested
    assert "results" in body
    assert "aggregated_metrics" in body
    assert len(body["results"]) == 1


def test_backtest_too_many_files():
    """Test validation for maximum file limit"""
    files = []
    for i in range(11):  # 11 files, should exceed limit
        csv_content = _make_csv([100, 101, 102, 103])
        files.append(
            (
                "csv",
                (f"file{i}.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv"),
            )
        )

    resp = client.post(
        "/api/v1/backtest?strategy=sma_crossover&sma_short=2&sma_long=3", files=files
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "Maximum of 10 CSV files allowed" in body["detail"]


def test_backtest_rsi_multiple_files():
    """Test RSI strategy with multiple files"""
    # Use more data points for RSI calculation (RSI needs more data to avoid NaN)
    csv1 = _make_csv(
        [
            100,
            101,
            102,
            103,
            104,
            105,
            106,
            107,
            108,
            109,
            110,
            111,
            112,
            113,
            114,
            115,
            116,
            117,
            118,
            119,
            120,
        ]
    )
    csv2 = _make_csv(
        [
            200,
            201,
            202,
            203,
            204,
            205,
            206,
            207,
            208,
            209,
            210,
            211,
            212,
            213,
            214,
            215,
            216,
            217,
            218,
            219,
            220,
        ]
    )

    files = [
        ("csv", ("rsi1.csv", io.BytesIO(csv1.encode("utf-8")), "text/csv")),
        ("csv", ("rsi2.csv", io.BytesIO(csv2.encode("utf-8")), "text/csv")),
    ]

    # Use period=14 (standard RSI period) instead of 5 to get better results
    resp = client.post(
        "/api/v1/backtest?strategy=rsi&period=14&overbought=70&oversold=30", files=files
    )

    # Debug: print response details if it fails
    if resp.status_code != 200:
        print(f"Response status: {resp.status_code}")
        print(f"Response body: {resp.text}")

    assert resp.status_code == 200

    body = resp.json()
    assert "results" in body
    assert len(body["results"]) == 2

    for result in body["results"]:
        assert "filename" in result
        assert result["filename"] in ["rsi1.csv", "rsi2.csv"]


def test_backtest_invalid_csv_in_batch():
    """Test error handling when one CSV in batch is invalid"""
    valid_csv = _make_csv([100, 101, 102, 103, 104])
    invalid_csv = "invalid,csv,content\nno,date,column"

    files = [
        ("csv", ("valid.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")),
        ("csv", ("invalid.csv", io.BytesIO(invalid_csv.encode("utf-8")), "text/csv")),
    ]

    resp = client.post(
        "/api/v1/backtest?strategy=sma_crossover&sma_short=2&sma_long=3", files=files
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "Error processing file" in body["detail"]
    assert "invalid.csv" in body["detail"]
