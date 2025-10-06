<script setup lang="ts">
import BacktestForm from '@/components/backtest/BacktestForm.vue'
import BacktestChart from '@/components/backtest/BacktestChart.vue'
import MetricsCard from '@/components/common/MetricsCard.vue'
import { useBacktestStore } from '@/stores/backtestStore'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { RefreshCw, Download } from 'lucide-vue-next'
import TopNav from '@/components/common/TopNav.vue'

const store = useBacktestStore()
const loading = computed(() => store.status === 'loading')
const { t } = useI18n()
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
        <div v-if="store.error" class="rounded-md border bg-destructive/10 text-destructive p-3">
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
              <Select>
                <SelectTrigger class="w-28">
                  <SelectValue placeholder="Timeframe" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1m">1m</SelectItem>
                  <SelectItem value="5m">5m</SelectItem>
                  <SelectItem value="1h">1h</SelectItem>
                  <SelectItem value="1d">1d</SelectItem>
                </SelectContent>
              </Select>
              <div class="hidden sm:flex items-center gap-1">
                <Button size="sm" variant="outline">1W</Button>
                <Button size="sm" variant="outline">1M</Button>
                <Button size="sm" variant="outline">YTD</Button>
                <Button size="sm" variant="outline">All</Button>
              </div>
              <div class="flex items-center gap-1">
                <Button size="sm" variant="ghost" class="hover:bg-muted"><RefreshCw class="size-4" /></Button>
                <Button size="sm" variant="ghost" class="hover:bg-muted"><Download class="size-4" /></Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div v-if="loading" class="h-[360px] w-full animate-pulse rounded-md bg-muted"></div>
            <BacktestChart v-else :series="store.equitySeries" />
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