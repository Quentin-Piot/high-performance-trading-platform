import { postFormData } from '@/services/apiClient'
import { retry } from '@/lib/retry'

// Strategy definitions
export type Strategy = 'sma' | 'rsi'
export type SmaParams = { smaShort: number; smaLong: number }
export type RsiParams = { period: number; overbought: number; oversold: number }
export type DateRange = { startDate?: string; endDate?: string }
export type BacktestRequest = { strategy: Strategy; params: SmaParams | RsiParams; dates?: DateRange }

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

function validateSma(params: SmaParams): void {
  const ok = params.smaShort > 0 && params.smaLong > 0 && params.smaShort < params.smaLong
  if (!ok) throw new BacktestValidationError('error.invalid_sma_params')
}

function validateRsi(params: RsiParams): void {
  const ok = params.period > 0 && params.overbought > params.oversold
  if (!ok) throw new BacktestValidationError('error.invalid_rsi_params')
}

function buildQuery(req: BacktestRequest): string {
  const q = new URLSearchParams()
  q.set('strategy', req.strategy)
  if (req.strategy === 'sma') {
    const p = req.params as SmaParams
    q.set('sma_short', String(p.smaShort))
    q.set('sma_long', String(p.smaLong))
  } else if (req.strategy === 'rsi') {
    const p = req.params as RsiParams
    q.set('period', String(p.period))
    q.set('overbought', String(p.overbought))
    q.set('oversold', String(p.oversold))
  }
  if (req.dates?.startDate) q.set('start_date', req.dates.startDate)
  if (req.dates?.endDate) q.set('end_date', req.dates.endDate)
  return `?${q.toString()}`
}

type RawBacktestResponse =
  | { dates: string[]; equity: number[]; pnl: number; drawdown: number; sharpe: number }
  | BacktestResponse

function normalizeResponse(resp: RawBacktestResponse): BacktestResponse {
  if ('dates' in resp && 'equity' in resp) {
    return {
      timestamps: resp.dates,
      equity_curve: resp.equity,
      pnl: resp.pnl,
      drawdown: resp.drawdown,
      sharpe: resp.sharpe,
    }
  }
  return resp
}

export async function runBacktest(file: File, req: BacktestRequest): Promise<BacktestResponse> {
  validateCsvFile(file)
  if (req.strategy === 'sma') validateSma(req.params as SmaParams)
  if (req.strategy === 'rsi') validateRsi(req.params as RsiParams)
  const fd = new FormData()
  fd.append('csv', file)
  const qs = buildQuery(req)
  const raw = await retry(() => postFormData<RawBacktestResponse>(`/api/v1/backtest${qs}`, fd))
  return normalizeResponse(raw)
}