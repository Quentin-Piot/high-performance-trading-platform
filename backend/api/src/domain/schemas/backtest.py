from pydantic import BaseModel


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
    timestamps: list[str]
    p5: list[float]
    p25: list[float]
    median: list[float]
    p75: list[float]
    p95: list[float]
class SingleBacktestResult(BaseModel):
    """Results for a single CSV file backtest"""
    filename: str
    timestamps: list[str]
    equity_curve: list[float]
    pnl: float
    drawdown: float
    sharpe: float
class MonteCarloBacktestResult(BaseModel):
    """Results for a Monte Carlo backtest on a single CSV file"""
    filename: str
    method: str
    runs: int
    successful_runs: int
    metrics_distribution: dict[str, MetricsDistribution]
    equity_envelope: EquityEnvelope | None = None
class AggregatedMetrics(BaseModel):
    """Aggregated metrics across all CSV files"""
    average_pnl: float
    average_sharpe: float
    average_drawdown: float
    total_files_processed: int
class SingleBacktestResponse(BaseModel):
    """Response for single CSV backtest (backward compatibility)"""
    timestamps: list[str]
    equity_curve: list[float]
    pnl: float
    drawdown: float
    sharpe: float
    processing_time: str | None = None


class MultiBacktestResponse(BaseModel):
    """Response for multiple CSV backtest"""
    results: list[SingleBacktestResult]
    aggregated_metrics: AggregatedMetrics | None = None
    processing_time: str | None = None


class MonteCarloResponse(BaseModel):
    """Response for Monte Carlo backtest"""
    results: list[MonteCarloBacktestResult]
    aggregated_metrics: AggregatedMetrics | None = None
    processing_time: str | None = None
BacktestResponse = SingleBacktestResponse | MultiBacktestResponse | MonteCarloResponse
