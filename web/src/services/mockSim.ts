import type { PriceTick, Trade, OrderBook } from "./api"

export type SimulationParams = {
  symbol: string
  intervalMs: number
  volatility: number // daily volatility proxy
  initialBalance?: number
}

export type SimState = {
  balance: number
  pnl: number
  positions: Record<string, { qty: number; avgPrice: number }>
  priceSeries: PriceTick[]
  trades: Trade[]
  orderBook: OrderBook
}

export function createSimulator(initialPrice = 100, params: SimulationParams) {
  let price = initialPrice
  let timer: number | null = null
  const state: SimState = {
    balance: params.initialBalance ?? 100000,
    pnl: 0,
    positions: {},
    priceSeries: [],
    trades: [],
    orderBook: buildOrderBook(initialPrice),
  }

  const listeners: Array<(s: SimState) => void> = []
  const emit = () => {
    const snap: SimState = {
      balance: state.balance,
      pnl: state.pnl,
      positions: { ...state.positions },
      priceSeries: state.priceSeries.slice(),
      trades: state.trades.slice(),
      orderBook: {
        bids: state.orderBook.bids.slice(),
        asks: state.orderBook.asks.slice(),
      },
    }
    listeners.forEach((cb) => cb(snap))
  }

  const step = () => {
    // Geometric Brownian Motion-like step
    const dt = params.intervalMs / (1000 * 60 * 60 * 24)
    const mu = 0.05 // drift
    const sigma = params.volatility
    const z = gaussian()
    const factor = Math.exp((mu - 0.5 * sigma * sigma) * dt + sigma * Math.sqrt(dt) * z)
    price = Math.max(0.01, price * factor)

    const tick = { time: Date.now(), price: round(price, 2) }
    state.priceSeries.push(tick)

    // Update order book levels around current price
    state.orderBook = buildOrderBook(price)

    // Mark-to-market unrealized PnL
    state.pnl = computePnL(state, price)
    emit()
  }

  const start = () => {
    if (timer) return
    // emit an immediate tick so UI updates instantly
    step()
    timer = setInterval(step, params.intervalMs) as unknown as number
  }
  const stop = () => {
    if (!timer) return
    clearInterval(timer as unknown as number)
    timer = null
  }

  const triggerTrade = (side: "BUY" | "SELL", qty: number) => {
    const px = price
    const id = (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function')
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2) + Date.now().toString(36)

    // Prepare realized PnL for SELL against current position
    const currentPos = state.positions[params.symbol] || { qty: 0, avgPrice: px }
    const realized = side === "SELL" ? round((px - currentPos.avgPrice) * qty, 2) : undefined

    // Update positions and balance
    const pos = { ...currentPos }
    if (side === "BUY") {
      const newQty = pos.qty + qty
      pos.avgPrice = (pos.avgPrice * pos.qty + px * qty) / (newQty || 1)
      pos.qty = newQty
      state.balance -= px * qty
    } else {
      const newQty = pos.qty - qty
      state.balance += px * qty
      pos.qty = newQty
      if (pos.qty <= 0) pos.avgPrice = px
    }
    state.positions[params.symbol] = pos

    const t: Trade = {
      id,
      time: Date.now(),
      symbol: params.symbol,
      side,
      qty,
      price: round(px, 2),
      balanceAfter: round(state.balance, 2),
      realizedPnl: realized,
    }
    state.trades.unshift(t)

    state.pnl = computePnL(state, price)
    emit()
  }

  const onUpdate = (cb: (s: SimState) => void) => {
    listeners.push(cb)
    return () => {
      const i = listeners.indexOf(cb)
      if (i >= 0) listeners.splice(i, 1)
    }
  }

  return {
    start,
    stop,
    triggerTrade,
    onUpdate,
    get snapshot() {
      return {
        balance: state.balance,
        pnl: state.pnl,
        positions: { ...state.positions },
        priceSeries: state.priceSeries.slice(),
        trades: state.trades.slice(),
        orderBook: {
          bids: state.orderBook.bids.slice(),
          asks: state.orderBook.asks.slice(),
        },
      }
    },
    get price() { return price }
  }
}

function gaussian() {
  // Box-Muller transform
  let u = 0, v = 0
  while (u === 0) u = Math.random()
  while (v === 0) v = Math.random()
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v)
}

function round(n: number, d = 2) {
  const f = 10 ** d
  return Math.round(n * f) / f
}

function computePnL(state: SimState, price: number) {
  let pnl = 0
  for (const [, pos] of Object.entries(state.positions)) {
    pnl += (price - pos.avgPrice) * pos.qty
  }
  return round(pnl, 2)
}

function buildOrderBook(px: number): OrderBook {
  const tick = Math.max(0.01, round(px * 0.001, 2))
  const levels = 5
  const bids = []
  const asks = []
  for (let i = 1; i <= levels; i++) {
    bids.push({ price: round(px - i * tick, 2), qty: Math.floor(5 + Math.random() * 95) })
    asks.push({ price: round(px + i * tick, 2), qty: Math.floor(5 + Math.random() * 95) })
  }
  // Ensure sorted: bids descending, asks ascending
  bids.sort((a, b) => b.price - a.price)
  asks.sort((a, b) => a.price - b.price)
  return { bids, asks }
}