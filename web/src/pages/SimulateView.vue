<script setup lang="ts">
import BacktestForm from '@/components/backtest/BacktestForm.vue'
import BacktestChart from '@/components/backtest/BacktestChart.vue'
import MetricsCard from '@/components/common/MetricsCard.vue'
import { useBacktestStore } from '@/stores/backtestStore'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { RefreshCw, Download, BarChart3, LineChart } from 'lucide-vue-next'
import TopNav from '@/components/common/TopNav.vue'
// Local chart types avoiding dependency on lightweight-charts TS exports
type BusinessDay = { year: number; month: number; day: number }
type ChartTime = number | BusinessDay
type ChartPoint = { time: ChartTime; value: number }
type LinePoint = { time: number; value: number }

const store = useBacktestStore()
const loading = computed(() => store.status === 'loading')
const { t } = useI18n()
// Toolbar state and helpers
const selectedResolution = ref<'1m' | '5m' | '1h' | '1d'>('1d')
const activeRange = ref<'1W' | '1M' | 'YTD' | 'All'>('All')

type EquitySeries = ChartPoint[]

function timeToSeconds(p: ChartPoint): number {
  if (typeof p.time === 'number') return p.time
  const bd = p.time as BusinessDay
  if (bd && typeof bd.year === 'number' && typeof bd.month === 'number' && typeof bd.day === 'number') {
    return Math.floor(Date.UTC(bd.year, bd.month - 1, bd.day) / 1000)
  }
  return Number(p.time) || 0
}

function downsample(series: EquitySeries, resolution: '1m' | '5m' | '1h' | '1d'): EquitySeries {
  const stepMap: Record<'1m' | '5m' | '1h' | '1d', number> = { '1m': 60, '5m': 300, '1h': 3600, '1d': 86400 }
  const step = stepMap[resolution]
  const out: EquitySeries = []
  let bucketStart: number | null = null
  for (const p of series) {
    const t = timeToSeconds(p)
    if (!Number.isFinite(t)) continue
    if (bucketStart === null) bucketStart = t
    const inBucket = t < bucketStart + step
    if (!inBucket) {
      bucketStart = t
      out.push(p)
    } else if (out.length === 0) {
      out.push(p)
    } else {
      out[out.length - 1] = p
    }
  }
  return out
}

function applyRange(series: EquitySeries, range: '1W' | '1M' | 'YTD' | 'All'): EquitySeries {
  if (range === 'All' || series.length === 0) return series
  const times = series.map(s => timeToSeconds(s)).filter(Number.isFinite)
  const maxTime = Math.max(...times)
  let cutoff = maxTime
  if (range === '1W') cutoff = maxTime - 7 * 86400
  else if (range === '1M') cutoff = maxTime - 30 * 86400
  else if (range === 'YTD') {
    const d = new Date(maxTime * 1000)
    const jan1 = Date.UTC(d.getUTCFullYear(), 0, 1) / 1000
    cutoff = jan1
  }
  return series.filter(s => timeToSeconds(s) >= cutoff)
}

const displaySeries = computed<EquitySeries>(() => {
  const base: EquitySeries = store.equitySeries || []
  const ranged = applyRange(base, activeRange.value)
  return downsample(ranged, selectedResolution.value)
})

const chartSeries = computed<LinePoint[]>(() => displaySeries.value.map(p => ({ time: timeToSeconds(p), value: p.value })))

