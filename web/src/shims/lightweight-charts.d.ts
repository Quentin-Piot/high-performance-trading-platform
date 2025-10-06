declare module 'lightweight-charts' {
  export type Time = number
  export interface LinePoint { time: Time; value: number }
  export interface LineSeriesApi { setData(data: LinePoint[]): void }
  export interface ChartApi {
    addLineSeries(opts: { color: string; lineWidth: number }): LineSeriesApi
    applyOptions(opts: { width?: number }): void
    remove(): void
  }

  // Minimal shape to support ColorType.Solid usage
  export const ColorType: { Solid: string }

  export function createChart(
    container: HTMLElement,
    options?: {
      layout?: { background?: { type: string; color?: string }, textColor?: string }
      width?: number
      height?: number
      rightPriceScale?: { borderVisible?: boolean }
      timeScale?: { borderVisible?: boolean; timeVisible?: boolean; secondsVisible?: boolean }
      grid?: { vertLines?: { color?: string }, horzLines?: { color?: string } }
    }
  ): ChartApi
}