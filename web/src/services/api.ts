/// <reference types="vite/client" />
import axios from "axios";

// API base URL configuration using environment variable
// Local: http://localhost:8000/api/v1 (via VITE_API_BASE_URL)
// Production: /api/v1 (default fallback)

export const api = axios.create({
  baseURL: "http://localhost:8000/api/v1",
  timeout: 10000,
});

export type PriceTick = { time: number; price: number };
export type OrderBookLevel = { price: number; qty: number };
export type OrderBook = { bids: OrderBookLevel[]; asks: OrderBookLevel[] };
export type Trade = {
  id: string;
  time: number;
  symbol: string;
  side: "BUY" | "SELL";
  qty: number;
  price: number;
  balanceAfter: number;
  realizedPnl?: number;
};
export type Position = { symbol: string; qty: number; avgPrice: number };

export const endpoints = {
  prices: "/prices", // GET: fetch latest prices
  trades: "/trades", // GET: fetch trade history
  triggerTrade: "/trade", // POST: execute a trade
};

// Example placeholder functions. Replace implementations with real API calls later.
export async function fetchPrices(): Promise<PriceTick[]> {
  // const { data } = await api.get(`${endpoints.prices}?symbol=${symbol}`)
  // return data
  return [];
}

export async function fetchTrades(): Promise<Trade[]> {
  // const { data } = await api.get(endpoints.trades)
  // return data
  return [];
}

export async function postTrade(
  payload: Omit<Trade, "id" | "time">,
): Promise<Trade> {
  // const { data } = await api.post(endpoints.triggerTrade, payload)
  // return data
  return { id: crypto.randomUUID(), time: Date.now(), ...payload };
}
