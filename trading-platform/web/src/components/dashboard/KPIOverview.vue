<script setup lang="ts">
import { computed } from 'vue'
import { useSimulationStore } from '@/stores/simulation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const store = useSimulationStore()
store.init()

const balance = computed(() => store.balance)
const unrealized = computed(() => store.unrealizedPnl)
const closed = computed(() => store.closedPnl)
const openQty = computed(() => store.openPositionQty)
const avgEntry = computed(() => store.avgEntryPrice)
</script>

<template>
  <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <Card>
      <CardHeader>
        <CardTitle>Account Balance</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="text-2xl font-semibold tabular-nums">{{ balance.toLocaleString(undefined,{maximumFractionDigits:0}) }} USD</div>
      </CardContent>
    </Card>
    <Card>
      <CardHeader>
        <CardTitle>Unrealized P&amp;L</CardTitle>
      </CardHeader>
      <CardContent>
        <div :class="['text-2xl font-semibold tabular-nums', unrealized>=0 ? 'text-emerald-600' : 'text-red-600']">{{ unrealized.toLocaleString(undefined,{maximumFractionDigits:2}) }} USD</div>
      </CardContent>
    </Card>
    <Card>
      <CardHeader>
        <CardTitle>Closed P&amp;L</CardTitle>
      </CardHeader>
      <CardContent>
        <div :class="['text-2xl font-semibold tabular-nums', closed>=0 ? 'text-emerald-600' : 'text-red-600']">{{ closed.toLocaleString(undefined,{maximumFractionDigits:2}) }} USD</div>
      </CardContent>
    </Card>
    <Card>
      <CardHeader>
        <CardTitle>Open Position / Avg Entry</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="text-2xl font-semibold tabular-nums">{{ openQty }}</div>
        <div class="text-sm text-muted-foreground">Avg {{ avgEntry.toFixed(2) }}</div>
      </CardContent>
    </Card>
  </div>
</template>