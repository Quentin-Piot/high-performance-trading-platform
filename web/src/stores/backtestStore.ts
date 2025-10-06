import { defineStore } from 'pinia'
import { postFormData, type BacktestResponse } from '@/services/apiClient'
import { buildEquityPoints, toLineData } from '@/composables/useEquitySeries'

export type BacktestStatus = 'idle' | 'loading' | 'success' | 'error'

export const useBacktestStore = defineStore('backtest', {
  state: () => ({
    status: 'idle' as BacktestStatus,
    timestamps: [] as string[],
    equityCurve: [] as number[],
    pnl: null as number | null,
    drawdown: null as number | null,
    sharpe: null as number | null,
    error: null as string | null,
  }),
  getters: {
    equitySeries(state) {
      const points = buildEquityPoints(state.timestamps, state.equityCurve)
      return toLineData(points)
    },
  },
  actions: {
    reset() {
      this.status = 'idle'
      this.timestamps = []
      this.equityCurve = []
      this.pnl = null
      this.drawdown = null
      this.sharpe = null
      this.error = null
    },
    async runBacktest(file: File, smaShort: number, smaLong: number) {
      this.status = 'loading'
      this.error = null
      try {
        // client-side validation
        if (!file || file.type !== 'text/csv') throw new Error('Le fichier doit être au format .csv')
        if (file.size > 5 * 1024 * 1024) throw new Error('Le fichier doit être ≤ 5MB')
        if (!(smaShort > 0 && smaLong > 0 && smaShort < smaLong)) throw new Error('Paramètres SMA invalides')

        const fd = new FormData()
        fd.append('csv', file)
        const qs = `?sma_short=${encodeURIComponent(smaShort)}&sma_long=${encodeURIComponent(smaLong)}`
        const resp = await postFormData<BacktestResponse>(`/backtest${qs}`, fd)

        const curve = resp.equity_curve || []
        const base = curve.length ? curve[0] : 1
        const normalized = base ? curve.map(v => v / base) : curve

        this.timestamps = resp.timestamps || []
        this.equityCurve = normalized
        this.pnl = resp.pnl
        this.drawdown = resp.drawdown
        this.sharpe = resp.sharpe
        this.status = 'success'
      } catch (e: any) {
        this.error = e?.message || 'Erreur lors du backtest'
        this.status = 'error'
      }
    },
  },
})