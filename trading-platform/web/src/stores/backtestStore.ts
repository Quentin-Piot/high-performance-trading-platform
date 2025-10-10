import { defineStore } from 'pinia'
import { BacktestValidationError, runBacktest as runBacktestSvc } from '@/services/backtestService'
import type { BacktestResponse, BacktestRequest } from '@/services/backtestService'
import { useErrorStore } from '@/stores/errorStore'
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
    errorCode: null as string | null,
    errorMessage: null as string | null,
    lastFile: null as File | null,
    lastRequest: null as BacktestRequest | null,
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
      this.errorCode = null
      this.errorMessage = null
      this.lastFile = null
      this.lastRequest = null
    },
    async runBacktest(file: File, req: BacktestRequest) {
      this.status = 'loading'
      this.errorCode = null
      this.errorMessage = null
      try {
        const resp: BacktestResponse = await runBacktestSvc(file, req)

        const curve = resp.equity_curve || []
        const base = curve.length ? curve[0] : 1
        const normalized = base ? curve.map(v => v / base) : curve

        this.timestamps = resp.timestamps || []
        this.equityCurve = normalized
        this.pnl = resp.pnl
        this.drawdown = resp.drawdown
        this.sharpe = resp.sharpe
        this.lastFile = file
        this.lastRequest = req
        this.status = 'success'
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e)
        let code: string = 'error.backtest_failed'
        if (e instanceof BacktestValidationError) {
          code = e.code
        }
        this.errorCode = code
        this.errorMessage = msg
        useErrorStore().log(code, msg, req)
        this.status = 'error'
      }
    },
    async retryLast() {
      if (!this.lastFile || !this.lastRequest) return
      await this.runBacktest(this.lastFile, this.lastRequest)
    },
  },
})