from fastapi import APIRouter, UploadFile, File, Query, HTTPException
import asyncio
from datetime import datetime
from typing import List
import os

from domain.schemas.backtest import (
    BacktestResponse, 
    SingleBacktestResponse, 
    MultiBacktestResponse, 
    MonteCarloResponse,
    SingleBacktestResult, 
    MonteCarloBacktestResult,
    AggregatedMetrics,
    MetricsDistribution,
    EquityEnvelope
)
from services.backtest_service import (
    run_sma_crossover,
    run_rsi,
    CsvBytesPriceSeriesSource,
)
from services.mc_backtest_service import (
    run_monte_carlo_on_df,
    ProgressPublisher,
    MAX_MONTE_CARLO_RUNS
)

router = APIRouter(tags=["backtest"])  # no internal prefix; main adds versioned prefix


@router.post("/backtest", response_model=BacktestResponse)
async def backtest(
    csv: UploadFile | List[UploadFile] = File(..., description="CSV file(s) with columns: date, close (max 10 files)"),
    strategy: str = Query(
        "sma_crossover",
        description="Strategy name (e.g., sma_crossover, rsi)",
    ),
    # SMA parameters (optional, required only if strategy = sma_crossover/sma)
    sma_short: int | None = Query(None, gt=0, description="Short SMA window"),
    sma_long: int | None = Query(None, gt=0, description="Long SMA window"),
    # RSI parameters (optional, required only if strategy = rsi/rsi_reversion)
    period: int | None = Query(None, gt=0, description="RSI period"),
    overbought: float | None = Query(
        None, ge=0, le=100, description="Overbought threshold (0-100)"
    ),
    oversold: float | None = Query(
        None, ge=0, le=100, description="Oversold threshold (0-100)"
    ),
    include_aggregated: bool = Query(False, description="Include aggregated metrics across all files"),
    # Monte Carlo parameters
    monte_carlo_runs: int = Query(1, ge=1, le=MAX_MONTE_CARLO_RUNS, description="Number of Monte Carlo runs"),
    method: str = Query("bootstrap", description="Perturbation method: bootstrap or gaussian"),
    sample_fraction: float = Query(1.0, ge=0.1, le=2.0, description="Bootstrap sample fraction"),
    gaussian_scale: float = Query(1.0, ge=0.1, le=5.0, description="Gaussian noise scale factor"),
    parallel_workers: int = Query(os.cpu_count() or 1, ge=1, le=16, description="Number of parallel workers"),
    include_equity_percentiles: bool = Query(True, description="Include equity curve percentiles"),
    stream: bool = Query(False, description="Stream progress updates (future feature)"),
    # Optional job_id to report progress to JobRepository for WS streaming
    job_id: str | None = Query(None, description="Monte Carlo job ID for progress tracking"),
):
    # Handle single file or multiple files
    files = csv if isinstance(csv, list) else [csv]
    
    # Validate file count
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum of 10 CSV files allowed"
        )
    
    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one CSV file is required"
        )

    # Normalize strategy aliases
    strat = strategy.strip().lower()
    
    # Validate strategy parameters
    if strat in {"sma_crossover", "sma"}:
        if sma_short is None or sma_long is None:
            raise HTTPException(
                status_code=422,
                detail="Missing required parameters for SMA: sma_short and sma_long",
            )
    elif strat in {"rsi", "rsi_reversion"}:
        if period is None or overbought is None or oversold is None:
            raise HTTPException(
                status_code=422,
                detail="Missing required parameters for RSI: period, overbought, oversold",
            )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported strategy: {strategy}")

    # Validate Monte Carlo method
    if method not in {"bootstrap", "gaussian"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported method: {method}. Use 'bootstrap' or 'gaussian'"
        )

    # Determine if this is a Monte Carlo run
    is_monte_carlo = monte_carlo_runs > 1
    
    if is_monte_carlo:
        # Monte Carlo mode
        return await run_monte_carlo_backtest(
            files=files,
            strategy=strat,
            strategy_params={
                "sma_short": sma_short,
                "sma_long": sma_long,
                "period": period,
                "overbought": overbought,
                "oversold": oversold,
            },
            monte_carlo_runs=monte_carlo_runs,
            method=method,
            method_params={
                "sample_fraction": sample_fraction,
                "gaussian_scale": gaussian_scale,
            },
            parallel_workers=parallel_workers,
            include_equity_percentiles=include_equity_percentiles,
            include_aggregated=include_aggregated,
            job_id=job_id,
        )
    else:
        # Regular backtest mode (existing logic)
        return await run_regular_backtest(
            files=files,
            strategy=strat,
            strategy_params={
                "sma_short": sma_short,
                "sma_long": sma_long,
                "period": period,
                "overbought": overbought,
                "oversold": oversold,
            },
            include_aggregated=include_aggregated,
        )


