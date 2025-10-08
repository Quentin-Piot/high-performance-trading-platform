from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from typing import Optional
from domain.schemas.backtest import BacktestResponse
from services.backtest_service import (
    run_sma_crossover,
    run_rsi,
    CsvBytesPriceSeriesSource
)

router = APIRouter(prefix="/api/v1", tags=["backtest"])


@router.post("/backtest", response_model=BacktestResponse)
async def backtest(
    csv: UploadFile = File(..., description="CSV with columns: date, close"),
    strategy: str = Query(..., description="Name of the strategy, e.g., sma_crossover or rsi"),
    # SMA params
    sma_short: Optional[int] = Query(None, gt=0, description="Short SMA window"),
    sma_long: Optional[int] = Query(None, gt=0, description="Long SMA window"),
    # RSI params
    period: Optional[int] = Query(None, gt=0, description="RSI period"),
    overbought: Optional[float] = Query(None, description="RSI overbought threshold"),
    oversold: Optional[float] = Query(None, description="RSI oversold threshold"),
):
    data = await csv.read()
    source = CsvBytesPriceSeriesSource(data)

    if strategy == "sma_crossover":
        if sma_short is None or sma_long is None:
            raise HTTPException(status_code=422, detail="Missing SMA parameters: sma_short and sma_long required")
        result = run_sma_crossover(source, sma_short, sma_long)

    elif strategy == "rsi":
        if period is None or overbought is None or oversold is None:
            raise HTTPException(status_code=422, detail="Missing RSI parameters: period, overbought, oversold required")
        result = run_rsi(source, period, overbought, oversold)

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported strategy: {strategy}")

    return BacktestResponse(
        timestamps=list(map(str, result.equity.index.tolist())),
        equity_curve=list(map(float, result.equity.values.tolist())),
        pnl=float(result.pnl),
        drawdown=float(result.drawdown),
        sharpe=float(result.sharpe),
    )
