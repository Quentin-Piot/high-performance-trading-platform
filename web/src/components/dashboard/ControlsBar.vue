<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button } from '@/components/ui/button'
import { useSimulationStore } from '@/stores/simulation'
import { Loader2, RotateCcw } from 'lucide-vue-next'
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select'

const store = useSimulationStore()

const running = computed(() => store.running)
const initialBalanceLocal = ref(String(store.params.initialBalance ?? 100000))

function toggleRun() {
  if (running.value) store.stop()
  else store.start()
}
function buy(){ store.triggerTrade('BUY', 1) }
function sell(){ store.triggerTrade('SELL', 1) }
function reset(){ store.reset() }
function applyBalance(){
  const n = Number(initialBalanceLocal.value)
  if (!Number.isNaN(n) && n >= 0) store.setInitialBalance(n)
}

const assets = [
  { label: 'QUTE', value: 'QUTE' },
  { label: 'INDEXX', value: 'INDEXX' },
  { label: 'ALPHA', value: 'ALPHA' },
]
</script>

<template>
  <div class="flex flex-wrap items-center gap-3">
    <Button :variant="running ? 'destructive' : undefined" @click="toggleRun">
      <Loader2 v-if="running" class="mr-2 size-4 animate-spin" />
      {{ running ? 'Arrêter' : 'Démarrer' }} la simulation
    </Button>

    <span
      :class="[
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium',
        running ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-300'
      ]"
      aria-live="polite"
    >
      <span :class="['size-1.5 rounded-full', running ? 'bg-emerald-500 animate-pulse' : 'bg-gray-400']"></span>
      {{ running ? 'En cours' : 'À l\'arrêt' }}
    </span>

    <div class="hidden sm:flex items-center gap-2 ml-auto">
      <span class="text-sm text-muted-foreground">Solde initial</span>
      <input v-model="initialBalanceLocal" type="number" class="h-9 w-28 rounded-md border px-2 text-sm bg-background" @change="applyBalance" />
    </div>

    <div class="flex items-center gap-2">
      <span class="text-sm text-muted-foreground">Actif</span>
      <Select :model-value="store.params.symbol" @update:model-value="v => store.setParams({ symbol: String(v) })">
        <SelectTrigger class="w-36">
          <SelectValue :placeholder="store.params.symbol" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="a in assets" :key="a.value" :value="a.value">{{ a.label }}</SelectItem>
        </SelectContent>
      </Select>
    </div>

    <div class="flex items-center gap-2">
      <Button variant="secondary" @click="reset"><RotateCcw class="mr-2 size-4"/>Réinitialiser</Button>
      <Button variant="outline" @click="buy">Buy 1</Button>
      <Button variant="outline" @click="sell">Sell 1</Button>
    </div>
  </div>
</template>