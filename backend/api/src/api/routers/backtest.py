from fastapi import APIRouter, UploadFile, File, Query, HTTPException

from domain.schemas.backtest import BacktestResponse
from services.backtest_service import run_sma_crossover, CsvBytesPriceSeriesSource

router = APIRouter(tags=["backtest"])  # no internal prefix; main adds versioned prefix


@router.post("/backtest", response_model=BacktestResponse)
async def backtest(
    csv: UploadFile = File(..., description="CSV avec colonnes: date, close"),
    sma_short: int = Query(..., gt=0, description="Fenêtre SMA courte"),
    sma_long: int = Query(..., gt=0, description="Fenêtre SMA longue"),
    strategy: str = Query("sma_crossover", description="Nom de la stratégie (ex: sma_crossover)"),
):
    if strategy != "sma_crossover":
        raise HTTPException(status_code=400, detail=f"Stratégie non prise en charge: {strategy}")
    source = CsvBytesPriceSeriesSource(await csv.read())
    result = run_sma_crossover(source, sma_short, sma_long)
    return BacktestResponse(
        timestamps=list(map(str, result.equity.index.tolist())),
        equity_curve=list(map(float, result.equity.values.tolist())),
        pnl=float(result.pnl),
        drawdown=float(result.drawdown),
        sharpe=float(result.sharpe),
    )
