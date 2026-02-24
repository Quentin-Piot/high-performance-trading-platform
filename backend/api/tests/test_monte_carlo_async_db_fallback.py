from datetime import UTC, datetime
from types import SimpleNamespace


def test_monte_carlo_async_status_falls_back_to_db_when_not_in_memory(
    client, monkeypatch
):
    class FakeWorker:
        def get_job_status(self, job_id: str):
            return None

    captured: dict[str, str | None] = {"job_id": None}

    class FakeJobRepository:
        def __init__(self, session):
            self.session = session

        async def get_job_by_id(self, job_id: str):
            captured["job_id"] = job_id
            return SimpleNamespace(
                id=job_id,
                status="completed",
                progress=1.0,
                created_at=datetime(2026, 2, 24, 10, 0, tzinfo=UTC),
                started_at=datetime(2026, 2, 24, 10, 0, 1, tzinfo=UTC),
                completed_at=datetime(2026, 2, 24, 10, 0, 3, tzinfo=UTC),
                payload={
                    "filename": "AAPL.csv",
                    "runs": 25,
                    "result": {"metrics_distribution": {"pnl": {}, "sharpe": {}, "drawdown": {}}},
                },
                error=None,
            )

    monkeypatch.setattr("workers.simple_worker.get_simple_worker", lambda: FakeWorker())
    monkeypatch.setattr("api.routes.monte_carlo.JobRepository", FakeJobRepository)

    job_id = "db-fallback-job-123"
    resp = client.get(f"/api/v1/monte-carlo/async/{job_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert captured["job_id"] == job_id
    assert data["job_id"] == job_id
    assert data["status"] == "completed"
    assert data["progress"] == 1.0
    assert data["filename"] == "AAPL.csv"
    assert data["runs"] == 25
    assert data["result"] is not None
    assert data["started_at"] is not None
    assert data["completed_at"] is not None
