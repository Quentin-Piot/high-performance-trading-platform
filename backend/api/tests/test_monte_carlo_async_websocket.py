import time

import pytest


def test_monte_carlo_async_websocket_progress(client):
    """Soumet un job Monte Carlo async et vérifie les updates via WebSocket."""
    # Soumission du job asynchrone
    params = {
        "symbol": "aapl",
        "start_date": "2017-01-01",
        "end_date": "2018-01-31",
        "num_runs": 30,
        "initial_capital": 10000,
        "strategy": "sma_crossover",
        "sma_short": 10,
        "sma_long": 20,
        "normalize": True,
    }
    resp = client.post("/api/v1/monte-carlo/async", params=params)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("status") == "submitted"
    job_id = data.get("job_id")
    assert isinstance(job_id, str) and len(job_id) > 0

    # Connexion au WebSocket de progression
    progress_values = []
    statuses = []
    ws_path = f"/api/v1/monte-carlo/ws/{job_id}"
    timeout_seconds = 30
    start_time = time.time()
    with client.websocket_connect(ws_path) as ws:
        while True:
            # Timeout pour éviter les tests bloqués
            if time.time() - start_time > timeout_seconds:
                pytest.fail("Timeout: le job Monte Carlo n'a pas terminé dans le délai imparti")
            msg = ws.receive_json()
            assert "status" in msg
            statuses.append(msg["status"])
            # La clé progress peut ne pas être présente dans les toutes premières réponses
            if "progress" in msg and msg["progress"] is not None:
                progress_values.append(float(msg["progress"]))
            if msg["status"] in {"completed", "failed", "cancelled"}:
                break

    # Vérifications de progression
    assert len(progress_values) >= 1, "Aucune mise à jour de progression reçue"
    assert progress_values[0] >= 0.0
    # progression non décroissante
    assert all(x2 + 1e-9 >= x1 for x1, x2 in zip(progress_values, progress_values[1:], strict=False)), (
        f"Progression non monotone: {progress_values}"
    )
    # Le dernier statut doit être completed et la progression à 1.0
    assert statuses[-1] == "completed", f"Statut final inattendu: {statuses[-1]}"
    assert progress_values[-1] == pytest.approx(1.0, rel=1e-6, abs=1e-6)

    # Vérifie l'endpoint HTTP de statut pour cohérence
    status_resp = client.get(f"/api/v1/monte-carlo/async/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "completed"
    assert status_data.get("result") is not None
    metrics = status_data["result"].get("metrics_distribution")
    assert metrics is not None and "pnl" in metrics and "sharpe" in metrics and "drawdown" in metrics
