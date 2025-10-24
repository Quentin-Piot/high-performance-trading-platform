import type { EquityPoint } from "../types/backtest"
export type LinePoint = { time: number; value: number }
export function toUtcTimestamp(ts: string): number {
  const m = ts.match(/^([0-9]{4})-([0-9]{2})-([0-9]{2})(?:$|T)/)
  if (m) {
    const year = Number(m[1])
    const month = Number(m[2]) - 1
    const day = Number(m[3])
    return Math.floor(Date.UTC(year, month, day) / 1000)
  }
  const ms = Date.parse(ts)
  return Math.floor((Number.isNaN(ms) ? Date.now() : ms) / 1000)
}
export function buildEquityPoints(timestamps: string[], equity: number[]): EquityPoint[] {
  const points = timestamps
    .map((t, i) => ({ time: toUtcTimestamp(t), value: (equity[i] ?? NaN) as number }))
    .filter((p) => Number.isFinite(p.value) && Number.isFinite(p.time))
    .sort((a, b) => a.time - b.time)
  const dedup: EquityPoint[] = []
  let prev: number | undefined
  for (const p of points) {
    if (prev !== undefined && p.time <= prev) continue
    dedup.push(p)
    prev = p.time
  }
  return dedup
}
export function toLineData(points: EquityPoint[]): LinePoint[] {
  return points.map(p => ({ time: p.time, value: p.value }))
}