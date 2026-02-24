import logging
import time
from collections.abc import Sequence

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes._backtest_route_utils import (
    dataframe_to_csv_bytes,
    load_filtered_local_dataset_df,
    validate_strategy_params,
)
from core.simple_auth import (
    SimpleUser,
    get_current_user_simple_optional,
)
from domain.schemas.backtest import (
    AggregatedMetrics,
    BacktestResponse,
    MultiBacktestResponse,
    SingleBacktestResponse,
    SingleBacktestResult,
)
from infrastructure.db import get_session
from infrastructure.repositories.backtest_history_repository import (
    BacktestHistoryRepository,
)
from infrastructure.repositories.user_repository import UserRepository
from services.backtest_service import (
    CsvBytesPriceSeriesSource,
    run_rsi,
    run_sma_crossover,
)

logger = logging.getLogger(__name__)


class LocalDatasetFile:
    """Wraps locally loaded CSV bytes to satisfy the same interface as FastAPI's UploadFile."""

    def __init__(self, content: bytes, filename: str):
        self.content = content
        self.filename = filename

    async def read(self) -> bytes:
        return self.content


router = APIRouter(tags=["backtest"])


@router.get("/backtest", response_model=BacktestResponse)
async def backtest_get(
    symbol: str = Query(
        ..., description="Symbol to use from local datasets (e.g., AAPL, AMZN)"
    ),
    start_date: str = Query(
        ..., description="Start date for dataset filtering (YYYY-MM-DD)"
    ),
    end_date: str = Query(
        ..., description="End date for dataset filtering (YYYY-MM-DD)"
    ),
    strategy: str = Query(
        "sma_crossover",
        description="Strategy name (e.g., sma_crossover, rsi)",
    ),
    price_type: str = Query(
        "close", description="Price type to use: 'close' or 'adj_close'"
    ),
    sma_short: int | None = Query(None, gt=0, description="Short SMA window"),
    sma_long: int | None = Query(None, gt=0, description="Long SMA window"),
    period: int | None = Query(None, gt=0, description="RSI period"),
    overbought: float | None = Query(
        None, ge=0, le=100, description="Overbought threshold (0-100)"
    ),
    oversold: float | None = Query(
        None, ge=0, le=100, description="Oversold threshold (0-100)"
    ),
    include_aggregated: bool = Query(
        False, description="Include aggregated metrics across all files"
    ),
    normalize: bool = Query(
        False, description="Normalize equity curve to start at 1.0"
    ),
):
    """
    Run backtest using local datasets with Monte Carlo simulation support.
    This endpoint allows running backtests on local datasets without file upload.
    Supports both regular backtests and Monte Carlo simulations.
    """
    start_time = time.time()
    df, _data_file = load_filtered_local_dataset_df(symbol, start_date, end_date)
    csv_data = dataframe_to_csv_bytes(df)
    mock_file = LocalDatasetFile(
        csv_data, f"{symbol.lower()}_{start_date}_{end_date}.csv"
    )
    files = [mock_file]
    strat = validate_strategy_params(
        strategy,
        sma_short=sma_short,
        sma_long=sma_long,
        period=period,
        overbought=overbought,
        oversold=oversold,
    )
    result = await run_regular_backtest(
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
        price_type=price_type,
        normalize=normalize,
    )
    elapsed_time = time.time() - start_time
    result.processing_time = f"{elapsed_time:.2f}s"
    return result


