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
import { RefreshCw, Download } from 'lucide-vue-next'
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
  <main class="container mx-auto px-6 py-10 space-y-10">
    <TopNav />
    <!-- Header -->
    <header class="flex flex-col gap-1">
      <h1 class="text-2xl font-semibold tracking-tight">{{ t('simulate.header.title') }}</h1>
      <p class="text-sm text-muted-foreground">{{ t('simulate.header.subtitle') }}</p>
    </header>

    <!-- Layout: left form, right chart -->
    <section class="grid gap-6 lg:grid-cols-3">
      <!-- Form panel -->
      <Card class="lg:col-span-1">
        <CardHeader>
          <CardTitle>{{ t('simulate.form.title') }}</CardTitle>
        </CardHeader>
        <CardContent>
          <BacktestForm />
        </CardContent>
      </Card>

      <!-- Chart panel -->
      <div class="lg:col-span-2 space-y-4">
        <!-- Error banner -->
        <div v-if="store.status==='error'" class="rounded-md border bg-destructive/10 text-destructive p-3">
          {{ t('simulate.errors.backtest') }}
        </div>

        <!-- Chart card and toolbar -->
        <Card>
          <CardHeader class="flex items-center justify-between gap-3">
            <div class="space-y-1">
              <CardTitle>{{ t('simulate.results.title') }}</CardTitle>
              <p class="text-xs text-muted-foreground">{{ t('simulate.header.subtitle') }}</p>
            </div>
            <!-- Toolbar type TradingView (UI only) -->
            <div class="flex flex-wrap items-center gap-2">
              <Select v-model="selectedResolution">
                <SelectTrigger class="w-28">
                  <SelectValue :placeholder="selectedResolution" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1m">1m</SelectItem>
                  <SelectItem value="5m">5m</SelectItem>
                  <SelectItem value="1h">1h</SelectItem>
                  <SelectItem value="1d">1d</SelectItem>
                </SelectContent>
              </Select>
              <div class="hidden sm:flex items-center gap-1">
                <Button size="sm" variant="outline" :class="activeRange==='1W' ? 'bg-muted' : ''" @click="activeRange='1W'">1W</Button>
                <Button size="sm" variant="outline" :class="activeRange==='1M' ? 'bg-muted' : ''" @click="activeRange='1M'">1M</Button>
                <Button size="sm" variant="outline" :class="activeRange==='YTD' ? 'bg-muted' : ''" @click="activeRange='YTD'">YTD</Button>
                <Button size="sm" variant="outline" :class="activeRange==='All' ? 'bg-muted' : ''" @click="activeRange='All'">All</Button>
              </div>
              <div class="flex items-center gap-1">
                <Button size="sm" variant="ghost" class="hover:bg-muted" @click="store.retryLast()"><RefreshCw class="size-4" /></Button>
                <Button size="sm" variant="ghost" class="hover:bg-muted" @click="downloadCsv"><Download class="size-4" /></Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div v-if="loading" class="h-[360px] w-full animate-pulse rounded-md bg-muted"></div>
            <BacktestChart v-else :series="chartSeries" />
          </CardContent>
        </Card>

        <!-- KPI grid -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <MetricsCard :label="t('simulate.metrics.pnl')" :value="store.pnl" percentage />
          <MetricsCard :label="t('simulate.metrics.drawdown')" :value="store.drawdown" percentage />
          <MetricsCard :label="t('simulate.metrics.sharpe')" :value="store.sharpe" />
        </div>
      </div>
    </section>
  </main>
</template>