<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, watchEffect } from 'vue'
import { createChart, ColorType } from 'lightweight-charts'
import { TrendingUp, Activity, BarChart3, Clock } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { formatProcessingTime } from '@/utils/timeFormatter'
const { t } = useI18n()
type LinePoint = { time: number; value: number }
const props = defineProps<{ 
  series?: LinePoint[]
  processingTime?: string | null
}>()
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
const hasData = computed(() => (props.series?.length ?? 0) > 0)
const isPositiveTrend = computed(() => {
  const s = props.series ?? []
  if (!hasData.value || s.length < 2) return true
  const first = s[0]?.value
  const last = s[s.length - 1]?.value
  return (last ?? first ?? 0) >= (first ?? 0)
})
const pointCount = computed(() => props.series?.length ?? 0)
function setSeries(data?: LinePoint[]) {
  if (!lineSeries || !data) return
  lineSeries.setData(data)
}
onMounted(() => {
  if (!el.value) return
  const rootEl = el.value!
  const width = Math.max(320, rootEl.clientWidth || rootEl.getBoundingClientRect().width || 600)
  const textColor = '#e2e8f0'
  const gridColor = '#1e293b'
  rootEl.style.color = textColor
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
  if (!chart) return
  const lineColor = isPositiveTrend.value ? '#10b981' : '#ef4444'
  lineSeries = chart.addLineSeries({ 
    color: lineColor, 
    lineWidth: 3
  })
  setSeries(props.series)
  if (props.series && props.series.length > 0) {
    (chart as any).timeScale().fitContent()
  }
  loaded.value = true
  ro = new ResizeObserver(() => {
    if (rootEl && chart) {
      const w = Math.max(320, rootEl.clientWidth || rootEl.getBoundingClientRect().width || 600)
      chart.applyOptions({ width: w })
    }
  })
  ro.observe(rootEl)
})
onUnmounted(() => {
  chart?.remove()
  if (ro && el.value) ro.unobserve(el.value)
  chart = null
  lineSeries = null
})
watch(() => props.series, (data: LinePoint[] | undefined) => setSeries(data), { deep: true })
watchEffect(() => {
  if (lineSeries && props.series && props.series.length) {
    lineSeries.setData(props.series)
    if (chart && props.series.length > 0) {
      (chart as any).timeScale().fitContent()
    }
  }
})
</script>
<template>
  <div class="relative">
    <div class="flex items-center justify-between mb-4 px-2">
      <div class="flex items-center gap-3">
        <div class="rounded-xl bg-trading-blue/10 p-2 text-trading-blue">
          <BarChart3 class="size-4" />
        </div>
        <div>
          <h3 class="font-semibold text-sm">{{ t('simulate.chart.title') }}</h3>
          <p class="text-xs text-muted-foreground">{{ t('simulate.chart.subtitle') }}</p>
        </div>
      </div>
      <div v-if="hasData" class="flex items-center gap-2">
        <div :class="['rounded-full p-1.5', isPositiveTrend ? 'bg-trading-green/10 text-trading-green' : 'bg-trading-red/10 text-trading-red']">
          <TrendingUp v-if="isPositiveTrend" class="size-3" />
          <Activity v-else class="size-3" />
        </div>
        <span :class="['text-xs font-medium', isPositiveTrend ? 'text-trading-green' : 'text-trading-red']">
          {{ isPositiveTrend ? t('simulate.chart.trend.positive') : t('simulate.chart.trend.negative') }}
        </span>
        <div v-if="processingTime" class="flex items-center gap-1.5 ml-3 px-2 py-1 bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-full border border-blue-500/20">
          <Clock class="size-3 text-blue-400" />
          <span class="text-xs font-medium text-blue-400 tabular-nums">
            {{ formatProcessingTime(processingTime) }}
          </span>
        </div>
      </div>
    </div>
    <div class="relative overflow-hidden rounded-xl">
      <div v-if="!loaded" class="absolute inset-0 bg-gradient-to-r from-secondary/30 via-secondary/50 to-secondary/30 animate-pulse rounded-xl">
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-pulse" style="animation-delay: 0.5s;"></div>
      </div>
      <div
        ref="el"
        class="w-full h-[400px] rounded-xl transition-all duration-500 relative z-10"
        :class="loaded ? 'opacity-100' : 'opacity-0'"
        :style="{ pointerEvents: hasData ? 'auto' : 'none' }"
      />
      <div v-if="loaded && !hasData" class="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-secondary/20 to-accent/10 rounded-xl">
        <div class="text-center space-y-3">
          <div class="rounded-full bg-muted/20 p-4 mx-auto w-fit">
            <BarChart3 class="size-8 text-muted-foreground" />
          </div>
          <div>
            <p class="font-medium text-muted-foreground">{{ t('simulate.chart.empty.title') }}</p>
            <p class="text-xs text-muted-foreground/70">{{ t('simulate.chart.empty.subtitle') }}</p>
          </div>
        </div>
      </div>
    </div>
    <div class="flex items-center justify-between mt-4 px-2">
      <div class="text-xs text-muted-foreground flex items-center gap-2">
        <div class="w-2 h-2 rounded-full bg-trading-blue"></div>
        {{ t('simulate.chart.legend') }}
      </div>
      <div v-if="hasData" class="text-xs text-muted-foreground">
        {{ pointCount }} points de données
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
:global(.tv-lightweight-charts .pane) {
  border-radius: 0.75rem;
}
</style>