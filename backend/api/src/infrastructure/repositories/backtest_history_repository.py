"""
Repository for backtest history management.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.models import BacktestHistory


class BacktestHistoryRepository:
    """Repository for backtest history operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_history_entry(
        self,
        user_id: int,
        strategy: str,
        strategy_params: dict[str, Any],
        start_date: str | None = None,
        end_date: str | None = None,
        initial_capital: float = 10000.0,
        monte_carlo_runs: int = 1,
        monte_carlo_method: str | None = None,
        sample_fraction: float | None = None,
        gaussian_scale: float | None = None,
        datasets_used: list[str] | None = None,
        price_type: str = "close"
    ) -> BacktestHistory:
        """Create a new backtest history entry."""
        history = BacktestHistory(
            user_id=user_id,
            strategy=strategy,
            strategy_params=strategy_params,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            monte_carlo_runs=monte_carlo_runs,
            monte_carlo_method=monte_carlo_method,
            sample_fraction=sample_fraction,
            gaussian_scale=gaussian_scale,
            datasets_used=datasets_used or [],
            price_type=price_type,
            status="running"
        )

        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        return history

    async def update_results(
        self,
        history_id: int,
        total_return: float | None = None,
        sharpe_ratio: float | None = None,
        max_drawdown: float | None = None,
        win_rate: float | None = None,
        total_trades: int | None = None,
        execution_time_seconds: float | None = None,
        status: str = "completed",
        error_message: str | None = None
    ) -> BacktestHistory | None:
        """Update backtest results."""
        result = await self.session.execute(
            select(BacktestHistory).where(BacktestHistory.id == history_id)
        )
        history = result.scalar_one_or_none()

        if not history:
            return None

        if total_return is not None:
            history.total_return = total_return
        if sharpe_ratio is not None:
            history.sharpe_ratio = sharpe_ratio
        if max_drawdown is not None:
            history.max_drawdown = max_drawdown
        if win_rate is not None:
            history.win_rate = win_rate
        if total_trades is not None:
            history.total_trades = total_trades
        if execution_time_seconds is not None:
            history.execution_time_seconds = execution_time_seconds

        history.status = status
        if error_message:
            history.error_message = error_message

        if status == "completed":
            history.completed_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(history)
        return history

    async def get_user_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        strategy_filter: str | None = None
    ) -> list[BacktestHistory]:
        """Get user's backtest history with optional filtering."""
        query = select(BacktestHistory).where(BacktestHistory.user_id == user_id)

        if strategy_filter:
            query = query.where(BacktestHistory.strategy == strategy_filter)

        query = query.order_by(desc(BacktestHistory.created_at)).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, history_id: int, user_id: int | None = None) -> BacktestHistory | None:
        """Get backtest history by ID, optionally filtered by user."""
        query = select(BacktestHistory).where(BacktestHistory.id == history_id)

        if user_id is not None:
            query = query.where(BacktestHistory.user_id == user_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_stats(self, user_id: int) -> dict[str, Any]:
        """Get user's backtest statistics."""
        # Get all completed backtests for the user
        result = await self.session.execute(
            select(BacktestHistory).where(
                and_(
                    BacktestHistory.user_id == user_id,
                    BacktestHistory.status == "completed"
                )
            )
        )
        histories = list(result.scalars().all())

        if not histories:
            return {
                "total_backtests": 0,
                "strategies_used": [],
                "avg_return": None,
                "best_return": None,
                "worst_return": None,
                "avg_sharpe": None,
                "total_monte_carlo_runs": 0
            }

        # Calculate statistics
        returns = [h.total_return for h in histories if h.total_return is not None]
        sharpes = [h.sharpe_ratio for h in histories if h.sharpe_ratio is not None]
        strategies = list(set(h.strategy for h in histories))
        total_mc_runs = sum(h.monte_carlo_runs for h in histories)

        return {
            "total_backtests": len(histories),
            "strategies_used": strategies,
            "avg_return": sum(returns) / len(returns) if returns else None,
            "best_return": max(returns) if returns else None,
            "worst_return": min(returns) if returns else None,
            "avg_sharpe": sum(sharpes) / len(sharpes) if sharpes else None,
            "total_monte_carlo_runs": total_mc_runs
        }

    async def delete_history(self, history_id: int, user_id: int) -> bool:
        """Delete a backtest history entry (user can only delete their own)."""
        result = await self.session.execute(
            select(BacktestHistory).where(
                and_(
                    BacktestHistory.id == history_id,
                    BacktestHistory.user_id == user_id
                )
            )
        )
        history = result.scalar_one_or_none()

        if not history:
            return False

        await self.session.delete(history)
        await self.session.commit()
        return True
