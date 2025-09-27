<script setup lang="ts">
import KPIOverview from '@/components/dashboard/KPIOverview.vue'
import PriceChart from '@/components/dashboard/PriceChart.vue'
import ControlsBar from '@/components/dashboard/ControlsBar.vue'
import FiltersBar from '@/components/dashboard/FiltersBar.vue'
import TradesTable from '@/components/dashboard/TradesTable.vue'
import PerformancePanel from '@/components/dashboard/PerformancePanel.vue'
import OrderBook from '@/components/dashboard/OrderBook.vue'
import { useSimulationStore } from '@/stores/simulation'

const store = useSimulationStore()
store.init()
</script>

<template>
  <main class="container mx-auto p-4 space-y-4">
    <header class="space-y-2">
      <h1 class="text-xl font-semibold">Trading Simulation</h1>
      <p class="text-sm text-muted-foreground">Real-time simulated market with adjustable parameters.</p>
    </header>

    <section class="flex flex-col gap-3">
      <FiltersBar />
      <ControlsBar />
    </section>

    <section class="grid gap-4 lg:grid-cols-3">
      <div class="lg:col-span-2"><PriceChart /></div>
      <OrderBook />
    </section>

    <section class="grid gap-4">
      <KPIOverview />
    </section>
   <section>
      <PerformancePanel />
    </section>
    <section>
      <TradesTable />
    </section>
  </main>
</template>