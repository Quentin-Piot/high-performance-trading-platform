from __future__ import annotations

import argparse
import json
import statistics as stats
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

# Make `backend/api/src` importable when running from `backend/api/`.
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from services.mc_backtest_service import run_monte_carlo_on_df  # noqa: E402


def _load_dataset_csv_bytes(symbol: str, start_date: str, end_date: str) -> tuple[bytes, str, int]:
    dataset_path = ROOT_DIR / "src" / "datasets" / f"{symbol.upper()}.csv"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    df = pd.read_csv(dataset_path)
    df.columns = [c.strip().lower() for c in df.columns]
    if "date" not in df.columns:
        raise ValueError(f"Dataset {dataset_path} does not contain a 'Date/date' column")
    df["date"] = pd.to_datetime(df["date"])
    filtered = df[
        (df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))
    ].copy()
    if filtered.empty:
        raise ValueError(
            f"No rows selected for {symbol} in range {start_date}..{end_date}"
        )
    return filtered.to_csv(index=False).encode(), str(dataset_path), int(len(filtered))


def _run_case(
    *,
    csv_bytes: bytes,
    runs: int,
    parallel_workers: int,
    repeats: int,
    seed_base: int,
    strategy_name: str,
    strategy_params: dict[str, Any],
    method: str,
    method_params: dict[str, Any],
    price_type: str,
    include_equity_envelope: bool,
    warmup: bool,
) -> dict[str, Any]:
    if warmup:
        run_monte_carlo_on_df(
            csv_data=csv_bytes,
            filename="benchmark.csv",
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            runs=min(runs, 5),
            method=method,
            method_params=method_params,
            parallel_workers=parallel_workers,
            seed=seed_base - 1,
            include_equity_envelope=False,
            price_type=price_type,
        )

    times: list[float] = []
    for rep in range(repeats):
        t0 = time.perf_counter()
        summary = run_monte_carlo_on_df(
            csv_data=csv_bytes,
            filename="benchmark.csv",
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            runs=runs,
            method=method,
            method_params=method_params,
            parallel_workers=parallel_workers,
            seed=seed_base + rep,
            include_equity_envelope=include_equity_envelope,
            price_type=price_type,
        )
        if summary.successful_runs <= 0:
            raise RuntimeError("Benchmark run completed with zero successful runs")
        times.append(time.perf_counter() - t0)

    return {
        "runs": runs,
        "parallel_workers": parallel_workers,
        "repeats": repeats,
        "ok": True,
        "error": None,
        "times_s": times,
        "mean_s": stats.mean(times),
        "median_s": stats.median(times),
        "min_s": min(times),
        "max_s": max(times),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark Monte Carlo runtime for different ProcessPool worker counts."
    )
    parser.add_argument("--symbol", default="AAPL", help="Local dataset symbol (default: AAPL)")
    parser.add_argument("--start-date", default="2015-01-01")
    parser.add_argument("--end-date", default="2017-12-31")
    parser.add_argument(
        "--runs",
        nargs="+",
        type=int,
        default=[20, 60, 120, 240],
        help="List of Monte Carlo run counts to benchmark",
    )
    parser.add_argument(
        "--workers",
        nargs="+",
        type=int,
        default=[1, 14],
        help="List of parallel_workers values to compare",
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed-base", type=int, default=42)
    parser.add_argument("--strategy", default="sma_crossover")
    parser.add_argument("--sma-short", type=int, default=5)
    parser.add_argument("--sma-long", type=int, default=20)
    parser.add_argument("--initial-capital", type=float, default=10000.0)
    parser.add_argument("--method", choices=["bootstrap", "gaussian"], default="bootstrap")
    parser.add_argument("--sample-fraction", type=float, default=1.0)
    parser.add_argument("--gaussian-scale", type=float, default=1.0)
    parser.add_argument("--price-type", choices=["close", "adj_close"], default="adj_close")
    parser.add_argument(
        "--no-equity-envelope",
        action="store_true",
        help="Disable equity envelope during benchmark to isolate distribution timing",
    )
    parser.add_argument(
        "--warmup",
        action="store_true",
        help="Run a small warmup call per worker-count to reduce pool startup bias",
    )
    parser.add_argument(
        "--output",
        default="/tmp/hptp_metrics_capture/mc_perf_compare.json",
        help="Output JSON file path",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    csv_bytes, dataset_path, rows_selected = _load_dataset_csv_bytes(
        args.symbol, args.start_date, args.end_date
    )

    strategy_params: dict[str, Any] = {
        "initial_capital": args.initial_capital,
    }
    if args.strategy in {"sma_crossover", "sma"}:
        strategy_params.update({"sma_short": args.sma_short, "sma_long": args.sma_long})
    else:
        raise ValueError(
            "This benchmark script currently supports only SMA strategies for reproducibility"
        )

    method_params: dict[str, Any] = {
        "sample_fraction": args.sample_fraction,
        "gaussian_scale": args.gaussian_scale,
    }

    results: list[dict[str, Any]] = []
    for runs in args.runs:
        for workers in args.workers:
            try:
                item = _run_case(
                    csv_bytes=csv_bytes,
                    runs=runs,
                    parallel_workers=workers,
                    repeats=args.repeats,
                    seed_base=args.seed_base,
                    strategy_name=args.strategy,
                    strategy_params=strategy_params,
                    method=args.method,
                    method_params=method_params,
                    price_type=args.price_type,
                    include_equity_envelope=not args.no_equity_envelope,
                    warmup=args.warmup,
                )
            except Exception as e:
                item = {
                    "runs": runs,
                    "parallel_workers": workers,
                    "repeats": args.repeats,
                    "ok": False,
                    "error": repr(e),
                }
            results.append(item)

    baseline_workers = args.workers[0] if args.workers else 1
    speedups: list[dict[str, Any]] = []
    for runs in args.runs:
        baseline = next(
            (
                r
                for r in results
                if r["runs"] == runs
                and r["parallel_workers"] == baseline_workers
                and r.get("ok")
            ),
            None,
        )
        if not baseline:
            continue
        for workers in args.workers[1:]:
            other = next(
                (
                    r
                    for r in results
                    if r["runs"] == runs
                    and r["parallel_workers"] == workers
                    and r.get("ok")
                ),
                None,
            )
            if not other:
                continue
            speedups.append(
                {
                    "runs": runs,
                    "baseline_workers": baseline_workers,
                    "compare_workers": workers,
                    "speedup_mean": baseline["mean_s"] / other["mean_s"]
                    if other["mean_s"] > 0
                    else None,
                    "delta_s_mean": baseline["mean_s"] - other["mean_s"],
                }
            )

    payload = {
        "dataset": {
            "symbol": args.symbol.upper(),
            "path": dataset_path,
            "period": [args.start_date, args.end_date],
            "rows_selected": rows_selected,
            "price_type": args.price_type,
        },
        "strategy": {
            "name": args.strategy,
            "params": strategy_params,
        },
        "monte_carlo": {
            "method": args.method,
            "method_params": method_params,
            "include_equity_envelope": not args.no_equity_envelope,
        },
        "benchmark": {
            "runs_cases": args.runs,
            "workers_compared": args.workers,
            "repeats": args.repeats,
            "seed_base": args.seed_base,
            "warmup": args.warmup,
        },
        "results": results,
        "speedups": speedups,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    print(f"saved_to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
