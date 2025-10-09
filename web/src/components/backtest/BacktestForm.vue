<script setup lang="ts">
import { ref, computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBacktestStore } from '@/stores/backtestStore'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { BACKTEST_STRATEGIES, type StrategyId } from '@/config/backtestStrategies'
import { 
  Upload, 
  FileSpreadsheet, 
  CheckCircle, 
  TrendingUp, 
  ChevronDown, 
  Settings, 
  Calendar, 
  Play, 
  RotateCcw, 
  AlertTriangle, 
  XCircle, 
  AlertCircle 
} from 'lucide-vue-next'

const store = useBacktestStore()
const { t } = useI18n()
const fileRef = ref<File | null>(null)
const strategy = ref<StrategyId>('sma_crossover')
const params = reactive<Record<string, number>>({})
const startDate = ref<string>('')
const endDate = ref<string>('')
const error = ref<string | null>(null)
const dragActive = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)

const currentCfg = computed(() => BACKTEST_STRATEGIES[strategy.value])
function initParams() {
  const cfg = currentCfg.value
  for (const p of cfg.params) {
    params[p.key] = p.default
  }
}
initParams()
watch(strategy, () => initParams())

const validation = computed(() => currentCfg.value.validate(params))
const validParams = computed(() => validation.value.ok)
const canSubmit = computed(() => !!fileRef.value && validParams.value && store.status !== 'loading')

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0] || null
  error.value = null
  if (f && !isCsvFile(f)) {
    error.value = t('errors.invalid_csv')
    fileRef.value = null
    return
  }
  fileRef.value = f
}

function isCsvFile(f: File) {
  // Certains navigateurs remettent un type mimé incohérent pour CSV, on tolère l'extension
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
  if (!fileRef.value) { error.value = t('errors.no_csv_file'); return }
  if (!validParams.value) { error.value = validation.value.message || t('errors.invalid_params'); return }
  const req = { strategy: strategy.value, params: { ...params }, dates: { startDate: startDate.value || undefined, endDate: endDate.value || undefined } }
  await store.runBacktest(fileRef.value, req)
}

function onReset() {
  store.reset()
  fileRef.value = null
  error.value = null
  strategy.value = 'sma_crossover'
  initParams()
  startDate.value = ''
  endDate.value = ''
}
</script>

