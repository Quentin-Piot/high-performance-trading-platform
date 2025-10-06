<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch, watchEffect } from 'vue'
import { createChart, ColorType } from 'lightweight-charts'

type LinePoint = { time: number; value: number }
const props = defineProps<{ series: LinePoint[] }>()

const el = ref<HTMLDivElement | null>(null)
type LineSeriesApi = { setData: (data: LinePoint[]) => void }
type ChartApi = {
  addLineSeries: (opts: { color: string; lineWidth: number }) => LineSeriesApi
  applyOptions: (opts: { width?: number }) => void
  remove: () => void
}
let lineSeries: LineSeriesApi | null = null
let chart: ChartApi | null = null
const loaded = ref(false)
let ro: ResizeObserver | null = null

function setSeries(data?: LinePoint[]) {
  if (!lineSeries || !data) return
  lineSeries.setData(data)
}

onMounted(() => {
  if (!el.value) return
  const width = Math.max(320, el.value.clientWidth || el.value.getBoundingClientRect().width || 600)
  // Forcer une couleur RGB sûre pour tout le conteneur et les widgets internes
  const textColor = '#cbd5e1'
  el.value.style.color = textColor
  chart = createChart(el.value, {
    layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor },
    width,
    height: 360,
    rightPriceScale: { borderVisible: false },
    timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
    grid: { vertLines: { color: '#0b1220' }, horzLines: { color: '#0b1220' }},
  })
  if (!chart) return
  lineSeries = chart.addLineSeries({ color: '#10b981', lineWidth: 2 })
  setSeries(props.series)
  loaded.value = true

  // Handle resize so chart always has width
  ro = new ResizeObserver(() => {
    if (el.value && chart) {
      const w = Math.max(320, el.value.clientWidth || el.value.getBoundingClientRect().width || 600)
      chart.applyOptions({ width: w })
    }
  })
  ro.observe(el.value)
})

onUnmounted(() => {
  chart?.remove()
  if (ro && el.value) ro.unobserve(el.value)
  chart = null
  lineSeries = null
})

// Observe changes to prebuilt series data
// React to data changes and also run once
watch(() => props.series, (data: LinePoint[]) => setSeries(data), { deep: true })
watchEffect(() => {
  if (lineSeries && props.series && props.series.length) {
    lineSeries.setData(props.series)
  }
})
</script>

<template>
  <div>
    <div
      ref="el"
      class="w-full h-[360px] rounded-md border transition-opacity duration-300"
      :class="loaded ? 'opacity-100' : 'opacity-0'"
    />
    <div class="text-xs text-muted-foreground text-center mt-2">Axe X : Date / Axe Y : Equity Curve</div>
  </div>
</template>

<style>
/* Empêche l’attribution de lightweight-charts d’hériter d’une couleur OKLCH */
:global(.tv-lightweight-charts) {
  color: #cbd5e1 !important;
}
</style>
