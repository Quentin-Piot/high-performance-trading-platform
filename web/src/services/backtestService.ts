import { BACKTEST_STRATEGIES, type StrategyId } from '@/config/backtestStrategies'
import { postFormData, BASE_URL } from '@/services/apiClient'
export type DateRange = { startDate?: string; endDate?: string }
export type BacktestRequest = { 
  strategy: StrategyId; 
  params: Record<string, number>; 
  dates?: DateRange;
  monte_carlo_runs?: number;  
  method?: 'bootstrap' | 'gaussian';  
  sample_fraction?: number;  
  gaussian_scale?: number;   
  price_type?: 'close' | 'adj_close';
  normalize?: boolean;
}
export interface MetricsDistribution {
  mean: number
  std: number
  p5: number
  p25: number
  median: number
  p75: number
  p95: number
}
export interface EquityEnvelope {
  timestamps: string[]
  p5: number[]
  p25: number[]
  median: number[]
  p75: number[]
  p95: number[]
}
export interface MonteCarloResult {
  filename: string
  method: 'bootstrap' | 'gaussian'
  runs: number
  successful_runs: number
  metrics_distribution: {
    pnl: MetricsDistribution
    sharpe: MetricsDistribution
    drawdown: MetricsDistribution
  }
  equity_envelope: EquityEnvelope
  processing_time?: string
}
export interface MonteCarloResponse {
  results: MonteCarloResult[]
  aggregated_metrics: {
    average_pnl: number
    average_sharpe: number
    average_drawdown: number
    total_files_processed: number
  }
  processing_time?: string
}
export type BacktestResponse = { 
  timestamps: string[]; 
  equity_curve: number[]; 
  pnl: number; 
  drawdown: number; 
  sharpe: number;
  processing_time?: string;
}
export type BacktestResult = {
  filename: string
  timestamps: string[]
  equity_curve: number[]
  pnl: number
  drawdown: number
  sharpe: number
  processing_time?: string
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
export type BacktestApiResponse = BacktestResponse | MultipleBacktestResponse | MonteCarloResponse
export function isBacktestResponse(response: BacktestApiResponse): response is BacktestResponse {
  return 'timestamps' in response && 'equity_curve' in response && !('results' in response)
}
export function isMultipleBacktestResponse(response: BacktestApiResponse): response is MultipleBacktestResponse {
  return 'results' in response && Array.isArray(response.results) && 
         response.results.length > 0 && !!response.results[0] && 'timestamps' in response.results[0]
}
export function isMonteCarloResponse(response: any): response is MonteCarloResponse {
  if (!response || typeof response !== 'object') return false
  if (response.results && Array.isArray(response.results) && response.results.length > 0) {
    const firstResult = response.results[0]
    if (firstResult?.metrics_distribution && firstResult?.equity_envelope) {
      return true
    }
  }
  const keys = Object.keys(response)
  const numericKeys = keys.filter(key => /^\d+$/.test(key))
  if (numericKeys.length > 0) {
    const firstKey = numericKeys[0]!
    const firstResult = response[firstKey]
    if (firstResult?.metrics_distribution && firstResult?.equity_envelope) {
      return true
    }
  }
  return false
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
  const params = new URLSearchParams()
  params.set('strategy', req.strategy)
  Object.entries(req.params).forEach(([key, value]) => {
    params.set(key, value.toString())
  })
  if (req.dates?.startDate) params.set('start_date', req.dates.startDate)
  if (req.dates?.endDate) params.set('end_date', req.dates.endDate)
  if (req.monte_carlo_runs) params.set('monte_carlo_runs', req.monte_carlo_runs.toString())
  if (req.method) params.set('method', req.method)
  if (req.sample_fraction) params.set('sample_fraction', req.sample_fraction.toString())
  if (req.gaussian_scale) params.set('gaussian_scale', req.gaussian_scale.toString())
  if (req.normalize) params.set('normalize', req.normalize.toString())
  if (includeAggregated) params.set('aggregated', 'true')
  return params.toString() ? `?${params.toString()}` : ''
}
type RawBacktestResponse = {
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
  processing_time?: string
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
function asNegativeDrawdown(value?: number): number {
  const v = value ?? 0
  return v <= 0 ? v : -Math.abs(v)
}
function normalizeResponse(resp: RawBacktestResponse): BacktestResponse {
  if ('timestamps' in resp && 'equity_curve' in resp && resp.timestamps && resp.equity_curve) {
    return {
      timestamps: resp.timestamps,
      equity_curve: resp.equity_curve,
      pnl: resp.pnl,
      drawdown: asNegativeDrawdown(resp.drawdown ?? resp.max_drawdown ?? 0),
      sharpe: (resp.sharpe ?? resp.sharpe_ratio ?? 0),
      processing_time: resp.processing_time,
    }
  }
  if ('dates' in resp && 'equity' in resp && resp.dates && resp.equity) {
    return {
      timestamps: resp.dates,
      equity_curve: resp.equity,
      pnl: resp.pnl,
      drawdown: asNegativeDrawdown(resp.drawdown ?? resp.max_drawdown ?? 0),
      sharpe: (resp.sharpe ?? resp.sharpe_ratio ?? 0),
      processing_time: resp.processing_time,
    }
  }
  return {
    timestamps: (resp.timestamps ?? resp.dates ?? []),
    equity_curve: (resp.equity_curve ?? resp.equity ?? []),
    pnl: resp.pnl,
    drawdown: asNegativeDrawdown(resp.drawdown ?? resp.max_drawdown ?? 0),
    sharpe: (resp.sharpe ?? resp.sharpe_ratio ?? 0),
    processing_time: resp.processing_time,
  }
}
function normalizeMultipleResponse(resp: RawMultipleBacktestResponse): MultipleBacktestResponse {
  return {
    results: resp.results.map(result => ({
      filename: result.filename,
      timestamps: result.timestamps ?? result.dates ?? [],
      equity_curve: result.equity_curve ?? result.equity ?? [],
      pnl: result.pnl,
      drawdown: asNegativeDrawdown(result.drawdown ?? result.max_drawdown ?? 0),
      sharpe: result.sharpe ?? result.sharpe_ratio ?? 0,
    })),
    aggregated_metrics: {
      average_pnl: resp.aggregated_metrics.average_pnl,
      average_sharpe: resp.aggregated_metrics.average_sharpe,
      average_drawdown: asNegativeDrawdown(resp.aggregated_metrics.average_drawdown),
      total_files_processed: resp.aggregated_metrics.total_files_processed,
    }
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
  const query = buildQuery(req, true) 
  const data = await postFormData<RawMultipleBacktestResponse>(`/backtest${query}`, formData)
  return normalizeMultipleResponse(data)
}
export async function runBacktestUnified(files: File[], req: BacktestRequest, selectedDatasets?: string[]): Promise<BacktestApiResponse> {
  const isMonteCarlo = req.monte_carlo_runs && req.monte_carlo_runs > 1
  if (isMonteCarlo) {
    validateStrategy(req.strategy, req.params)
    const params = new URLSearchParams()
    if (selectedDatasets && selectedDatasets.length > 0) {
      params.set('symbol', selectedDatasets[0]!) 
      if (req.dates?.startDate) {
        params.set('start_date', req.dates.startDate)
      }
      if (req.dates?.endDate) {
        params.set('end_date', req.dates.endDate)
      }
    }
    params.set('num_runs', req.monte_carlo_runs!.toString())
    params.set('initial_capital', '10000') 
    params.set('strategy', req.strategy)
    Object.entries(req.params).forEach(([key, value]) => {
      params.set(key, value.toString())
    })
    if (req.method) params.set('method', req.method)
    if (req.sample_fraction) params.set('sample_fraction', req.sample_fraction.toString())
    if (req.gaussian_scale) params.set('gaussian_scale', req.gaussian_scale.toString())
    if (req.price_type) params.set('price_type', req.price_type)
    if (req.normalize) params.set('normalize', req.normalize.toString())
    const formData = new FormData()
    if (files.length > 0 && (!selectedDatasets || selectedDatasets.length === 0)) {
      validateCsvFiles(files)
      files.forEach(file => {
        formData.append('file', file)
      })
    }
    const url = `/monte-carlo/run?${params.toString()}`
    const response = await fetch(`${BASE_URL}${url}`, {
      method: 'POST',
      body: (files.length > 0 && (!selectedDatasets || selectedDatasets.length === 0)) ? formData : undefined,
    })
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(`HTTP ${response.status}: ${errorData.detail || 'Request failed'}`)
    }
    const rawResponse = await response.json()
    return rawResponse as MonteCarloResponse
  }
  if (selectedDatasets && selectedDatasets.length > 0) {
    const params = new URLSearchParams()
    params.set('symbol', selectedDatasets[0]!)
    if (req.dates?.startDate) {
      params.set('start_date', req.dates.startDate)
    }
    if (req.dates?.endDate) {
      params.set('end_date', req.dates.endDate)
    }
    params.set('strategy', req.strategy)
    Object.entries(req.params).forEach(([key, value]) => {
      params.set(key, value.toString())
    })
    if (req.price_type) params.set('price_type', req.price_type)
    if (selectedDatasets.length > 1) {
      params.set('include_aggregated', 'true')
    }
    const url = `/backtest?${params.toString()}`
    const response = await fetch(`${BASE_URL}${url}`, {
      method: 'POST',
    })
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(`HTTP ${response.status}: ${errorData.detail || 'Request failed'}`)
    }
    const rawResponse = await response.json()
    if (selectedDatasets.length > 1) {
      return normalizeMultipleResponse(rawResponse)
    } else {
      return normalizeResponse(rawResponse)
    }
  }
  if (files.length === 1) {
    const file = files[0]
    if (!file) throw new BacktestValidationError('error.invalid_csv', 'No file provided')
    return await runBacktest(file, req)
  } else {
    return await runMultipleBacktests(files, req)
  }
}