async def run_regular_backtest(
    files: List[UploadFile],
    strategy: str,
    strategy_params: dict,
    include_aggregated: bool,
) -> BacktestResponse:
    results = []
    
    # Process each CSV file
    for file in files:
        try:
            source = CsvBytesPriceSeriesSource(await file.read())
            
            # Run backtest based on strategy
            if strategy in {"sma_crossover", "sma"}:
                result = run_sma_crossover(source, strategy_params["sma_short"], strategy_params["sma_long"])
            elif strategy in {"rsi", "rsi_reversion"}:
                result = run_rsi(source, strategy_params["period"], strategy_params["overbought"], strategy_params["oversold"])
            
            # Create single result
            single_result = SingleBacktestResult(
                filename=file.filename or f"file_{len(results) + 1}.csv",
                timestamps=list(map(str, result.equity.index.tolist())),
                equity_curve=list(map(float, result.equity.values.tolist())),
                pnl=float(result.pnl),
                drawdown=float(result.drawdown),
                sharpe=float(result.sharpe),
            )
            results.append(single_result)
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error processing file '{file.filename}': {str(e)}"
            )
    
    # Handle single file case for backward compatibility
    if len(results) == 1 and not include_aggregated:
        single = results[0]
        return SingleBacktestResponse(
            timestamps=single.timestamps,
            equity_curve=single.equity_curve,
            pnl=single.pnl,
            drawdown=single.drawdown,
            sharpe=single.sharpe,
        )
    
    # Handle multiple files or aggregated metrics requested
    aggregated_metrics = None
    if include_aggregated and results:
        avg_pnl = sum(r.pnl for r in results) / len(results)
        avg_sharpe = sum(r.sharpe for r in results) / len(results)
        avg_drawdown = sum(r.drawdown for r in results) / len(results)
        
        aggregated_metrics = AggregatedMetrics(
            average_pnl=avg_pnl,
            average_sharpe=avg_sharpe,
            average_drawdown=avg_drawdown,
            total_files_processed=len(results),
        )
    
    return MultiBacktestResponse(
        results=results,
        aggregated_metrics=aggregated_metrics,
    )


