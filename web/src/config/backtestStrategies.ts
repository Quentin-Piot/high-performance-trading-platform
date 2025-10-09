export type StrategyParam = {
  key: string
  label: string
  type: 'int' | 'float'
  default: number
  min?: number
}

export type StrategyConfig = {
  id: StrategyId
  name: string
  params: StrategyParam[]
  validate: (values: Record<string, number>) => { ok: boolean; message?: string }
}

export type StrategyId = 'sma_crossover' | 'rsi'

export const BACKTEST_STRATEGIES: Record<StrategyId, StrategyConfig> = {
  sma_crossover: {
    id: 'sma_crossover',
    name: 'SMA Crossover',
    params: [
      { key: 'sma_short', label: 'SMA Short', type: 'int', default: 10, min: 1 },
      { key: 'sma_long', label: 'SMA Long', type: 'int', default: 30, min: 2 },
    ],
    validate(values) {
      const s = values['sma_short'] ?? 0
      const l = values['sma_long'] ?? 0
      const ok = s > 0 && l > 0 && s < l
      return ok
        ? { ok }
        : { ok, message: 'SMA Short must be < SMA Long and > 0' }
    },
  },
  rsi: {
    id: 'rsi',
    name: 'RSI Strategy',
    params: [
      { key: 'period', label: 'RSI Period', type: 'int', default: 14, min: 1 },
      { key: 'overbought', label: 'Overbought', type: 'float', default: 70.0 },
      { key: 'oversold', label: 'Oversold', type: 'float', default: 30.0 },
    ],
    validate(values) {
      const p = values['period'] ?? 0
      const ob = values['overbought'] ?? 0
      const os = values['oversold'] ?? 0
      const ok = p > 0 && ob > os
      return ok
        ? { ok }
        : { ok, message: 'Overbought must be > Oversold; Period > 0' }
    },
  },
}