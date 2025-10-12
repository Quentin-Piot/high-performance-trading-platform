from pydantic import BaseModel
from typing import List, Optional

class SingleBacktestResult(BaseModel):
    """Results for a single CSV file backtest"""
    filename: str
    timestamps: List[str]
    equity_curve: List[float]
    pnl: float
    drawdown: float
    sharpe: float

class AggregatedMetrics(BaseModel):
    """Aggregated metrics across all CSV files"""
    average_pnl: float
    average_sharpe: float
    average_drawdown: float
    total_files_processed: int

class SingleBacktestResponse(BaseModel):
    """Response for single CSV backtest (backward compatibility)"""
    timestamps: List[str]
    equity_curve: List[float]
    pnl: float
    drawdown: float
    sharpe: float

class MultiBacktestResponse(BaseModel):
    """Response for multiple CSV backtest"""
    results: List[SingleBacktestResult]
    aggregated_metrics: Optional[AggregatedMetrics] = None

# Union type for the endpoint response
BacktestResponse = SingleBacktestResponse | MultiBacktestResponse
