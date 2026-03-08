# Testing Guide (Inventory and Coverage Map)

## Purpose

This document maps the current backend test suite to code areas and behaviors.

It is designed for:
- maintainers
- interview preparation
- RAG retrieval (“Where is X tested?”)

## Commands

## Backend quality checks

```bash
cd backend/api
make lint       # ruff
make typecheck  # basedpyright
make test       # pytest
```

## Frontend validation (current state)

The frontend does not currently include a committed test runner.

Use:

```bash
cd web
pnpm lint
pnpm build
```

And perform manual checks for:
- backtest flow
- Monte Carlo async flow (progress + result)
- auth/history UI paths

## Backend test stack

Main tools:
- `pytest`
- `pytest-asyncio` (strict mode)
- `hypothesis` (property-based tests)
- FastAPI `TestClient`

Test fixtures (`backend/api/tests/conftest.py`) include:
- test app client
- DB/session overrides (SQLite async test DB)

## Test Inventory by Area

## Backtest API route tests

### `backend/api/tests/test_api_backtest.py`
Covers:
- valid backtest request returns `200`
- invalid parameters return `400`
- FastAPI query validation returns `422`

### `backend/api/tests/test_api_backtest_strategy_param.py`
Covers:
- valid RSI strategy params
- unknown strategy handling (`400`)

### `backend/api/tests/test_api_backtest_multi_csv.py`
Covers:
- single CSV backward compatibility
- multiple CSV uploads
- aggregated metrics across files
- single CSV with aggregated flag
- max file limit (`>10`)
- invalid CSV in batch
- RSI with multiple files

## Backtest services, parsing, and validation

### `backend/api/tests/test_backtest_service.py`
Covers:
- basic SMA crossover backtest execution

### `backend/api/tests/test_backtest_service_validation.py`
Covers:
- invalid SMA parameter combinations
- missing price column errors

### `backend/api/tests/test_backtest_service_property.py`
Covers:
- output shape and invariants on generated price series (Hypothesis/property tests)

### `backend/api/tests/test_csv_parsing_financial.py`
Covers:
- `adj_close` fallback behavior
- date sorting for unsorted CSV input
- CSV without `date` column
- dropping invalid rows before series construction

### `backend/api/tests/test_service_run_sma_crossover.py`
Covers:
- valid service result contract
- invalid params raise errors

## Strategy correctness and financial metrics

### `backend/api/tests/test_metrics_financial.py`
Covers:
- `sharpe_ratio` edge cases (zero returns / NaN-safe behavior)
- `max_drawdown` on known equity path
- `total_return` basic and empty cases
- `trade_summary_from_positions` entry/exit pairing logic
- handling series starting already in position

### `backend/api/tests/test_moving_average_strategy_correctness.py`
Covers:
- SMA strategy waits for long window before entering position

### `backend/api/tests/test_rsi_strategy_correctness.py`
Covers:
- RSI behavior on monotonic uptrend
- exit threshold semantics in RSI strategy

## Monte Carlo tests

### `backend/api/tests/test_monte_carlo_sync.py`
Covers:
- sync Monte Carlo route forwards method/method params/price type correctly to service

### `backend/api/tests/test_monte_carlo_service_correctness.py`
Covers:
- bootstrap preserves length/index semantics
- `compute_equity_envelope` timestamp alignment
- strategy alias support and `initial_capital` forwarding

### `backend/api/tests/test_monte_carlo_async_websocket.py`
Covers:
- async Monte Carlo WebSocket progress updates (high-value test for UI demo credibility)

### `backend/api/tests/test_monte_carlo_async_db_fallback.py`
Covers:
- async status endpoint fallback to DB when runtime job is absent from in-memory worker state

## History and performance endpoints

### `backend/api/tests/test_history_endpoints.py`
Covers:
- authenticated history listing/stats/detail/delete/rerun behaviors (depending on fixture setup)

### `backend/api/tests/test_load_performance.py`
Covers:
- performance/load-oriented API checks (project-specific perf endpoints and response behavior)

## What Is Covered Well (Strengths)

- API validation and error cases
- CSV parsing edge cases
- strategy correctness details
- financial metric correctness
- async Monte Carlo WebSocket progress
- async DB fallback behavior
- property-based testing on backtest output structure

## Known Gaps (Current State)

- no automated frontend component/E2E tests
- no restart-recovery tests for async jobs (feature not implemented)
- no distributed queue worker tests (queue not implemented)
- limited full-stack end-to-end browser automation

## RAG Retrieval Tips

For questions like “Is X tested?” index these first:
- `backend/api/tests/test_monte_carlo_async_websocket.py`
- `backend/api/tests/test_monte_carlo_async_db_fallback.py`
- `backend/api/tests/test_metrics_financial.py`
- `backend/api/tests/test_csv_parsing_financial.py`
- `backend/api/tests/conftest.py`
