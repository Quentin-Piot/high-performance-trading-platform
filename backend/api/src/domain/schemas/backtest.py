from pydantic import BaseModel, ConfigDict


class MetricsDistribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mean: float
    std: float
    p5: float
    p25: float
    median: float
    p75: float
    p95: float


class EquityEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamps: list[str]
    p5: list[float]
    p25: list[float]
    median: list[float]
    p75: list[float]
    p95: list[float]


class SingleBacktestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    timestamps: list[str]
    equity_curve: list[float]
    pnl: float
    drawdown: float
    sharpe: float


class MonteCarloBacktestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    method: str
    runs: int
    successful_runs: int
    metrics_distribution: dict[str, MetricsDistribution]
    equity_envelope: EquityEnvelope | None = None


class AggregatedMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    average_pnl: float
    average_sharpe: float
    average_drawdown: float
    total_files_processed: int


class SingleBacktestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamps: list[str]
    equity_curve: list[float]
    pnl: float
    drawdown: float
    sharpe: float
    processing_time: str | None = None


class MultiBacktestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[SingleBacktestResult]
    aggregated_metrics: AggregatedMetrics | None = None
    processing_time: str | None = None


class MonteCarloResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[MonteCarloBacktestResult]
    aggregated_metrics: AggregatedMetrics | None = None
    processing_time: str | None = None


BacktestResponse = SingleBacktestResponse | MultiBacktestResponse | MonteCarloResponse