<template>
  <div class="space-y-6">
    <!-- File Upload Section avec design premium -->
    <div class="space-y-3">
      <Label class="text-sm font-medium flex items-center gap-2">
        <div class="rounded-lg bg-trading-blue/10 p-1.5 text-trading-blue">
          <Upload class="size-3.5" />
        </div>
        {{ t('simulate.form.labels.csv_file') }}
      </Label>
      <div
        class="group relative overflow-hidden rounded-xl border-2 border-dashed p-6 text-sm transition-all duration-300 cursor-pointer"
        :class="[
          dragActive 
            ? 'border-trading-blue bg-gradient-to-br from-trading-blue/5 via-trading-blue/10 to-trading-purple/5 shadow-soft' 
            : 'border-border hover:border-trading-blue/50 hover:bg-gradient-to-br hover:from-secondary/30 hover:to-accent/20',
          'text-muted-foreground hover:text-foreground'
        ]"
        @click="onZoneClick"
        @dragenter="onDragEnter"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
      >
        <!-- Animated background effect -->
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
        
        <input ref="inputEl" type="file" accept=".csv" @change="onFileChange" class="hidden" />
        
        <div class="relative z-10 flex flex-col items-center gap-3">
          <div class="rounded-full bg-secondary/50 p-3 group-hover:bg-trading-blue/10 transition-colors">
            <FileSpreadsheet class="size-6 text-muted-foreground group-hover:text-trading-blue transition-colors" />
          </div>
          <div class="text-center">
            <p class="font-medium">{{ t('simulate.form.csv.drop_hint') }}</p>
            <p v-if="fileRef" class="mt-2 text-xs text-trading-green font-medium flex items-center justify-center gap-2">
              <CheckCircle class="size-4" />
              {{ t('simulate.form.csv.selected_file', { name: fileRef?.name }) }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Strategy Selection avec style moderne -->
    <div class="space-y-3">
      <Label class="text-sm font-medium flex items-center gap-2">
        <div class="rounded-lg bg-trading-purple/10 p-1.5 text-trading-purple">
          <TrendingUp class="size-3.5" />
        </div>
        {{ t('simulate.form.labels.strategy') }}
      </Label>
      <div class="relative">
        <select 
          v-model="strategy" 
          class="w-full h-11 rounded-xl border-0 bg-gradient-to-r from-secondary/50 to-accent/30 px-4 text-sm font-medium shadow-soft hover:shadow-medium transition-all duration-300 focus:ring-2 focus:ring-trading-blue/50 focus:outline-none"
        >
          <option v-for="id in Object.keys(BACKTEST_STRATEGIES)" :key="id" :value="id" class="bg-background">
            {{ t('simulate.form.strategy.names.' + (id as string)) }}
          </option>
        </select>
        <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
      </div>
    </div>

    <!-- Parameters Grid avec animations -->
    <div class="space-y-3">
      <Label class="text-sm font-medium flex items-center gap-2">
        <div class="rounded-lg bg-trading-green/10 p-1.5 text-trading-green">
          <Settings class="size-3.5" />
        </div>
        Paramètres de stratégie
      </Label>
      <div class="grid gap-4 animate-slide-up" :class="currentCfg.params.length === 3 ? 'grid-cols-1 sm:grid-cols-3' : 'grid-cols-1 sm:grid-cols-2'">
        <div v-for="(p, index) in currentCfg.params" :key="p.key" class="space-y-2 animate-scale-in" :style="`animation-delay: ${index * 0.1}s`">
          <Label class="text-xs font-medium text-muted-foreground">
            {{ t('simulate.form.strategy.params.' + strategy + '.' + p.key) }}
          </Label>
          <div class="relative group">
            <Input
              v-model.number="params[p.key]"
              type="number"
              :min="p.min ?? undefined"
              :step="p.type==='float' ? 0.1 : 1"
              class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-blue/50"
            />
            <div class="absolute inset-0 rounded-lg bg-gradient-to-r from-trading-blue/0 via-trading-blue/5 to-trading-blue/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Date Range avec design élégant -->
    <div class="space-y-3">
      <Label class="text-sm font-medium flex items-center gap-2">
        <div class="rounded-lg bg-trading-cyan/10 p-1.5 text-trading-cyan">
          <Calendar class="size-3.5" />
        </div>
        Période d'analyse
      </Label>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground">
            {{ t('simulate.form.labels.start_date_optional') }}
          </Label>
          <Input 
            v-model="startDate" 
            type="date" 
            class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-cyan/50"
          />
        </div>
        <div class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground">
            {{ t('simulate.form.labels.end_date_optional') }}
          </Label>
          <Input 
            v-model="endDate" 
            type="date" 
            class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-cyan/50"
          />
        </div>
      </div>
    </div>

    <!-- Action Buttons avec effets premium -->
    <div class="flex items-center gap-3 pt-2">
      <Button 
        :disabled="!canSubmit" 
        class="flex-1 h-12 bg-gradient-to-r from-trading-blue to-trading-purple hover:from-trading-blue/90 hover:to-trading-purple/90 text-white font-medium shadow-medium hover:shadow-strong transition-all duration-300 hover-scale disabled:opacity-70 disabled:cursor-not-allowed disabled:from-gray-400 disabled:to-gray-500"
        @click="onSubmit"
      >
        <div class="flex items-center gap-2">
          <Play class="size-4" />
          {{ t('simulate.form.buttons.run') }}
        </div>
      </Button>
      <Button 
        variant="outline" 
        class="h-12 px-6 border-0 bg-gradient-to-r from-secondary/50 to-accent/30 hover:from-secondary/70 hover:to-accent/50 shadow-soft hover:shadow-medium transition-all duration-300 hover-scale"
        @click="onReset"
      >
        <div class="flex items-center gap-2">
          <RotateCcw class="size-4" />
          {{ t('simulate.form.buttons.reset') }}
        </div>
      </Button>
    </div>

    <!-- Status Messages avec design moderne -->
    <div class="space-y-3">
      <div v-if="!validParams" class="rounded-xl border border-amber-200/50 bg-gradient-to-r from-amber-50/50 to-orange-50/30 text-amber-700 p-4 shadow-soft animate-slide-up">
        <div class="flex items-center gap-3">
          <div class="rounded-full bg-amber-100 p-2">
            <AlertTriangle class="size-4" />
          </div>
          <span class="text-sm font-medium">{{ validation.message || t('errors.invalid_params') }}</span>
        </div>
      </div>
      
      <div v-if="error" class="rounded-xl border border-trading-red/20 bg-gradient-to-r from-trading-red/5 to-red-50/30 text-trading-red p-4 shadow-soft animate-slide-up">
        <div class="flex items-center gap-3">
          <div class="rounded-full bg-trading-red/10 p-2">
            <XCircle class="size-4" />
          </div>
          <span class="text-sm font-medium">{{ error }}</span>
        </div>
      </div>
      
      <div v-if="store.status==='error' && store.errorMessage" class="rounded-xl border border-trading-red/20 bg-gradient-to-r from-trading-red/5 to-red-50/30 text-trading-red p-4 shadow-soft animate-slide-up">
        <div class="flex items-center gap-3">
          <div class="rounded-full bg-trading-red/10 p-2">
            <AlertCircle class="size-4" />
          </div>
          <span class="text-sm font-medium">{{ store.errorMessage }}</span>
        </div>
      </div>
    </div>
  </div>
</template>