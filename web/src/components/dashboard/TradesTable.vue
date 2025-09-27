<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSimulationStore } from '@/stores/simulation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select'

const store = useSimulationStore()

const sideFilter = ref<'ALL' | 'BUY' | 'SELL'>('ALL')
const assetFilter = ref<string>('ALL')
const fromDate = ref<string>('')
const toDate = ref<string>('')

const assets = [
  { label: 'All', value: 'ALL' },
  { label: 'QUTE', value: 'QUTE' },
  { label: 'INDEXX', value: 'INDEXX' },
  { label: 'ALPHA', value: 'ALPHA' },
]

const rows = computed(() => store.trades)
const filteredRows = computed(() => {
  const from = fromDate.value ? new Date(fromDate.value).getTime() : -Infinity
  const to = toDate.value ? new Date(toDate.value).getTime() : Infinity
  return rows.value.filter(t => {
    if (sideFilter.value !== 'ALL' && t.side !== sideFilter.value) return false
    if (assetFilter.value !== 'ALL' && t.symbol !== assetFilter.value) return false
    if (t.time < from || t.time > to) return false
    return true
  })
})
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Transaction History</CardTitle>
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground">Side</span>
            <Select :model-value="sideFilter" @update:model-value="v => sideFilter = v as any">
              <SelectTrigger class="w-28">
                <SelectValue :placeholder="sideFilter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All</SelectItem>
                <SelectItem value="BUY">BUY</SelectItem>
                <SelectItem value="SELL">SELL</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground">Asset</span>
            <Select :model-value="assetFilter" @update:model-value="v => assetFilter = String(v)">
              <SelectTrigger class="w-36">
                <SelectValue :placeholder="assetFilter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="a in assets" :key="a.value" :value="a.value">{{ a.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground">From</span>
            <input v-model="fromDate" type="date" class="h-8 w-36 rounded-md border px-2 text-xs bg-background" />
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground">To</span>
            <input v-model="toDate" type="date" class="h-8 w-36 rounded-md border px-2 text-xs bg-background" />
          </div>
        </div>
      </div>
    </CardHeader>
    <CardContent>
      <div class="rounded-md border overflow-hidden">
        <div class="grid grid-cols-6 bg-muted/50 text-xs font-medium uppercase tracking-wide">
          <div class="px-3 py-2">Time</div>
          <div class="px-3 py-2">Symbol</div>
          <div class="px-3 py-2">Side</div>
          <div class="px-3 py-2 text-right">Price</div>
          <div class="px-3 py-2 text-right">Qty</div>
          <div class="px-3 py-2 text-right">Balance</div>
        </div>
        <div class="max-h-60 overflow-auto">
          <div v-for="t in filteredRows" :key="t.id" class="grid grid-cols-6 border-t text-sm hover:bg-muted/30">
            <div class="px-3 py-2 tabular-nums text-muted-foreground">{{ new Date(t.time).toLocaleTimeString() }}</div>
            <div class="px-3 py-2">{{ t.symbol }}</div>
            <div class="px-3 py-2">
              <span :class="[
                'inline-flex items-center rounded px-2 py-0.5 text-xs font-medium',
                t.side === 'BUY' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300' : 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300'
              ]">{{ t.side }}</span>
            </div>
            <div class="px-3 py-2 text-right tabular-nums">{{ t.price.toFixed(2) }}</div>
            <div class="px-3 py-2 text-right tabular-nums">{{ t.qty }}</div>
            <div class="px-3 py-2 text-right tabular-nums">{{ t.balanceAfter?.toLocaleString(undefined,{maximumFractionDigits:0}) ?? '-' }}</div>
          </div>
          <div v-if="filteredRows.length===0" class="py-6 text-center text-muted-foreground text-sm">No trades match your filters.</div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>