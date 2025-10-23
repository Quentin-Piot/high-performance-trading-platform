<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useSimulationStore } from '@/stores/simulation'
const store = useSimulationStore()
const totalTrades = computed(() => store.trades.length)
const wins = computed(() => store.trades.filter(t => (t.realizedPnl ?? 0) > 0).length)
const winRate = computed(() => totalTrades.value ? Math.round((wins.value / totalTrades.value) * 100) : 0)
const latency = ref(0)
let timer: number | null = null
onMounted(() => {
  const update = () => { latency.value = Math.floor(5 + Math.random() * 20) }
  update()
  timer = setInterval(update, 1500) as unknown as number
})
onBeforeUnmount(() => { if (timer) clearInterval(timer as unknown as number) })
</script>
<template>
  <Card>
    <CardHeader>
      <CardTitle>Performance</CardTitle>
    </CardHeader>
    <CardContent>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <div class="text-xs text-muted-foreground">Total Trades</div>
          <div class="text-xl font-semibold tabular-nums">{{ totalTrades }}</div>
        </div>
        <div>
          <div class="text-xs text-muted-foreground">Win Rate</div>
          <div class="text-xl font-semibold">{{ winRate }}%</div>
        </div>
        <div>
          <div class="text-xs text-muted-foreground">Latency</div>
          <div class="text-xl font-semibold tabular-nums">{{ latency }} ms</div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>