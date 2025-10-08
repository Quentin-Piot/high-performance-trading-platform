<script setup lang="ts">
import { ref, computed } from 'vue'
import { useBacktestStore } from '@/stores/backtestStore'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

const store = useBacktestStore()
const fileRef = ref<File | null>(null)
const strategy = ref<'sma' | 'rsi'>('sma')
const smaShort = ref<number>(10)
const smaLong = ref<number>(30)
const rsiPeriod = ref<number>(14)
const rsiOverbought = ref<number>(70)
const rsiOversold = ref<number>(30)
const startDate = ref<string>('')
const endDate = ref<string>('')
const error = ref<string | null>(null)
const dragActive = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)

const validSma = computed(() => smaShort.value > 0 && smaLong.value > 0 && smaShort.value < smaLong.value)
const validRsi = computed(() => rsiPeriod.value > 0 && rsiOverbought.value > rsiOversold.value)
const validParams = computed(() => strategy.value === 'sma' ? validSma.value : validRsi.value)
const canSubmit = computed(() => !!fileRef.value && validParams.value && store.status !== 'loading')

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0] || null
  error.value = null
  if (f && !isCsvFile(f)) {
    error.value = 'File must be in .csv format'
    fileRef.value = null
    return
  }
  fileRef.value = f
}

function isCsvFile(f: File) {
  // Certains navigateurs remettent un type mimé incohérent pour CSV, on tolère l’extension
  return f.type === 'text/csv' || f.name.toLowerCase().endsWith('.csv')
}

function onZoneClick() {
  inputEl.value?.click()
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
  dragActive.value = true
}

function onDragEnter(e: DragEvent) {
  e.preventDefault()
  dragActive.value = true
}

function onDragLeave(e: DragEvent) {
  e.preventDefault()
  dragActive.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  dragActive.value = false
  const f = e.dataTransfer?.files?.[0]
  error.value = null
  if (!f) return
  if (!isCsvFile(f)) {
    error.value = 'File must be in .csv format'
    fileRef.value = null
    return
  }
  fileRef.value = f
}

async function onSubmit() {
  error.value = null
  if (!fileRef.value) { error.value = 'Please select a CSV file'; return }
  if (!validParams.value) { error.value = strategy.value==='sma' ? 'Invalid SMA parameters' : 'Invalid RSI parameters'; return }
  const req = strategy.value === 'sma'
    ? { strategy: 'sma' as const, params: { smaShort: smaShort.value, smaLong: smaLong.value }, dates: { startDate: startDate.value || undefined, endDate: endDate.value || undefined } }
    : { strategy: 'rsi' as const, params: { period: rsiPeriod.value, overbought: rsiOverbought.value, oversold: rsiOversold.value }, dates: { startDate: startDate.value || undefined, endDate: endDate.value || undefined } }
  await store.runBacktest(fileRef.value, req)
}

function onReset() {
  store.reset()
  fileRef.value = null
  error.value = null
  strategy.value = 'sma'
  smaShort.value = 10
  smaLong.value = 30
  rsiPeriod.value = 14
  rsiOverbought.value = 70
  rsiOversold.value = 30
  startDate.value = ''
  endDate.value = ''
}
</script>

<template>
  <div class="space-y-4">
    <div>
      <Label class="mb-1">CSV File</Label>
      <div
        class="rounded-lg border border-dashed p-4 text-sm transition-colors"
        :class="[
          dragActive ? 'border-primary bg-primary/5' : 'hover:bg-muted/30',
          'text-muted-foreground cursor-pointer'
        ]"
        @click="onZoneClick"
        @dragenter="onDragEnter"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
      >
        <Input ref="inputEl" type="file" accept=".csv" @change="onFileChange" />
        <p class="mt-2">Glissez-déposez votre fichier ou cliquez pour sélectionner.</p>
        <p v-if="fileRef" class="mt-1 text-xs text-foreground">Fichier sélectionné : {{ fileRef?.name }}</p>
      </div>
    </div>
    <div>
      <Label class="mb-1">Strategy</Label>
      <select v-model="strategy" class="w-full h-9 rounded-md border bg-background px-3 text-sm">
        <option value="sma">SMA Crossover</option>
        <option value="rsi">RSI Strategy</option>
      </select>
    </div>
    <div class="grid grid-cols-2 gap-3" v-if="strategy==='sma'">
      <div>
        <Label class="mb-1">SMA Short</Label>
        <Input v-model.number="smaShort" type="number" min="1" />
      </div>
      <div>
        <Label class="mb-1">SMA Long</Label>
        <Input v-model.number="smaLong" type="number" min="2" />
      </div>
    </div>
    <div class="grid grid-cols-3 gap-3" v-else>
      <div>
        <Label class="mb-1">RSI Period</Label>
        <Input v-model.number="rsiPeriod" type="number" min="1" placeholder="e.g. 14" title="Positive integer" />
      </div>
      <div>
        <Label class="mb-1">Overbought</Label>
        <Input v-model.number="rsiOverbought" type="number" step="0.1" placeholder="e.g. 70.0" title="Float, must be > Oversold" />
      </div>
      <div>
        <Label class="mb-1">Oversold</Label>
        <Input v-model.number="rsiOversold" type="number" step="0.1" placeholder="e.g. 30.0" title="Float, must be < Overbought" />
      </div>
    </div>
    <div class="grid grid-cols-2 gap-3">
      <div>
        <Label class="mb-1">Start Date (optional)</Label>
        <Input v-model="startDate" type="date" />
      </div>
      <div>
        <Label class="mb-1">End Date (optional)</Label>
        <Input v-model="endDate" type="date" />
      </div>
    </div>
    <div class="flex items-center gap-2">
      <Button :disabled="!canSubmit" class="h-10" @click="onSubmit">Run</Button>
      <Button variant="outline" class="h-10" @click="onReset">Reset</Button>
    </div>
    <p v-if="strategy==='sma' && !validSma" class="text-xs text-amber-600">SMA Short must be &lt; SMA Long and &gt; 0</p>
    <p v-if="strategy==='rsi' && !validRsi" class="text-xs text-amber-600">Overbought must be &gt; Oversold; Period &gt; 0</p>
    <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
  </div>
</template>