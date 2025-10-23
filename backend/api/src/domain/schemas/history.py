"""
Pydantic schemas for backtest history.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BacktestHistoryCreate(BaseModel):
    """Schema for creating a backtest history entry."""

    strategy: str = Field(..., description="Strategy name")
    strategy_params: dict[str, Any] = Field(..., description="Strategy parameters")
    start_date: str | None = Field(None, description="Backtest start date")
    end_date: str | None = Field(None, description="Backtest end date")
    initial_capital: float = Field(10000.0, description="Initial capital")
    monte_carlo_runs: int = Field(1, description="Number of Monte Carlo runs")
    monte_carlo_method: str | None = Field(None, description="Monte Carlo method")
    sample_fraction: float | None = Field(
        None, description="Sample fraction for bootstrap"
    )
    gaussian_scale: float | None = Field(None, description="Gaussian scale for noise")
    datasets_used: list[str] | None = Field(
        None, description="List of dataset IDs used"
    )
    price_type: str = Field("close", description="Price type used")


class BacktestHistoryUpdate(BaseModel):
    """Schema for updating backtest results."""

    total_return: float | None = Field(None, description="Total return percentage")
    sharpe_ratio: float | None = Field(None, description="Sharpe ratio")
    max_drawdown: float | None = Field(None, description="Maximum drawdown percentage")
    win_rate: float | None = Field(None, description="Win rate percentage")
    total_trades: int | None = Field(None, description="Total number of trades")
    execution_time_seconds: float | None = Field(
        None, description="Execution time in seconds"
    )
    status: str = Field("completed", description="Backtest status")
    error_message: str | None = Field(None, description="Error message if failed")


class BacktestHistoryResponse(BaseModel):
    """Schema for backtest history response."""

    id: int
    user_id: int
    strategy: str
    strategy_params: dict[str, Any]
    start_date: str | None
    end_date: str | None
    initial_capital: float
    monte_carlo_runs: int
    monte_carlo_method: str | None
    sample_fraction: float | None
    gaussian_scale: float | None
    datasets_used: list[str] | None
    price_type: str

    # Results
    total_return: float | None
    sharpe_ratio: float | None
    max_drawdown: float | None
    win_rate: float | None
    total_trades: int | None

    # Metadata
    execution_time_seconds: float | None
    status: str
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class BacktestHistoryList(BaseModel):
    """Schema for paginated backtest history list."""

    items: list[BacktestHistoryResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class UserStatsResponse(BaseModel):
    """Schema for user backtest statistics."""

    total_backtests: int
    strategies_used: list[str]
    avg_return: float | None
    best_return: float | None
    worst_return: float | None
    avg_sharpe: float | None
    total_monte_carlo_runs: int


class BacktestRerunRequest(BaseModel):
    """Schema for rerunning a backtest from history."""

    history_id: int
    override_params: dict[str, Any] | None = Field(
        None, description="Parameters to override"
    )
    new_datasets: list[str] | None = Field(None, description="New datasets to use")
    new_date_range: dict[str, str] | None = Field(None, description="New date range")


class BacktestFavoriteCreate(BaseModel):
    """Schema for creating a favorite backtest configuration."""

    name: str = Field(
        ..., max_length=255, description="Name for the favorite configuration"
    )
    description: str | None = Field(
        None, description="Description of the configuration"
    )
    history_id: int = Field(
        ..., description="ID of the backtest history to save as favorite"
    )


class BacktestFavoriteResponse(BaseModel):
    """Schema for favorite backtest configuration response."""

    id: int
    name: str
    description: str | None
    strategy: str
    strategy_params: dict[str, Any]
    start_date: str | None
    end_date: str | None
    initial_capital: float
    monte_carlo_runs: int
    monte_carlo_method: str | None
    sample_fraction: float | None
    gaussian_scale: float | None
    datasets_used: list[str] | None
    price_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
