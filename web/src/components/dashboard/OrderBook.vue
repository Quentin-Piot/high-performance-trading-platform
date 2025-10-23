<script setup lang="ts">
import { computed } from 'vue'
import { useSimulationStore } from '@/stores/simulation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
const store = useSimulationStore()
const ob = computed(() => store.snapshot?.orderBook)
</script>
<template>
  <Card>
    <CardHeader>
      <CardTitle>Order Book</CardTitle>
    </CardHeader>
    <CardContent>
      <div v-if="ob" class="grid grid-cols-2 gap-4">
        <div>
          <div class="mb-1 text-xs text-muted-foreground">Bids</div>
          <div class="space-y-1">
            <div v-for="(b, i) in ob!.bids" :key="'b'+i" class="flex items-center justify-between rounded bg-emerald-500/10 px-2 py-1 text-sm">
              <span class="tabular-nums text-emerald-600">{{ b.price.toFixed(2) }}</span>
              <span class="tabular-nums text-muted-foreground">{{ b.qty }}</span>
            </div>
          </div>
        </div>
        <div>
          <div class="mb-1 text-xs text-muted-foreground">Asks</div>
          <div class="space-y-1">
            <div v-for="(a, i) in ob!.asks" :key="'a'+i" class="flex items-center justify-between rounded bg-red-500/10 px-2 py-1 text-sm">
              <span class="tabular-nums text-red-600">{{ a.price.toFixed(2) }}</span>
              <span class="tabular-nums text-muted-foreground">{{ a.qty }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-sm text-muted-foreground">No order book data.</div>
    </CardContent>
  </Card>
</template>