function downloadCsv() {
  const rows = [['time','value'], ...displaySeries.value.map((p) => [String(timeToSeconds(p)), String(p.value)])]
  const csv = rows.map(r => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'equity_series.csv'
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <main class="container mx-auto px-6 py-10 space-y-10 animate-fade-in">
    <TopNav />
    
    <!-- Header avec effet premium -->
    <header class="flex flex-col gap-2 animate-slide-up">
      <h1 class="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary via-trading-purple to-trading-cyan bg-clip-text text-transparent">
        {{ t('simulate.header.title') }}
      </h1>
      <p class="text-base text-muted-foreground">{{ t('simulate.header.subtitle') }}</p>
    </header>

    <!-- Layout: left form, right chart -->
    <section class="grid gap-8 lg:grid-cols-3 animate-scale-in" style="animation-delay: 0.2s;">
      <!-- Form panel avec design moderne -->
      <Card class="lg:col-span-1 border-0 shadow-medium bg-gradient-to-br from-card via-card to-secondary/20">
        <CardHeader class="pb-4">
          <CardTitle class="flex items-center gap-3 text-xl">
            <div class="rounded-xl bg-trading-blue/10 p-2 text-trading-blue">
              <BarChart3 class="size-5" />
            </div>
            {{ t('simulate.form.title') }}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <BacktestForm />
        </CardContent>
      </Card>

      <!-- Chart panel avec interface TradingView -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Error banner avec style moderne -->
        <div v-if="store.status==='error'" class="rounded-xl border border-trading-red/20 bg-trading-red/5 text-trading-red p-4 shadow-soft animate-slide-up">
          <div class="flex items-center gap-3">
            <div class="rounded-full bg-trading-red/10 p-2">
              <RefreshCw class="size-4" />
            </div>
            <span class="font-medium">{{ t('simulate.errors.backtest') }}</span>
          </div>
        </div>

        <!-- Chart card avec toolbar TradingView style -->
        <Card class="border-0 shadow-strong bg-gradient-to-br from-card via-card to-secondary/10 overflow-hidden">
          <CardHeader class="flex items-center justify-between gap-4 pb-4">
            <div class="space-y-1">
              <CardTitle class="flex items-center gap-3 text-xl">
                <div class="rounded-xl bg-trading-green/10 p-2 text-trading-green">
                  <LineChart class="size-5" />
                </div>
                {{ t('simulate.results.title') }}
              </CardTitle>
              <p class="text-sm text-muted-foreground">{{ t('simulate.header.subtitle') }}</p>
            </div>
            
            <!-- Toolbar type TradingView avec design premium -->
            <div class="flex flex-wrap items-center gap-3">
              <!-- Sélecteur de résolution avec style moderne -->
              <div class="flex items-center gap-2">
                <Select v-model="selectedResolution">
                  <SelectTrigger class="w-32 border-0 bg-secondary/50 hover:bg-secondary/70 transition-smooth shadow-soft">
                    <SelectValue :placeholder="t('simulate.chart.resolution.' + selectedResolution)" />
                  </SelectTrigger>
                  <SelectContent class="border-0 shadow-strong">
                    <SelectItem value="1m" class="hover:bg-trading-blue/10">{{ t('simulate.chart.resolution.1m') }}</SelectItem>
                    <SelectItem value="5m" class="hover:bg-trading-blue/10">{{ t('simulate.chart.resolution.5m') }}</SelectItem>
                    <SelectItem value="1h" class="hover:bg-trading-blue/10">{{ t('simulate.chart.resolution.1h') }}</SelectItem>
                    <SelectItem value="1d" class="hover:bg-trading-blue/10">{{ t('simulate.chart.resolution.1d') }}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <!-- Boutons de plage temporelle avec style TradingView -->
              <div class="hidden sm:flex items-center gap-1 bg-secondary/30 rounded-xl p-1">
                <Button 
                  size="sm" 
                  variant="ghost" 
                  :class="[
                    'rounded-lg transition-smooth font-medium',
                    activeRange==='1W' ? 'bg-trading-blue text-white shadow-soft' : 'hover:bg-secondary/50'
                  ]" 
                  @click="activeRange='1W'"
                >
                  {{ t('simulate.chart.range.1W') }}
                </Button>
                <Button 
                  size="sm" 
                  variant="ghost" 
                  :class="[
                    'rounded-lg transition-smooth font-medium',
                    activeRange==='1M' ? 'bg-trading-blue text-white shadow-soft' : 'hover:bg-secondary/50'
                  ]" 
                  @click="activeRange='1M'"
                >
                  {{ t('simulate.chart.range.1M') }}
                </Button>
                <Button 
                  size="sm" 
                  variant="ghost" 
                  :class="[
                    'rounded-lg transition-smooth font-medium',
                    activeRange==='YTD' ? 'bg-trading-blue text-white shadow-soft' : 'hover:bg-secondary/50'
                  ]" 
                  @click="activeRange='YTD'"
                >
                  {{ t('simulate.chart.range.YTD') }}
                </Button>
                <Button 
                  size="sm" 
                  variant="ghost" 
                  :class="[
                    'rounded-lg transition-smooth font-medium',
                    activeRange==='All' ? 'bg-trading-blue text-white shadow-soft' : 'hover:bg-secondary/50'
                  ]" 
                  @click="activeRange='All'"
                >
                  {{ t('simulate.chart.range.All') }}
                </Button>
              </div>
              
              <!-- Actions avec effets visuels -->
              <div class="flex items-center gap-2">
                <Button 
                  size="sm" 
                  variant="ghost" 
                  class="rounded-xl hover:bg-trading-green/10 hover:text-trading-green transition-smooth shadow-soft hover-scale" 
                  @click="store.retryLast()"
                >
                  <RefreshCw class="size-4" />
                </Button>
                <Button 
                  size="sm" 
                  variant="ghost" 
                  class="rounded-xl hover:bg-trading-purple/10 hover:text-trading-purple transition-smooth shadow-soft hover-scale" 
                  @click="downloadCsv"
                >
                  <Download class="size-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          
          <CardContent class="p-0">
            <div v-if="loading" class="h-[400px] w-full relative overflow-hidden">
              <!-- Skeleton avec animation moderne -->
              <div class="absolute inset-0 bg-gradient-to-r from-secondary/30 via-secondary/50 to-secondary/30 animate-pulse"></div>
              <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-pulse" style="animation-delay: 0.5s;"></div>
            </div>
            <div v-else class="p-6">
              <BacktestChart :series="chartSeries" />
            </div>
          </CardContent>
        </Card>

        <!-- KPI grid avec design premium -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-slide-up" style="animation-delay: 0.4s;">
          <div class="relative overflow-hidden rounded-xl border-0 shadow-medium bg-gradient-to-br from-card to-trading-green/5 transition-smooth">
            <div class="absolute top-0 right-0 w-20 h-20 bg-trading-green/10 rounded-full -translate-y-10 translate-x-10"></div>
            <MetricsCard :label="t('simulate.metrics.pnl')" :value="store.pnl" percentage class="relative z-10 bg-transparent border-0 shadow-none" />
          </div>
          
          <div class="relative overflow-hidden rounded-xl border-0 shadow-medium bg-gradient-to-br from-card to-trading-red/5 transition-smooth">
            <div class="absolute top-0 right-0 w-20 h-20 bg-trading-red/10 rounded-full -translate-y-10 translate-x-10"></div>
            <MetricsCard :label="t('simulate.metrics.drawdown')" :value="store.drawdown" percentage class="relative z-10 bg-transparent border-0 shadow-none" />
          </div>
          
          <div class="relative overflow-hidden rounded-xl border-0 shadow-medium bg-gradient-to-br from-card to-trading-blue/5 transition-smooth">
            <div class="absolute top-0 right-0 w-20 h-20 bg-trading-blue/10 rounded-full -translate-y-10 translate-x-10"></div>
            <MetricsCard :label="t('simulate.metrics.sharpe')" :value="store.sharpe" class="relative z-10 bg-transparent border-0 shadow-none" />
          </div>
        </div>
      </div>
    </section>
  </main>
</template>