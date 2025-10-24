import os
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

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
):
    """
    Run backtest using local datasets with Monte Carlo simulation support.
    This endpoint allows running backtests on local datasets without file upload.
    Supports both regular backtests and Monte Carlo simulations.
    """
    symbol_to_file = {
        "aapl": "AAPL.csv",
        "amzn": "AMZN.csv",
        "fb": "FB.csv",
        "googl": "GOOGL.csv",
        "msft": "MSFT.csv",
        "nflx": "NFLX.csv",
        "nvda": "NVDA.csv",
    }
    symbol_lower = symbol.lower()
    if symbol_lower not in symbol_to_file:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol {symbol} not supported. Available symbols: {list(symbol_to_file.keys())}",
        )
    current_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(__file__))
    )
    datasets_path = os.path.join(current_dir, "datasets")
    csv_file_path = os.path.join(datasets_path, symbol_to_file[symbol_lower])
    if not os.path.exists(csv_file_path):
        raise HTTPException(
            status_code=404, detail=f"Dataset file not found for symbol {symbol}"
        )
    df = pd.read_csv(csv_file_path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        try:
            from datetime import datetime
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            raise HTTPException(
                status_code=422, detail="Invalid date format. Use YYYY-MM-DD"
            ) from e
        mask = (df["date"] >= start_dt) & (df["date"] <= end_dt)
        df = df.loc[mask]
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail=f"No data available for {symbol} in the specified date range",
            )
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_data = csv_buffer.getvalue()
    class MockUploadFile:
        def __init__(self, content: bytes, filename: str):
            self.content = content
            self.filename = filename
            self._file = BytesIO(content)
        async def read(self) -> bytes:
            return self.content
        def seek(self, offset: int) -> None:
            self._file.seek(offset)
    mock_file = MockUploadFile(csv_data, f"{symbol_lower}_{start_date}_{end_date}.csv")
    files = [mock_file]
    strat = strategy.strip().lower()
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
        price_type=price_type,
    )
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
    csv: list[UploadFile] = File(default=[]),
    current_user: SimpleUser | None = Depends(get_current_user_simple_optional),
    session: AsyncSession = Depends(get_session),
):
    """
    Run backtest with Monte Carlo simulation support.
    Supports both CSV file upload and local dataset usage.
    When using local datasets, provide symbol, start_date, and end_date parameters.
    """
    files = []
    # Priority: use local datasets if symbol is provided, otherwise use uploaded files
    if symbol and start_date and end_date:
        symbol_to_file = {
            "aapl": "AAPL.csv",
            "amzn": "AMZN.csv",
            "fb": "FB.csv",
            "googl": "GOOGL.csv",
            "msft": "MSFT.csv",
            "nflx": "NFLX.csv",
            "nvda": "NVDA.csv",
        }
        symbol_lower = symbol.lower()
        if symbol_lower not in symbol_to_file:
            raise HTTPException(
                status_code=400,
                detail=f"Symbol {symbol} not supported. Available symbols: {list(symbol_to_file.keys())}",
            )
        import os
        current_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )
        datasets_path = os.path.join(current_dir, "datasets")
        csv_file_path = os.path.join(datasets_path, symbol_to_file[symbol_lower])
        if not os.path.exists(csv_file_path):
            raise HTTPException(
                status_code=404, detail=f"Dataset file not found for symbol {symbol}"
            )
        df = pd.read_csv(csv_file_path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError as e:
                raise HTTPException(
                    status_code=422, detail="Invalid date format. Use YYYY-MM-DD"
                ) from e
            mask = (df["date"] >= start_dt) & (df["date"] <= end_dt)
            df = df.loc[mask]
            if df.empty:
                raise HTTPException(
                    status_code=400,
                    detail=f"No data available for {symbol} in the specified date range",
                )
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        class MockUploadFile:
            def __init__(self, content: bytes, filename: str):
                self.content = content
                self.filename = filename
                self._file = BytesIO(content)
            async def read(self) -> bytes:
                return self.content
            def seek(self, offset: int) -> None:
                self._file.seek(offset)
        mock_file = MockUploadFile(
            csv_data, f"{symbol_lower}_{start_date}_{end_date}.csv"
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
    strat = strategy.strip().lower()
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
    print("Calling run_regular_backtest")
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
    )
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
                if hasattr(result, "pnl"):
                    total_return = float(result.pnl)
                    sharpe_ratio = float(result.sharpe)
                    max_drawdown = float(result.drawdown)
                elif hasattr(result, "results") and result.results:
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
            print(f"Warning: Failed to save backtest to history: {str(e)}")
    return result
async def run_regular_backtest(
    files: list[UploadFile],
    strategy: str,
    strategy_params: dict,
    include_aggregated: bool,
    price_type: str = "close",
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
