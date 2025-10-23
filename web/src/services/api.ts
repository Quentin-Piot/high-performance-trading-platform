import axios from "axios";
export const api = axios.create({
  baseURL: "/api/v1",
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
  prices: "/prices", 
  trades: "/trades", 
  triggerTrade: "/trade", 
};
export async function fetchPrices(): Promise<PriceTick[]> {
  return [];
}
export async function fetchTrades(): Promise<Trade[]> {
  return [];
}
export async function postTrade(
  payload: Omit<Trade, "id" | "time">,
): Promise<Trade> {
  return { id: crypto.randomUUID(), time: Date.now(), ...payload };
}