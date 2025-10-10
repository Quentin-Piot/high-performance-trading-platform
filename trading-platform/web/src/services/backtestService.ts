import { postFormData } from '@/services/apiClient'
import { retry } from '@/lib/retry'
import { BACKTEST_STRATEGIES, type StrategyId } from '@/config/backtestStrategies'

// Strategy definitions from centralized config
export type DateRange = { startDate?: string; endDate?: string }
export type BacktestRequest = { strategy: StrategyId; params: Record<string, number>; dates?: DateRange }

// Normalized response used by the app
export type BacktestResponse = { timestamps: string[]; equity_curve: number[]; pnl: number; drawdown: number; sharpe: number }

export type BacktestErrorCode =
  | 'error.invalid_csv'
  | 'error.csv_too_large'
  | 'error.invalid_sma_params'
  | 'error.invalid_rsi_params'
  | 'error.backtest_failed'

export class BacktestValidationError extends Error {
  code: BacktestErrorCode
  constructor(code: BacktestErrorCode, message?: string) {
    super(message)
    this.code = code
    this.name = 'BacktestValidationError'
  }
}

export function validateCsvFile(file: File): void {
  const isCsv = file && (file.type === 'text/csv' || file.name.toLowerCase().endsWith('.csv'))
  if (!isCsv) throw new BacktestValidationError('error.invalid_csv')
  if (file.size > 5 * 1024 * 1024) throw new BacktestValidationError('error.csv_too_large')
}

function validateStrategy(strategy: StrategyId, params: Record<string, number>): void {
  const cfg = BACKTEST_STRATEGIES[strategy]
  const { ok } = cfg.validate(params)
  if (!ok) {
    const code = strategy === 'sma_crossover' ? 'error.invalid_sma_params' : 'error.invalid_rsi_params'
    throw new BacktestValidationError(code)
  }
}

function buildQuery(req: BacktestRequest): string {
  const q = new URLSearchParams()
  q.set('strategy', req.strategy)
  const cfg = BACKTEST_STRATEGIES[req.strategy]
  for (const param of cfg.params) {
    const val = req.params[param.key]
    if (val !== undefined && val !== null) q.set(param.key, String(val))
  }
  if (req.dates?.startDate) q.set('start_date', req.dates.startDate)
  if (req.dates?.endDate) q.set('end_date', req.dates.endDate)
  return `?${q.toString()}`
}

type RawBacktestResponse = {
  // Normalized or domain-style variants from backend
  timestamps?: string[]
  equity_curve?: number[]
  dates?: string[]
  equity?: number[]
  pnl: number
  drawdown?: number
  max_drawdown?: number
  sharpe?: number
  sharpe_ratio?: number
  metrics?: unknown
  signals?: unknown
  trades?: unknown
}

function normalizeResponse(resp: RawBacktestResponse): BacktestResponse {
  // If already in normalized shape, return as-is
  if ('timestamps' in resp && 'equity_curve' in resp && resp.timestamps && resp.equity_curve) {
    return {
      timestamps: resp.timestamps,
      equity_curve: resp.equity_curve,
      pnl: resp.pnl,
      drawdown: (resp.drawdown ?? resp.max_drawdown ?? 0),
      sharpe: (resp.sharpe ?? resp.sharpe_ratio ?? 0),
    }
  }

  // Handle variant with dates/equity and possible max_drawdown/sharpe_ratio
  if ('dates' in resp && 'equity' in resp && resp.dates && resp.equity) {
    return {
      timestamps: resp.dates,
      equity_curve: resp.equity,
      pnl: resp.pnl,
      drawdown: (resp.drawdown ?? resp.max_drawdown ?? 0),
      sharpe: (resp.sharpe ?? resp.sharpe_ratio ?? 0),
    }
  }

  // Fallback: map what we can to the normalized shape
  return {
    timestamps: (resp.timestamps ?? resp.dates ?? []),
    equity_curve: (resp.equity_curve ?? resp.equity ?? []),
    pnl: resp.pnl,
    drawdown: (resp.drawdown ?? resp.max_drawdown ?? 0),
    sharpe: (resp.sharpe ?? resp.sharpe_ratio ?? 0),
  }
}

export async function runBacktest(file: File, req: BacktestRequest): Promise<BacktestResponse> {
  validateCsvFile(file)
  validateStrategy(req.strategy, req.params)
  const fd = new FormData()
  fd.append('csv', file)
  const qs = buildQuery(req)
  const raw = await retry(() => postFormData<RawBacktestResponse>(`/backtest${qs}`, fd))
  return normalizeResponse(raw)
}