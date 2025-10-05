<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { createChart, type ISeriesApi, type LineData, type Time, ColorType } from 'lightweight-charts'

const props = defineProps<{ timestamps: string[]; equity_curve: number[] }>()

const el = ref<HTMLDivElement | null>(null)
let series: ISeriesApi<'Line'> | null = null
let chart: ReturnType<typeof createChart> | null = null

function parseToTime(s: string): Time {
  const m = s.match(/^([0-9]{4})-([0-9]{2})-([0-9]{2})(?:$|T)/)
  if (m) {
    const year = Number(m[1])
    const month = Number(m[2]) - 1
    const day = Number(m[3])
    const ts = Math.floor(Date.UTC(year, month, day) / 1000)
    return ts as unknown as Time
  }
  const ms = Date.parse(s)
  if (!Number.isNaN(ms)) return Math.floor(ms / 1000) as unknown as Time
  return Math.floor(Date.now() / 1000) as unknown as Time
}

function setData(times?: string[], values?: number[]) {
  if (!series || !times || !values) return

  const zipped = times
    .map((t: string, i) => {
      const v = values[i]
      if (v === undefined || v === null) return null
      const time = parseToTime(t) as unknown as number
      if (Number.isNaN(time)) return null
      return { time, value: v }
    })
    .filter((d): d is { time: number; value: number } => d !== null)
    .sort((a, b) => a.time - b.time)

  const dedup: LineData<Time>[] = []
  let prev: number | undefined
  for (const p of zipped) {
    if (prev !== undefined && p.time <= prev) continue
    dedup.push({ time: p.time as unknown as Time, value: p.value })
    prev = p.time
  }

  series.setData(dedup)
}

onMounted(() => {
  if (!el.value) return
  chart = createChart(el.value, {
    layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#cbd5e1' },
    width: el.value.clientWidth,
    height: 360,
    rightPriceScale: { borderVisible: false },
    timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
    grid: { vertLines: { color: '#0b1220' }, horzLines: { color: '#0b1220' }},
  })
  series = chart.addLineSeries({ color: '#10b981', lineWidth: 2 })
  setData(props.timestamps, props.equity_curve)
})

onUnmounted(() => {
  chart?.remove()
  chart = null
  series = null
})

// Observe changes on timestamps and equity_curve without tuple type issues
watch([() => props.timestamps, () => props.equity_curve], () => {
  setData(props.timestamps, props.equity_curve)
})
</script>

<template>
  <div>
    <div ref="el" class="w-full h-[360px] rounded-md border" />
    <div class="text-xs text-muted-foreground text-center mt-2">Axe X : Date / Axe Y : Equity Curve</div>
  </div>
</template>
