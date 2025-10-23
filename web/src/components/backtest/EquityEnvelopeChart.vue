<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { createChart, ColorType } from 'lightweight-charts'
import { BarChart3 } from 'lucide-vue-next'
interface EquityEnvelope {
  timestamps: string[]
  p5: number[]
  p25: number[]
  median: number[]
  p75: number[]
  p95: number[]
}
const props = defineProps<{
  equityEnvelope?: EquityEnvelope
  activeRange?: "1W" | "1M" | "YTD" | "All"
}>()
const el = ref<HTMLDivElement | null>(null)
let chart: any = null
let p5Series: any = null
let p25Series: any = null
let medianSeries: any = null
let p75Series: any = null
let p95Series: any = null
let ro: ResizeObserver | null = null
const hasData = computed(() => {
  return !!(props.equityEnvelope?.timestamps?.length && 
           props.equityEnvelope?.median?.length && 
           props.equityEnvelope?.p25?.length && 
           props.equityEnvelope?.p75?.length)
})
const pointCount = computed(() => props.equityEnvelope?.timestamps.length ?? 0)
function convertToChartData(timestamps: string[], values: number[]) {
  let data = timestamps.map((timestamp, index) => ({
    time: new Date(timestamp).getTime() / 1000, 
    value: values[index]
  }))
  if (props.activeRange && props.activeRange !== "All" && data.length > 0) {
    const times = data.map(d => d.time)
    const maxTime = Math.max(...times)
    let cutoff = maxTime
    if (props.activeRange === "1W") cutoff = maxTime - 7 * 86400
    else if (props.activeRange === "1M") cutoff = maxTime - 30 * 86400
    else if (props.activeRange === "YTD") {
      const d = new Date(maxTime * 1000)
      const jan1 = Date.UTC(d.getUTCFullYear(), 0, 1) / 1000
      cutoff = jan1
    }
    data = data.filter(d => d.time >= cutoff)
  }
  return data
}
function updateSeries() {
  if (!props.equityEnvelope || !chart) return
  const { timestamps, p5, p25, median, p75, p95 } = props.equityEnvelope
  const p5Data = convertToChartData(timestamps, p5)
  const p25Data = convertToChartData(timestamps, p25)
  const medianData = convertToChartData(timestamps, median)
  const p75Data = convertToChartData(timestamps, p75)
  const p95Data = convertToChartData(timestamps, p95)
  if (p5Series) p5Series.setData(p5Data)
  if (p25Series) p25Series.setData(p25Data)
  if (medianSeries) medianSeries.setData(medianData)
  if (p75Series) p75Series.setData(p75Data)
  if (p95Series) p95Series.setData(p95Data)
}
onMounted(() => {
  if (!el.value) return
  const rootEl = el.value
  const width = Math.max(320, rootEl.clientWidth || 600)
  const textColor = '#e2e8f0'
  const gridColor = '#1e293b'
  chart = createChart(rootEl, {
    layout: { 
      background: { type: ColorType.Solid, color: 'transparent' }, 
      textColor
    },
    width,
    height: 400,
    rightPriceScale: { 
      borderVisible: false
    },
    timeScale: { 
      borderVisible: false, 
      timeVisible: true, 
      secondsVisible: false
    },
    grid: { 
      vertLines: { color: gridColor }, 
      horzLines: { color: gridColor }
    }
  })
  p5Series = chart.addLineSeries({
    color: 'rgba(239, 68, 68, 0.6)',
    lineWidth: 1
  })
  p25Series = chart.addLineSeries({
    color: 'rgba(251, 146, 60, 0.8)',
    lineWidth: 2
  })
  medianSeries = chart.addLineSeries({
    color: '#10b981',
    lineWidth: 3
  })
  p75Series = chart.addLineSeries({
    color: 'rgba(34, 197, 94, 0.8)',
    lineWidth: 2
  })
  p95Series = chart.addLineSeries({
    color: 'rgba(16, 185, 129, 0.6)',
    lineWidth: 1
  })
  updateSeries()
  ro = new ResizeObserver(() => {
    if (rootEl && chart) {
      const w = Math.max(320, rootEl.clientWidth || 600)
      chart.applyOptions({ width: w })
    }
  })
  ro.observe(rootEl)
})
onUnmounted(() => {
  chart?.remove()
  if (ro && el.value) ro.unobserve(el.value)
  chart = null
  p5Series = null
  p25Series = null
  medianSeries = null
  p75Series = null
  p95Series = null
})
watch(() => props.equityEnvelope, updateSeries, { deep: true })
watch(() => props.activeRange, updateSeries)
</script>
<template>
  <div class="w-full">
    <!-- Header with chart info -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <BarChart3 class="h-5 w-5 text-primary" />
        <h3 class="text-lg font-semibold">Monte Carlo Equity Envelope</h3>
      </div>
      <div v-if="hasData" class="text-sm text-muted-foreground">
        {{ pointCount }} data points
      </div>
    </div>
    <!-- Chart container -->
    <div class="relative">
      <div 
        ref="el" 
        class="w-full h-[400px] rounded-lg border bg-card"
        :class="{ 'opacity-50': !hasData }"
      />
      <!-- No data overlay -->
      <div 
        v-if="!hasData" 
        class="absolute inset-0 flex items-center justify-center bg-muted/50 rounded-lg"
      >
        <div class="text-center text-muted-foreground">
          <BarChart3 class="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p class="text-sm">No Monte Carlo data available</p>
        </div>
      </div>
    </div>
    <!-- Legend -->
    <div v-if="hasData" class="mt-4 flex flex-wrap gap-4 text-xs">
      <div class="flex items-center gap-2">
        <div class="w-3 h-0.5 bg-red-400 opacity-60"></div>
        <span>5th Percentile</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-0.5 bg-orange-400 opacity-80"></div>
        <span>25th Percentile</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-0.5 bg-green-500"></div>
        <span>Median</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-0.5 bg-green-400 opacity-80"></div>
        <span>75th Percentile</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-0.5 bg-green-400 opacity-60"></div>
        <span>95th Percentile</span>
      </div>
    </div>
  </div>
</template>
<style>
:global(.tv-lightweight-charts) {
  color: #e2e8f0 !important;
  font-family: 'Inter', system-ui, sans-serif !important;
}
:global(.tv-lightweight-charts canvas) {
  border-radius: 0.75rem;
}
</style>