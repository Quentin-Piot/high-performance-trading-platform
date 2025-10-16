import { BACKTEST_STRATEGIES, type StrategyId } from '@/config/backtestStrategies'
import { postFormData } from '@/services/apiClient'

// Strategy definitions from centralized config
export type DateRange = { startDate?: string; endDate?: string }
export type BacktestRequest = { 
  strategy: StrategyId; 
  params: Record<string, number>; 
  dates?: DateRange;
  // Monte Carlo parameters
  monte_carlo_runs?: number;  // 1-20000, default: 1
  method?: 'bootstrap' | 'gaussian';  // default: 'bootstrap'
  sample_fraction?: number;  // 0.1-2.0, default: 1.0
  gaussian_scale?: number;   // 0.1-5.0, default: 1.0
  // Optional job id to let backend stream progress to WS
  job_id?: string;
}

// Monte Carlo specific types
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
}

export interface MonteCarloResponse {
  results: MonteCarloResult[]
  aggregated_metrics: {
    average_pnl: number
    average_sharpe: number
    average_drawdown: number
    total_files_processed: number
  }
}

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

// Union type for API responses - handles both regular and Monte Carlo responses
export type BacktestApiResponse = BacktestResponse | MultipleBacktestResponse | MonteCarloResponse

// Type guards
export function isBacktestResponse(response: BacktestApiResponse): response is BacktestResponse {
  return 'timestamps' in response && 'equity_curve' in response && !('results' in response)
}

export function isMultipleBacktestResponse(response: BacktestApiResponse): response is MultipleBacktestResponse {
  return 'results' in response && Array.isArray(response.results) && 
         response.results.length > 0 && !!response.results[0] && 'timestamps' in response.results[0]
}

