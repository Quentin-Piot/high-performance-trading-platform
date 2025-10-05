<script setup lang="ts">
import BacktestForm from '@/components/backtest/BacktestForm.vue'
import BacktestChart from '@/components/backtest/BacktestChart.vue'
import MetricsCard from '@/components/common/MetricsCard.vue'
import { useBacktestStore } from '@/stores/backtestStore'
import { computed } from 'vue'

const store = useBacktestStore()
const loading = computed(() => store.status === 'loading')
</script>

<template>
  <main class="container mx-auto p-6 space-y-4">
    <header class="space-y-2">
      <h1 class="text-xl font-semibold">Backtest Simulation</h1>
      <p class="text-sm text-muted-foreground">Upload a CSV and run an SMA backtest.</p>
    </header>
    <section class="grid gap-6 lg:grid-cols-3">
      <div class="lg:col-span-1">
        <div class="rounded-md border p-4">
          <h2 class="text-base font-medium mb-3">Strategy Form</h2>
          <BacktestForm />
        </div>
      </div>
      <div class="lg:col-span-2 space-y-3">
        <div v-if="store.error" class="rounded-md border border-red-300 bg-red-50 text-red-700 p-3">
          {{ store.error }}
        </div>
        <div class="rounded-md border p-4">
          <h2 class="text-base font-medium mb-3">Results</h2>
          <div v-if="loading" class="h-[360px] w-full animate-pulse rounded-md bg-muted"></div>
          <BacktestChart v-else :timestamps="store.timestamps" :equity_curve="store.equityCurve" />
        </div>
        <div class="grid grid-cols-3 gap-3">
          <MetricsCard label="P&L" :value="store.pnl" percentage />
          <MetricsCard label="Max Drawdown" :value="store.drawdown" percentage />
          <MetricsCard label="Sharpe Ratio" :value="store.sharpe" />
        </div>
      </div>
    </section>
  </main>
 </template>