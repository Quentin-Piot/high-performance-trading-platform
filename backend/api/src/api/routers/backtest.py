from fastapi import APIRouter, UploadFile, File, Query, HTTPException

from domain.schemas.backtest import BacktestResponse
from services.backtest_service import (
    run_sma_crossover,
    run_rsi,
    CsvBytesPriceSeriesSource,
)

router = APIRouter(tags=["backtest"])  # no internal prefix; main adds versioned prefix


@router.post("/backtest", response_model=BacktestResponse)
async def backtest(
    csv: UploadFile = File(..., description="CSV avec colonnes: date, close"),
    strategy: str = Query(
        "sma_crossover",
        description="Nom de la stratégie (ex: sma_crossover, rsi)",
    ),
    # Paramètres SMA (optionnels, requis seulement si stratégie = sma_crossover/sma)
    sma_short: int | None = Query(None, gt=0, description="Fenêtre SMA courte"),
    sma_long: int | None = Query(None, gt=0, description="Fenêtre SMA longue"),
    # Paramètres RSI (optionnels, requis seulement si stratégie = rsi/rsi_reversion)
    period: int | None = Query(None, gt=0, description="Période RSI"),
    overbought: float | None = Query(
        None, ge=0, le=100, description="Seuil surachat (0-100)"
    ),
    oversold: float | None = Query(
        None, ge=0, le=100, description="Seuil survente (0-100)"
    ),
):
    source = CsvBytesPriceSeriesSource(await csv.read())

    # Normaliser les alias de stratégie
    strat = strategy.strip().lower()
    if strat in {"sma_crossover", "sma"}:
        if sma_short is None or sma_long is None:
            raise HTTPException(
                status_code=422,
                detail="Paramètres requis manquants pour SMA: sma_short et sma_long",
            )
        result = run_sma_crossover(source, sma_short, sma_long)
    elif strat in {"rsi", "rsi_reversion"}:
        if period is None or overbought is None or oversold is None:
            raise HTTPException(
                status_code=422,
                detail="Paramètres requis manquants pour RSI: period, overbought, oversold",
            )
        result = run_rsi(source, period, overbought, oversold)
    else:
        raise HTTPException(status_code=400, detail=f"Stratégie non prise en charge: {strategy}")

    return BacktestResponse(
        timestamps=list(map(str, result.equity.index.tolist())),
        equity_curve=list(map(float, result.equity.values.tolist())),
        pnl=float(result.pnl),
        drawdown=float(result.drawdown),
        sharpe=float(result.sharpe),
    )
