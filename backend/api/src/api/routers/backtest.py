from fastapi import APIRouter, UploadFile, File, Query

from domain.schemas.backtest import BacktestResponse
from services.backtest_service import sma_crossover_backtest


router = APIRouter(prefix="", tags=["backtest"])


@router.post("/backtest", response_model=BacktestResponse)
async def backtest(
    csv: UploadFile = File(..., description="CSV avec colonnes: date, close"),
    sma_short: int = Query(..., gt=0, description="Fenêtre SMA courte"),
    sma_long: int = Query(..., gt=0, description="Fenêtre SMA longue"),
):
    equity, pnl, max_dd, sharpe = sma_crossover_backtest(await csv.read(), sma_short, sma_long)
    return BacktestResponse(
        timestamps=list(map(str, equity.index.tolist())),
        equity_curve=list(map(float, equity.values.tolist())),
        pnl=float(pnl),
        drawdown=float(max_dd),
        sharpe=float(sharpe),
    )
