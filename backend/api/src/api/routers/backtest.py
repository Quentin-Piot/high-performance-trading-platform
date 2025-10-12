from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from typing import List

from domain.schemas.backtest import BacktestResponse, SingleBacktestResponse, MultiBacktestResponse, SingleBacktestResult, AggregatedMetrics
from services.backtest_service import (
    run_sma_crossover,
    run_rsi,
    CsvBytesPriceSeriesSource,
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

    results = []
    
    # Process each CSV file
    for file in files:
        try:
            source = CsvBytesPriceSeriesSource(await file.read())
            
            # Run backtest based on strategy
            if strat in {"sma_crossover", "sma"}:
                result = run_sma_crossover(source, sma_short, sma_long)
            elif strat in {"rsi", "rsi_reversion"}:
                result = run_rsi(source, period, overbought, oversold)
            
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
