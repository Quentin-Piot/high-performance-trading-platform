from pydantic import BaseModel
from typing import List, Optional, Dict

class MetricsDistribution(BaseModel):
    """Statistical distribution of a metric"""
    mean: float
    std: float
    p5: float
    p25: float
    median: float
    p75: float
    p95: float

class EquityEnvelope(BaseModel):
    """Equity curve envelope with percentiles"""
    timestamps: List[str]
    p5: List[float]
    p25: List[float]
    median: List[float]
    p75: List[float]
    p95: List[float]

class SingleBacktestResult(BaseModel):
    """Results for a single CSV file backtest"""
    filename: str
    timestamps: List[str]
    equity_curve: List[float]
    pnl: float
    drawdown: float
    sharpe: float

class MonteCarloBacktestResult(BaseModel):
    """Results for a Monte Carlo backtest on a single CSV file"""
    filename: str
    method: str
    runs: int
    successful_runs: int
    metrics_distribution: Dict[str, MetricsDistribution]
    equity_envelope: Optional[EquityEnvelope] = None

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

class MonteCarloResponse(BaseModel):
    """Response for Monte Carlo backtest"""
    results: List[MonteCarloBacktestResult]
    aggregated_metrics: Optional[AggregatedMetrics] = None

# Union type for the endpoint response
BacktestResponse = SingleBacktestResponse | MultiBacktestResponse | MonteCarloResponse
