# Implemented Metrics (and Missing Metrics)

## Scope

This repository currently computes metrics for **strategy backtesting on price series** and **Monte Carlo simulation summaries**.

It does **not** currently implement predictive-market metrics such as:
- Brier score
- calibration curve / reliability diagram
- log loss for event probabilities

If the project later evolves toward Polymarket/Kalshi-style prediction markets, those metrics would need to be added explicitly.

## Where Metrics Are Computed in the Code

## Core financial metrics

File:
- `backend/api/src/strategies/metrics.py`

Functions:
- `sharpe_ratio(returns, annualization=252)`
- `max_drawdown(equity)`
- `total_return(equity)`
- `trade_summary_from_positions(positions, price)`

## Backtest result assembly

File:
- `backend/api/src/strategies/backtest_result_builder.py`

This builder computes and stores:
- `pnl` from `total_return(equity)`
- `max_drawdown` from `max_drawdown(equity)`
- `sharpe_ratio` from `sharpe_ratio(strategy_returns)`
- `metrics["n_trades"]` from `trade_summary_from_positions(...)`

## Monte Carlo distributions and envelope

File:
- `backend/api/src/services/mc_backtest_service.py`

This module computes:
- metrics distributions for `pnl`, `sharpe`, `drawdown`
- summary statistics (`mean`, `std`, percentiles)
- `equity_envelope` percentiles over time

## Metric Definitions and Formulas

## 1) Total Return (`pnl` in API/backtest responses)

Meaning:
- total return over the backtest period, represented as a fraction (not percent)

Formula used in code:

```text
total_return = equity[-1] / equity[0] - 1
```

Example:
- `0.18` means approximately `+18%`

## 2) Max Drawdown

Meaning:
- worst peak-to-trough decline of the equity curve

Formula used in code:

```text
roll_max = cummax(equity)
drawdown_t = equity_t / roll_max_t - 1
max_drawdown = min(drawdown_t)
```

Interpretation:
- value is typically negative (e.g. `-0.28` ~= `-28%`)

## 3) Sharpe Ratio

Meaning:
- mean return adjusted by return volatility (no risk-free rate in this implementation)

Formula used in code:

```text
sharpe = (mean(strategy_returns) / std(strategy_returns)) * sqrt(annualization)
```

Implementation details:
- uses `std(ddof=0)`
- returns `0.0` when std is zero or values are NaN
- default annualization is `252`

## Frequency Caveat (Important)

The local stock CSV datasets appear to be weekly-resolution data, but annualization remains `252` by default in strategy parameters.

This means:
- Sharpe values are **code-consistent**
- Sharpe values may be **frequency-miscalibrated** if interpreted as daily-frequency Sharpe

## 4) Trade Summary (Supporting Analytics)

`trade_summary_from_positions(...)` is not a single scalar metric. It reconstructs trades from the position series and returns a DataFrame with:
- `entry_date`
- `exit_date`
- `entry_price`
- `exit_price`
- `pnl_pct`

This is useful for future extensions such as:
- win rate
- average holding period
- average trade PnL

## 5) Monte Carlo Metrics Distribution

For each metric (`pnl`, `sharpe`, `drawdown`), the Monte Carlo service computes:
- `mean`
- `std`
- `p5`
- `p25`
- `median`
- `p75`
- `p95`

Meaning:
- summary of the empirical distribution over simulation runs
- useful for robustness analysis (not a guarantee or formal confidence interval)

## 6) Equity Envelope (Monte Carlo)

The Monte Carlo service computes per-timestamp percentiles across equity curves:
- `p5`, `p25`, `median`, `p75`, `p95`

Meaning:
- median path and dispersion over time
- visualization-friendly summary of Monte Carlo outcome spread

## Executed Validation (Real CSV + Real Backend Services)

## What was validated

I validated the metric logic using the repository's real code and local dataset files:

1. Backend startup (`uvicorn`) was executed successfully (startup/shutdown logs observed)
2. Metric computations were executed using backend service modules
3. A manual recomputation was performed for SMA backtest metrics and matched exactly

Why service-level execution was used for metrics validation:
- the execution environment sandbox isolates local network access across processes/sessions
- direct `curl` validation against a background server was unreliable in this environment
- service-level execution still uses the same production metric logic

## Reference Dataset and Configuration

Dataset:
- `backend/api/src/datasets/AAPL.csv`

Reference slice:
- `2015-01-01` to `2017-12-31`

Backtest setup:
- strategy: `sma_crossover`
- parameters: `sma_short=5`, `sma_long=20`
- `price_type=adj_close`
- `initial_capital=10000`

## Backtest Result (SMA 5/20 on AAPL)

