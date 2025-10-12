import { BACKTEST_STRATEGIES, type StrategyId } from '@/config/backtestStrategies'
import { postFormData } from '@/services/apiClient'

// Strategy definitions from centralized config
export type DateRange = { startDate?: string; endDate?: string }
export type BacktestRequest = { strategy: StrategyId; params: Record<string, number>; dates?: DateRange }

// Normalized response used by the app (single file - backward compatible)
export type BacktestResponse = { timestamps: string[]; equity_curve: number[]; pnl: number; drawdown: number; sharpe: number }

// New types for multiple file support
export type BacktestResult = {
  filename: string
  timestamps: string[]
  equity_curve: number[]
  pnl: number
  drawdown: number
  sharpe: number
}

export type AggregatedMetrics = {
  average_pnl: number
  average_sharpe: number
  average_drawdown: number
  total_files_processed: number
}

export type MultipleBacktestResponse = {
  results: BacktestResult[]
  aggregated_metrics: AggregatedMetrics
}

// Union type for API responses
export type BacktestApiResponse = BacktestResponse | MultipleBacktestResponse

// Type guard to check if response is multiple results
export function isMultipleBacktestResponse(response: BacktestApiResponse): response is MultipleBacktestResponse {
  return 'results' in response && 'aggregated_metrics' in response
}

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

export function validateCsvFiles(files: File[]): void {
  if (files.length === 0) throw new BacktestValidationError('error.invalid_csv', 'No files provided')
  if (files.length > 10) throw new BacktestValidationError('error.csv_too_large', 'Maximum 10 files allowed')
  files.forEach(file => validateCsvFile(file))
}

function validateStrategy(strategy: StrategyId, params: Record<string, number>): void {
  const cfg = BACKTEST_STRATEGIES[strategy]
  const { ok } = cfg.validate(params)
  if (!ok) {
    const code = strategy === 'sma_crossover' ? 'error.invalid_sma_params' : 'error.invalid_rsi_params'
    throw new BacktestValidationError(code)
  }
}

function buildQuery(req: BacktestRequest, includeAggregated: boolean = false): string {
  const q = new URLSearchParams()
  q.set('strategy', req.strategy)
  const cfg = BACKTEST_STRATEGIES[req.strategy]
  for (const param of cfg.params) {
    const val = req.params[param.key]
    if (val !== undefined && val !== null) q.set(param.key, String(val))
  }
  if (req.dates?.startDate) q.set('start_date', req.dates.startDate)
  if (req.dates?.endDate) q.set('end_date', req.dates.endDate)
  if (includeAggregated) q.set('include_aggregated', 'true')
  return `?${q.toString()}`
}

type RawBacktestResponse = {
  // Single file response (backward compatible)
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

type RawMultipleBacktestResponse = {
  results: Array<{
    filename: string
    timestamps?: string[]
    equity_curve?: number[]
    dates?: string[]
    equity?: number[]
    pnl: number
    drawdown?: number
    max_drawdown?: number
    sharpe?: number
    sharpe_ratio?: number
  }>
  aggregated_metrics: {
    average_pnl: number
    average_sharpe: number
    average_drawdown: number
    total_files_processed: number
  }
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

function normalizeMultipleResponse(resp: RawMultipleBacktestResponse): MultipleBacktestResponse {
  return {
    results: resp.results.map(result => ({
      filename: result.filename,
      timestamps: result.timestamps ?? result.dates ?? [],
      equity_curve: result.equity_curve ?? result.equity ?? [],
      pnl: result.pnl,
      drawdown: result.drawdown ?? result.max_drawdown ?? 0,
      sharpe: result.sharpe ?? result.sharpe_ratio ?? 0,
    })),
    aggregated_metrics: resp.aggregated_metrics
  }
}

export async function runBacktest(file: File, req: BacktestRequest): Promise<BacktestResponse> {
  validateCsvFile(file)
  validateStrategy(req.strategy, req.params)

  const formData = new FormData()
  formData.append('csv', file)

  const query = buildQuery(req)
  const data = await postFormData<RawBacktestResponse>(`/backtest${query}`, formData)
  return normalizeResponse(data)
}

export async function runMultipleBacktests(files: File[], req: BacktestRequest): Promise<MultipleBacktestResponse> {
  validateCsvFiles(files)
  validateStrategy(req.strategy, req.params)

  const formData = new FormData()
  files.forEach(file => formData.append('csv', file))

  const query = buildQuery(req, true) // Include aggregated metrics
  const data = await postFormData<RawMultipleBacktestResponse>(`/backtest${query}`, formData)
  return normalizeMultipleResponse(data)
}

export async function runBacktestUnified(files: File[], req: BacktestRequest): Promise<BacktestApiResponse> {
  if (files.length === 1) {
    const file = files[0]
    if (!file) throw new BacktestValidationError('error.invalid_csv', 'No file provided')
    return await runBacktest(file, req)
  } else {
    return await runMultipleBacktests(files, req)
  }
}