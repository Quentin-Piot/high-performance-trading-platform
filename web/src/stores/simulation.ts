import { defineStore } from "pinia"
import { createSimulator, type SimState, type SimulationParams } from "@/services/mockSim"
import type { Trade, PriceTick } from "@/services/api"
export const useSimulationStore = defineStore("simulation", {
  state: () => ({
    running: false as boolean,
    params: { symbol: "QUTE", intervalMs: 1000, volatility: 0.2, initialBalance: 100000 } as SimulationParams,
    sim: null as ReturnType<typeof createSimulator> | null,
    snapshot: null as SimState | null,
    tradesArr: [] as Trade[],
    pricesArr: [] as PriceTick[],
    realizedClosedPnl: 0 as number,
  }),
  getters: {
    balance: (s) => s.snapshot?.balance ?? (s.params.initialBalance ?? 0),
    pnl: (s) => s.snapshot?.pnl ?? 0,
    positions: (s) => s.snapshot?.positions ?? {},
    priceSeries: (s) => s.pricesArr,
    trades: (s) => s.tradesArr,
    openPositionQty: (s): number => Object.values(s.snapshot?.positions ?? {}).reduce((a, p) => a + p.qty, 0),
    avgEntryPrice: (s): number => {
      const pos = (s.snapshot?.positions ?? {})[s.params.symbol]
      return pos?.avgPrice ?? 0
    },
    unrealizedPnl: (s): number => s.snapshot?.pnl ?? 0,
    closedPnl: (s): number => s.realizedClosedPnl,
  },
  actions: {
    init() {
      if (this.sim) return
      this.sim = createSimulator(100, this.params)
      this.snapshot = this.sim.snapshot
      this.tradesArr = this.snapshot.trades
      this.pricesArr = this.snapshot.priceSeries
      this.sim.onUpdate((snap) => {
        this.snapshot = snap
        this.tradesArr = snap.trades
        this.pricesArr = snap.priceSeries
      })
    },
    start() {
      if (!this.sim) this.init()
      this.sim!.start()
      this.running = true
    },
    stop() {
      this.sim?.stop()
      this.running = false
    },
    reset() {
      this.realizedClosedPnl = 0
      if (this.sim) {
        this.sim.stop()
        this.sim = null
      }
      this.snapshot = null
      this.tradesArr = []
      this.pricesArr = []
      this.init()
      this.running = false
    },
    triggerTrade(side: "BUY" | "SELL", qty: number) {
      if (!this.sim) this.init()
      this.sim!.triggerTrade(side, qty)
      const latest = this.trades[0]
      if (latest?.realizedPnl !== undefined) this.realizedClosedPnl += latest.realizedPnl
    },
    setParams(p: Partial<SimulationParams>) {
      this.params = { ...this.params, ...p }
      if (this.sim && (p.intervalMs || p.volatility || p.symbol || p.initialBalance !== undefined)) {
        this.sim.stop()
        this.sim = createSimulator(this.sim.price, this.params)
        this.snapshot = this.sim.snapshot
        this.tradesArr = this.snapshot.trades
        this.pricesArr = this.snapshot.priceSeries
        this.sim.onUpdate((snap) => {
          this.snapshot = snap
          this.tradesArr = snap.trades
          this.pricesArr = snap.priceSeries
        })
        if (this.running) this.sim.start()
      }
    },
    setInitialBalance(value: number) {
      this.setParams({ initialBalance: value })
    },
  },
})