async def run_monte_carlo_backtest(
    files: List[UploadFile],
    strategy: str,
    strategy_params: dict,
    monte_carlo_runs: int,
    method: str,
    method_params: dict,
    parallel_workers: int,
    include_equity_percentiles: bool,
    include_aggregated: bool,
    job_id: str | None,
) -> MonteCarloResponse:
    """Run Monte Carlo backtesting on multiple CSV files."""
    results = []
    total_units = max(1, monte_carlo_runs * max(1, len(files)))
    completed_units = 0
    started_sent = False
    
    # Lazy import to avoid circulars
    from infrastructure.db import SessionLocal
    from infrastructure.repositories.jobs import JobRepository
    
    # Process each CSV file
    for file in files:
        try:
            # Read CSV data
            csv_bytes = await file.read()
            source = CsvBytesPriceSeriesSource(csv_bytes)
            df = source.to_dataframe()
            
            # Progress callback: updates JobRepository so WS can stream progress
            def progress_callback(processed: int, total: int):
                if not job_id:
                    return
                # Compute global progress across all files
                try:
                    local_progress_units = completed_units + processed
                    progress_ratio = float(local_progress_units) / float(total_units)
                except Exception:
                    progress_ratio = 0.0

                # Build a human-friendly message
                msg = f"Processing {file.filename or 'file'}: {processed}/{total} runs"

                async def _report():
                    async with SessionLocal() as session:
                        repo = JobRepository(session)
                        started_at = None
                        nonlocal started_sent
                        if not started_sent:
                            started_at = datetime.utcnow()
                            started_sent = True
                            # Also mark status running on first progress
                            try:
                                await repo.update_job_status(job_id, "running")
                            except Exception:
                                pass
                        await repo.update_job_progress(job_id, progress_ratio, msg, started_at=started_at)

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_report())
                except RuntimeError:
                    # No running loop (unlikely in FastAPI), fallback to synchronous run
                    asyncio.run(_report())
            
            # Run Monte Carlo simulation
            mc_result = run_monte_carlo_on_df(
                csv_data=csv_bytes,
                filename=file.filename or f"file_{len(results) + 1}.csv",
                strategy_name=strategy,
                strategy_params=strategy_params,
                runs=monte_carlo_runs,
                method=method,
                method_params=method_params,
                parallel_workers=parallel_workers,
                include_equity_envelope=include_equity_percentiles,
                progress_callback=progress_callback,
            )

            # After finishing this file, advance the global completed units
            try:
                completed_units += monte_carlo_runs
                if job_id:
                    # Send a final per-file progress tick to ensure smooth WS updates
                    final_msg = f"Completed {file.filename or 'file'} ({monte_carlo_runs}/{monte_carlo_runs} runs)"
                    async def _final_report():
                        async with SessionLocal() as session:
                            repo = JobRepository(session)
                            await repo.update_job_progress(job_id, min(1.0, float(completed_units)/float(total_units)), final_msg)
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(_final_report())
                    except RuntimeError:
                        asyncio.run(_final_report())
            except Exception:
                pass
            
            # Convert to response format - no conversion needed, types are already compatible
            monte_carlo_result = MonteCarloBacktestResult(
                filename=file.filename or f"file_{len(results) + 1}.csv",
                method=method,
                runs=monte_carlo_runs,
                successful_runs=mc_result.successful_runs,
                metrics_distribution=mc_result.metrics_distribution,
                equity_envelope=mc_result.equity_envelope
            )
            results.append(monte_carlo_result)
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error processing Monte Carlo for file '{file.filename}': {str(e)}"
            )
    
    # Calculate aggregated metrics if requested
    aggregated_metrics = None
    if include_aggregated and results:
        avg_pnl = sum(r.metrics_distribution["pnl"].mean for r in results) / len(results)
        avg_sharpe = sum(r.metrics_distribution["sharpe"].mean for r in results) / len(results)
        avg_drawdown = sum(r.metrics_distribution["drawdown"].mean for r in results) / len(results)
        
        aggregated_metrics = AggregatedMetrics(
            average_pnl=avg_pnl,
            average_sharpe=avg_sharpe,
            average_drawdown=avg_drawdown,
            total_files_processed=len(results),
        )
    # Mark job completed in repository
    if job_id:
        async def _mark_completed():
            async with SessionLocal() as session:
                repo = JobRepository(session)
                try:
                    await repo.update_job_status(job_id, "completed", progress=1.0, completed_at=datetime.utcnow())
                except Exception:
                    # If status update fails, still try to set progress to 1
                    await repo.update_job_progress(job_id, 1.0, "Monte Carlo completed", completed_at=datetime.utcnow())
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_mark_completed())
        except RuntimeError:
            asyncio.run(_mark_completed())

    return MonteCarloResponse(
        results=results,
        aggregated_metrics=aggregated_metrics,
    )
