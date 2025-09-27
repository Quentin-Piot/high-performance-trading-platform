<script setup lang="ts">
import { Select } from '@/components/ui/select'
import { SelectTrigger } from '@/components/ui/select'
import { SelectContent } from '@/components/ui/select'
import { SelectItem } from '@/components/ui/select'
import { SelectValue } from '@/components/ui/select'
import { useSimulationStore } from '@/stores/simulation'

const store = useSimulationStore()

const intervals = [500, 1000, 2000, 5000]
const assets = [
  { label: 'QUTE', value: 'QUTE' },
  { label: 'INDEXX', value: 'INDEXX' },
  { label: 'ALPHA', value: 'ALPHA' },
]
</script>

<template>
  <div class="flex flex-wrap items-center gap-4">
    <div class="flex items-center gap-2">
      <span class="text-sm text-muted-foreground">Interval</span>
      <Select :model-value="String(store.params.intervalMs)" @update:model-value="v => store.setParams({ intervalMs: Number(v) })">
        <SelectTrigger class="w-36">
          <SelectValue :placeholder="store.params.intervalMs + ' ms'" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="i in intervals" :key="i" :value="String(i)">{{ i }} ms</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div class="flex items-center gap-2">
      <span class="text-sm text-muted-foreground">Asset</span>
      <Select :model-value="store.params.symbol" @update:model-value="v => store.setParams({ symbol: String(v) })">
        <SelectTrigger class="w-36">
          <SelectValue :placeholder="store.params.symbol" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="a in assets" :key="a.value" :value="a.value">{{ a.label }}</SelectItem>
        </SelectContent>
      </Select>
    </div>
  </div>
</template>