@router.post("/backtest", response_model=BacktestResponse)
async def backtest_post(
    symbol: str | None = Query(
        None, description="Symbol to use from local datasets (e.g., AAPL, AMZN)"
    ),
    start_date: str | None = Query(
        None, description="Start date for dataset filtering (YYYY-MM-DD)"
    ),
    end_date: str | None = Query(
        None, description="End date for dataset filtering (YYYY-MM-DD)"
    ),
    strategy: str = Query(
        "sma_crossover",
        description="Strategy name (e.g., sma_crossover, rsi)",
    ),
    price_type: str = Query(
        "close", description="Price type to use: 'close' or 'adj_close'"
    ),
    sma_short: int | None = Query(None, gt=0, description="Short SMA window"),
    sma_long: int | None = Query(None, gt=0, description="Long SMA window"),
    period: int | None = Query(None, gt=0, description="RSI period"),
    overbought: float | None = Query(
        None, ge=0, le=100, description="Overbought threshold (0-100)"
    ),
    oversold: float | None = Query(
        None, ge=0, le=100, description="Oversold threshold (0-100)"
    ),
    include_aggregated: bool = Query(
        False, description="Include aggregated metrics across all files"
    ),
    normalize: bool = Query(
        False, description="Normalize equity curve to start at 1.0"
    ),
    csv: list[UploadFile] = File(default=[]),
    current_user: SimpleUser | None = Depends(get_current_user_simple_optional),
    session: AsyncSession = Depends(get_session),
):
    """
    Run backtest with Monte Carlo simulation support.
    Supports both CSV file upload and local dataset usage.
    When using local datasets, provide symbol, start_date, and end_date parameters.
    """
    start_time = time.time()
    files = []
    if symbol and start_date and end_date:
        df, _data_file = load_filtered_local_dataset_df(symbol, start_date, end_date)
        csv_data = dataframe_to_csv_bytes(df)
        mock_file = LocalDatasetFile(
            csv_data, f"{symbol.lower()}_{start_date}_{end_date}.csv"
        )
        files = [mock_file]
    elif csv and len(csv) > 0:
        files = csv
    else:
        raise HTTPException(
            status_code=422,
            detail="Either csv file(s) or symbol with start_date and end_date must be provided",
        )
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum of 10 CSV files allowed")
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="At least one CSV file is required")
    strat = validate_strategy_params(
        strategy,
        sma_short=sma_short,
        sma_long=sma_long,
        period=period,
        overbought=overbought,
        oversold=oversold,
    )
    result = await run_regular_backtest(
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
        price_type=price_type,
        normalize=normalize,
    )
    elapsed_time = time.time() - start_time
    result.processing_time = f"{elapsed_time:.2f}s"
    if current_user:
        try:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(current_user.id)
            if user:
                history_repo = BacktestHistoryRepository(session)
                datasets_used = []
                if symbol:
                    datasets_used = [symbol.upper()]
                elif csv:
                    datasets_used = [
                        f.filename or f"file_{i + 1}.csv" for i, f in enumerate(csv)
                    ]
                total_return = None
                sharpe_ratio = None
                max_drawdown = None
                if isinstance(result, SingleBacktestResponse):
                    total_return = float(result.pnl)
                    sharpe_ratio = float(result.sharpe)
                    max_drawdown = float(result.drawdown)
                elif isinstance(result, MultiBacktestResponse) and result.results:
                    first_result = result.results[0]
                    total_return = float(first_result.pnl)
                    sharpe_ratio = float(first_result.sharpe)
                    max_drawdown = float(first_result.drawdown)
                history_entry = await history_repo.create_history_entry(
                    user_id=user.id,
                    strategy=strategy,
                    strategy_params={
                        "sma_short": sma_short,
                        "sma_long": sma_long,
                        "period": period,
                        "overbought": overbought,
                        "oversold": oversold,
                    },
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=10000.0,
                    monte_carlo_runs=1,
                    datasets_used=datasets_used,
                    price_type=price_type,
                )
                if total_return is not None:
                    await history_repo.update_results(
                        history_id=history_entry.id,
                        total_return=total_return,
                        sharpe_ratio=sharpe_ratio,
                        max_drawdown=max_drawdown,
                        status="completed",
                    )
        except Exception as e:
            logger.warning(f"Failed to save backtest to history: {e}")
    return result


async def run_regular_backtest(
    files: Sequence[UploadFile | LocalDatasetFile],
    strategy: str,
    strategy_params: dict,
    include_aggregated: bool,
    price_type: str = "close",
    normalize: bool = False,
) -> BacktestResponse:
    results = []
    for file in files:
        try:
            source = CsvBytesPriceSeriesSource(await file.read(), price_type)
            if strategy in {"sma_crossover", "sma"}:
                result = run_sma_crossover(
                    source, strategy_params["sma_short"], strategy_params["sma_long"]
                )
            elif strategy in {"rsi", "rsi_reversion"}:
                result = run_rsi(
                    source,
                    strategy_params["period"],
                    strategy_params["overbought"],
                    strategy_params["oversold"],
                )
            else:
                raise ValueError(f"Unknown strategy: {strategy}")

            equity_curve = list(map(float, result.equity.values.tolist()))
            if normalize and equity_curve and equity_curve[0] != 0:
                first_value = equity_curve[0]
                equity_curve = [value / first_value for value in equity_curve]

            single_result = SingleBacktestResult(
                filename=file.filename or f"file_{len(results) + 1}.csv",
                timestamps=list(map(str, result.equity.index.tolist())),
                equity_curve=equity_curve,
                pnl=float(result.pnl),
                drawdown=float(result.drawdown),
                sharpe=float(result.sharpe),
            )
            results.append(single_result)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error processing file '{file.filename}': {str(e)}",
            ) from e
    if len(results) == 1 and not include_aggregated:
        single = results[0]
        return SingleBacktestResponse(
            timestamps=single.timestamps,
            equity_curve=single.equity_curve,
            pnl=single.pnl,
            drawdown=single.drawdown,
            sharpe=single.sharpe,
        )
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
