<script setup lang="ts">
import { ref, computed } from 'vue'
import { useBacktestStore } from '@/stores/backtestStore'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

const store = useBacktestStore()
const fileRef = ref<File | null>(null)
const smaShort = ref<number>(10)
const smaLong = ref<number>(30)
const error = ref<string | null>(null)
const dragActive = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)

const validParams = computed(() => smaShort.value > 0 && smaLong.value > 0 && smaShort.value < smaLong.value)
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
  if (!validParams.value) { error.value = 'Invalid SMA parameters'; return }
  await store.runBacktest(fileRef.value, smaShort.value, smaLong.value)
}

function onReset() {
  store.reset()
  fileRef.value = null
  error.value = null
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
    <div class="grid grid-cols-2 gap-3">
      <div>
        <Label class="mb-1">SMA Short</Label>
        <Input v-model.number="smaShort" type="number" min="1" />
      </div>
      <div>
        <Label class="mb-1">SMA Long</Label>
        <Input v-model.number="smaLong" type="number" min="2" />
      </div>
    </div>
    <div class="flex items-center gap-2">
      <Button :disabled="!canSubmit" class="h-10" @click="onSubmit">Run</Button>
      <Button variant="outline" class="h-10" @click="onReset">Reset</Button>
    </div>
    <p v-if="!validParams" class="text-xs text-amber-600">SMA Short must be &lt; SMA Long and &gt; 0</p>
    <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
  </div>
</template>