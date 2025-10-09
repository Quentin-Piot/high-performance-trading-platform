export interface BacktestResponse {
  timestamps: string[]
  equity_curve: number[]
  pnl: number
  drawdown: number
  sharpe: number
}

export interface EquityPoint {
  time: number // UTCTimestamp seconds
  value: number
}

