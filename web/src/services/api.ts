import axios from "axios"

// Placeholder API client setup for future backend integration
// Base URL can be replaced with real endpoint later.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "https://api.example.com",
  timeout: 10000,
})

export type PriceTick = { time: number; price: number }
export type OrderBookLevel = { price: number; qty: number }
export type OrderBook = { bids: OrderBookLevel[]; asks: OrderBookLevel[] }
export type Trade = {
  id: string
  time: number
  symbol: string
  side: "BUY" | "SELL"
  qty: number
  price: number
  balanceAfter: number
  realizedPnl?: number
}
export type Position = { symbol: string; qty: number; avgPrice: number }

export const endpoints = {
  prices: "/prices", // GET: fetch latest prices
  trades: "/trades", // GET: fetch trade history
  triggerTrade: "/trade", // POST: execute a trade
}

// Example placeholder functions. Replace implementations with real API calls later.
export async function fetchPrices(symbol: string): Promise<PriceTick[]> {
  // const { data } = await api.get(`${endpoints.prices}?symbol=${symbol}`)
  // return data
  return []
}

export async function fetchTrades(): Promise<Trade[]> {
  // const { data } = await api.get(endpoints.trades)
  // return data
  return []
}

export async function postTrade(payload: Omit<Trade, "id" | "time">): Promise<Trade> {
  // const { data } = await api.post(endpoints.triggerTrade, payload)
  // return data
  return { id: crypto.randomUUID(), time: Date.now(), ...payload }
}