Service result:
- `pnl`: `0.18757812015186426` (~ `+18.76%`)
- `drawdown`: `-0.28552519327421844` (~ `-28.55%`)
- `sharpe`: `0.9439872943058683`
- `equity_first`: `10000.0`
- `equity_last`: `11875.781201518643`
- `equity_points`: `156`

Manual recomputation (independent formula reconstruction):
- `pnl`: `0.18757812015186426`
- `drawdown`: `-0.28552519327421844`
- `sharpe`: `0.9439872943058683`

Absolute difference (service vs manual):
- `pnl`: `0.0`
- `drawdown`: `0.0`
- `sharpe`: `0.0`

## Monte Carlo Example Result (Bootstrap, 12 Runs, Seed=42)

Setup:
- method: `bootstrap`
- `runs=12`
- `sample_fraction=1.0`
- same AAPL slice and SMA(5,20) configuration

Summary:
- `successful_runs`: `12/12`
- `equity_envelope.points`: `156`

Distribution `pnl`:
- `mean`: `0.4664201789521514`
- `std`: `0.4453129307703351`
- `p5`: `-0.09107649482888013`
- `median`: `0.43173046550322514`
- `p95`: `1.1799827574807973`

Distribution `sharpe` (mean):
- `1.4531391059239323`

Distribution `drawdown` (mean):
- `-0.2097026388147767`

Raw capture file used during validation:
- `/tmp/hptp_metrics_capture/metrics_computed.json`

## Monte Carlo Performance Comparison: `parallel_workers=1` vs `14`

## Is this comparison relevant?

Frank answer: **yes, conditionally**.

It is relevant because:
- the API now passes `DEFAULT_PARALLEL_WORKERS` explicitly
- the process pool may be used by default depending on the runtime

It is not universally transferable because:
- results depend on machine CPU, process startup behavior, and runtime permissions
- small workloads are sensitive to process pool startup overhead

## Benchmark Method

Dataset and strategy:
- same AAPL slice and SMA(5,20) config as above
- `price_type=adj_close`
- Monte Carlo method: `bootstrap`

Comparison:
- `parallel_workers=1`
- `parallel_workers=14` (user machine max in this case)

Protocol:
- `3` repeats per configuration
- run counts tested: `20`, `60`, `120`, `240`
- benchmark executed from a Python file (not `stdin`) because `multiprocessing` spawn/forkserver is not reliable from `stdin`

Raw benchmark output:
- `/tmp/hptp_metrics_capture/mc_perf_compare_1_vs_14.json`

## Results (Observed)

### `runs=20`
- `workers=1` mean: `0.1067s` (median `0.1051s`)
- `workers=14` mean: `0.1871s` (median `0.0771s`)

Interpretation:
- the `workers=14` mean is skewed by a large first-run startup cost (~0.41s)
- median suggests process pool can be faster once warm
- for small run counts, results are noisy and workload-dependent

### `runs=60`
- `workers=1` mean: `0.3111s`
- `workers=14` mean: `0.1139s`
- speedup (`14` vs `1`, mean): ~`2.73x`

### `runs=120`
- `workers=1` mean: `0.5989s`
- `workers=14` mean: `0.1850s`
- speedup (`14` vs `1`, mean): ~`3.24x`

### `runs=240`
- `workers=1` mean: `1.1568s`
- `workers=14` mean: `0.3060s`
- speedup (`14` vs `1`, mean): ~`3.78x`

## Benchmark Tool (Reusable)

A reusable benchmark CLI was added to the codebase:
- `backend/api/scripts/benchmark_monte_carlo_parallelism.py`

Basic usage:

```bash
cd backend/api
uv run python scripts/benchmark_monte_carlo_parallelism.py
```

Example (explicit comparison):

```bash
cd backend/api
uv run python scripts/benchmark_monte_carlo_parallelism.py \
  --workers 1 14 \
  --runs 20 60 120 240 \
  --repeats 3 \
  --warmup \
  --output /tmp/hptp_metrics_capture/mc_perf_compare_1_vs_14.json
```

Convenience target:

```bash
cd backend/api
make bench-mc-parallel
```

## Practical Conclusion (Frank)

- More process-pool workers can improve Monte Carlo performance significantly for medium/large run counts.
- The gain is not free:
  - process startup overhead
  - increased CPU/RAM usage
  - environment sensitivity (sandbox/container/runtime limits)
- For demos or constrained infra, sequential execution may still be the right default.
- For heavier workloads on a capable machine, CPU-aware defaults are useful and measurable.

## What Would Need to Be Added for Prediction-Market Metrics (Future Scope)

If this project later supports event probability forecasting/markets, add:
- Brier score
- calibration bins / reliability curves / ECE
- log loss
- resolution-aware evaluation by market and horizon