export function isMonteCarloResponse(response: any): response is MonteCarloResponse {
  if (!response || typeof response !== 'object') return false
  
  // Check for standard Monte Carlo structure
  if (response.results && Array.isArray(response.results) && response.results.length > 0) {
    const firstResult = response.results[0]
    if (firstResult?.metrics_distribution && firstResult?.equity_envelope) {
      return true
    }
  }
  
  // Check for numeric key structure (e.g., "0", "1", "2"...)
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

// Fonction pour normaliser les données equity_envelope du backend
function normalizeEquityEnvelope(envelope: any): EquityEnvelope {
  const normalizeArray = (arr: any[]): number[] => {
    return arr.map(item => {
      if (typeof item === 'number') return item
      if (typeof item === 'object' && item.parsedValue !== undefined) {
        return typeof item.parsedValue === 'number' ? item.parsedValue : parseFloat(item.parsedValue)
      }
      if (typeof item === 'string') return parseFloat(item)
      return 0
    })
  }

  return {
    timestamps: envelope.timestamps || [],
    p5: normalizeArray(envelope.p5 || []),
    p25: normalizeArray(envelope.p25 || []),
    median: normalizeArray(envelope.median || []),
    p75: normalizeArray(envelope.p75 || []),
    p95: normalizeArray(envelope.p95 || [])
  }
}

// Fonction pour normaliser les résultats Monte Carlo
function normalizeMonteCarloResponse(response: any): MonteCarloResponse {
  // Handle numeric key structure (e.g., {"0": {...}, "1": {...}})
  const keys = Object.keys(response)
  const numericKeys = keys.filter(key => /^\d+$/.test(key))
  
  if (numericKeys.length > 0) {
    // Convert numeric key structure to results array
    const results = numericKeys.map(key => {
      const result = response[key]
      return {
        ...result,
        equity_envelope: result.equity_envelope ? normalizeEquityEnvelope(result.equity_envelope) : undefined
      }
    })
    
    return {
      results,
      aggregated_metrics: response.aggregated_metrics || {
        average_pnl: 0,
        average_sharpe: 0,
        average_drawdown: 0,
        total_files_processed: results.length
      }
    }
  }
  
  // Handle standard structure
  return {
    results: response.results.map((result: any) => ({
      ...result,
      equity_envelope: normalizeEquityEnvelope(result.equity_envelope)
    })),
    aggregated_metrics: response.aggregated_metrics
  }
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
  
  // Monte Carlo parameters
  if (req.monte_carlo_runs !== undefined && req.monte_carlo_runs > 1) {
    q.set('monte_carlo_runs', String(req.monte_carlo_runs))
  }
  if (req.method) {
    q.set('method', req.method)
  }
  if (req.sample_fraction !== undefined) {
    q.set('sample_fraction', String(req.sample_fraction))
  }
  if (req.gaussian_scale !== undefined) {
    q.set('gaussian_scale', String(req.gaussian_scale))
  }
  if (req.job_id) {
    q.set('job_id', req.job_id)
  }
  
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


function asNegativeDrawdown(value?: number): number {
  const v = value ?? 0
  return v <= 0 ? v : -Math.abs(v)
}

function normalizeResponse(resp: RawBacktestResponse): BacktestResponse {
  // If already in normalized shape, return as-is
  if ('timestamps' in resp && 'equity_curve' in resp && resp.timestamps && resp.equity_curve) {
    return {
      timestamps: resp.timestamps,
      equity_curve: resp.equity_curve,
      pnl: resp.pnl,
      drawdown: asNegativeDrawdown(resp.drawdown ?? resp.max_drawdown ?? 0),
      sharpe: (resp.sharpe ?? resp.sharpe_ratio ?? 0),
    }
  }

  // Handle variant with dates/equity and possible max_drawdown/sharpe_ratio
  if ('dates' in resp && 'equity' in resp && resp.dates && resp.equity) {
    return {
      timestamps: resp.dates,
      equity_curve: resp.equity,
      pnl: resp.pnl,
      drawdown: asNegativeDrawdown(resp.drawdown ?? resp.max_drawdown ?? 0),
      sharpe: (resp.sharpe ?? resp.sharpe_ratio ?? 0),
    }
  }

  // Fallback: map what we can to the normalized shape
  return {
    timestamps: (resp.timestamps ?? resp.dates ?? []),
    equity_curve: (resp.equity_curve ?? resp.equity ?? []),
    pnl: resp.pnl,
    drawdown: asNegativeDrawdown(resp.drawdown ?? resp.max_drawdown ?? 0),
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

  const query = buildQuery(req, true) // Include aggregated metrics
  const data = await postFormData<RawMultipleBacktestResponse>(`/backtest${query}`, formData)
  return normalizeMultipleResponse(data)
}

export async function runBacktestUnified(files: File[], req: BacktestRequest): Promise<BacktestApiResponse> {
  // Determine if this is a Monte Carlo request
  const isMonteCarlo = req.monte_carlo_runs && req.monte_carlo_runs > 1

  if (isMonteCarlo) {
    // For Monte Carlo, we need to handle the response differently
    validateCsvFiles(files)
    validateStrategy(req.strategy, req.params)

    const formData = new FormData()
    files.forEach(file => formData.append('csv', file))
    
    const query = buildQuery(req, true) // Include aggregated for Monte Carlo
    const rawResponse = await postFormData(`/backtest${query}`, formData)
    
    // Check if this is a Monte Carlo response and normalize it
    if (isMonteCarloResponse(rawResponse as BacktestApiResponse)) {
      return normalizeMonteCarloResponse(rawResponse)
    }
    
    // If not detected as Monte Carlo, return as-is (fallback)
    return rawResponse as BacktestApiResponse
  }

  // Non-Monte Carlo logic (existing)
  if (files.length === 1) {
    const file = files[0]
    if (!file) throw new BacktestValidationError('error.invalid_csv', 'No file provided')
    return await runBacktest(file, req)
  } else {
    return await runMultipleBacktests(files, req)
  }
}