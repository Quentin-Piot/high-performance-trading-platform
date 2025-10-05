from fastapi import APIRouter, UploadFile, File, Query

from domain.schemas.backtest import BacktestResponse
from services.backtest_service import sma_crossover_backtest, run_sma_crossover, CsvBytesPriceSeriesSource


router = APIRouter(prefix="", tags=["backtest"])


@router.post("/backtest", response_model=BacktestResponse)
async def backtest(
    csv: UploadFile = File(..., description="CSV avec colonnes: date, close"),
    sma_short: int = Query(..., gt=0, description="Fenêtre SMA courte"),
    sma_long: int = Query(..., gt=0, description="Fenêtre SMA longue"),
):
    source = CsvBytesPriceSeriesSource(await csv.read())
    result = run_sma_crossover(source, sma_short, sma_long)
    return BacktestResponse(
        timestamps=list(map(str, result.equity.index.tolist())),
        equity_curve=list(map(float, result.equity.values.tolist())),
        pnl=float(result.pnl),
        drawdown=float(result.drawdown),
        sharpe=float(result.sharpe),
    )
