<script setup lang="ts">
// @ts-ignore - use runtime imports; types provided by tooling
import { onMounted, onUnmounted, ref, watch, watchEffect } from 'vue'
// @ts-ignore - rely on runtime, avoid type-only imports
import { createChart, ColorType } from 'lightweight-charts'

type LinePoint = { time: number; value: number }
const props = defineProps<{ series: LinePoint[] }>()

const el = ref<HTMLDivElement | null>(null)
let series: any = null
let chart: any = null

function setSeries(data?: LinePoint[]) {
  if (!series || !data) return
  series.setData(data)
}

function cssVar(name: string): string {
  const elRef = el.value
  const root = elRef ? getComputedStyle(elRef) : getComputedStyle(document.documentElement)
  return root.getPropertyValue(name).trim() || ''
}

function toRgbColor(input: string, fallback: string): string {
  if (!input) return fallback
  const lower = input.toLowerCase()
  // Lightweight Charts ne supporte pas oklch/oklab, forcer un fallback
  if (lower.includes('oklch') || lower.includes('oklab')) return fallback
  const tmp = document.createElement('span')
  tmp.style.color = input
  document.body.appendChild(tmp)
  const resolved = getComputedStyle(tmp).color
  document.body.removeChild(tmp)
  if (!resolved || resolved === '' || resolved.toLowerCase().includes('oklch') || resolved === input) {
    return fallback
  }
  return resolved
}

onMounted(() => {
  if (!el.value) return
  const width = Math.max(320, el.value.clientWidth || el.value.getBoundingClientRect().width || 600)
  const textColor = toRgbColor(cssVar('--muted-foreground'), '#cbd5e1')
  // Évite l'utilisation d'une couleur oklch par le widget d'attribution
  el.value.style.color = textColor
  chart = createChart(el.value, {
    layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor },
    width,
    height: 360,
    rightPriceScale: { borderVisible: false },
    timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
    grid: { vertLines: { color: toRgbColor(cssVar('--border'), '#0b1220') }, horzLines: { color: toRgbColor(cssVar('--border'), '#0b1220') }},
  })
  series = chart.addLineSeries({ color: toRgbColor(cssVar('--chart-1'), '#10b981'), lineWidth: 2 })
  setSeries(props.series)

  // Handle resize so chart always has width
  const ro = new ResizeObserver(() => {
    if (el.value && chart) {
      const w = Math.max(320, el.value.clientWidth || el.value.getBoundingClientRect().width || 600)
      chart.applyOptions({ width: w })
    }
  })
  ro.observe(el.value)
  ;(chart as any)._ro = ro
})

onUnmounted(() => {
  chart?.remove()
  // Cleanup resize listener if present
  const ro = (chart as any)?._ro as ResizeObserver | undefined
  if (ro && el.value) ro.unobserve(el.value)
  chart = null
  series = null
})

// Observe changes to prebuilt series data
// React to data changes and also run once
watch(() => props.series, (data: LinePoint[]) => setSeries(data), { deep: true })
watchEffect(() => {
  if (series && props.series && props.series.length) {
    series.setData(props.series)
  }
})
</script>

<template>
  <div>
    <div ref="el" class="w-full h-[360px] rounded-md border" />
    <div class="text-xs text-muted-foreground text-center mt-2">Axe X : Date / Axe Y : Equity Curve</div>
  </div>
</template>
