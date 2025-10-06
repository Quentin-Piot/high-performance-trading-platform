export interface BacktestResponse {
  timestamps: string[]
  equity_curve: number[]
  pnl?: number
  max_drawdown?: number
  sharpe?: number
}

export interface EquityPoint {
  time: number // UTCTimestamp seconds
  value: number
}

export interface Metrics {
  pnl: number
  maxDrawdown: number
  sharpe: number
}