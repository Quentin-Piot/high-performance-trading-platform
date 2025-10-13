<script setup lang="ts">
import { ref, computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBacktestStore } from '@/stores/backtestStore'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { ToggleGroupItem, MultiLineToggleGroup } from '@/components/ui/toggle-group'
import { BACKTEST_STRATEGIES, type StrategyId } from '@/config/backtestStrategies'
import { AVAILABLE_DATASETS, fetchDatasetFile } from '@/config/datasets'
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
  AlertCircle,
  X,
  Database
} from 'lucide-vue-next'

const store = useBacktestStore()
const { t } = useI18n()
const selectedFiles = ref<File[]>([])
const selectedDatasets = ref<string[]>([])
const strategy = ref<StrategyId>('sma_crossover')
const params = reactive<Record<string, number>>({})
const startDate = ref<string>('')
const endDate = ref<string>('')
const error = ref<string | null>(null)
const dragActive = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)

// Monte Carlo parameters
const monteCarloRuns = ref<number>(1)
const monteCarloMethod = ref<'bootstrap' | 'gaussian' | ''>('bootstrap')
const sampleFraction = ref<number>(1.0)
const gaussianScale = ref<number>(1.0)

// Computed property to check if Monte Carlo is enabled
const isMonteCarloEnabled = computed(() => monteCarloRuns.value > 1)

// Watch for Monte Carlo runs changes to ensure method is selected
watch(monteCarloRuns, (newValue) => {
  if (newValue > 1 && !monteCarloMethod.value) {
    monteCarloMethod.value = 'bootstrap'
  }
})

function formatDateToDisplay(isoDate: string): string {
  if (!isoDate) return ''
  const [year, month, day] = isoDate.split('-')
  return `${day}/${month}/${year}`
}

function formatDateToISO(displayDate: string): string {
  if (!displayDate) return ''
  const parts = displayDate.split('/')
  if (parts.length !== 3) return ''
  const [day, month, year] = parts
  if (!day || !month || !year) return ''
  return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
}

const startDateDisplay = computed({
  get: () => formatDateToDisplay(startDate.value),
  set: (value: string) => {
    startDate.value = formatDateToISO(value)
  }
})

const endDateDisplay = computed({
  get: () => formatDateToDisplay(endDate.value),
  set: (value: string) => {
    endDate.value = formatDateToISO(value)
  }
})

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
const canSubmit = computed(() => 
  (selectedFiles.value.length > 0 || selectedDatasets.value.length > 0) && 
  validParams.value && 
  store.status !== 'loading' &&
  // Add validation for Monte Carlo method when Monte Carlo is enabled
  (!isMonteCarloEnabled.value || (isMonteCarloEnabled.value && monteCarloMethod.value))
)

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  addFiles(files)
}

function addFiles(files: File[]) {
  error.value = null
  const validFiles = files.filter(f => {
    if (!isCsvFile(f)) {
      error.value = t('errors.invalid_csv')
      return false
    }
    return true
  })
  
  const newFiles = [...selectedFiles.value, ...validFiles]
  if (newFiles.length > 10) {
    error.value = 'Maximum 10 files allowed'
    return
  }
  
  selectedFiles.value = newFiles
}

function removeFile(index: number) {
  selectedFiles.value = selectedFiles.value.filter((_, i) => i !== index)
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
  const files = Array.from(e.dataTransfer?.files || [])
  addFiles(files)
}

async function onSubmit() {
  error.value = null
  
  // Validate Monte Carlo method selection
  if (isMonteCarloEnabled.value && !monteCarloMethod.value) {
    error.value = t('simulate.form.monte_carlo.method_required')
    return
  }
  
  // Combine uploaded files and selected datasets
  let allFiles = [...selectedFiles.value]
  
  // Fetch dataset files if any are selected
  if (selectedDatasets.value.length > 0) {
    try {
      const datasetFiles = await Promise.all(
        selectedDatasets.value.map(async (datasetId) => {
          const dataset = AVAILABLE_DATASETS.find(d => d.id === datasetId)
          if (!dataset) throw new Error(`Dataset ${datasetId} not found`)
          return await fetchDatasetFile(dataset.filename)
        })
      )
      allFiles = [...allFiles, ...datasetFiles]
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load datasets'
      return
    }
  }
  
  if (allFiles.length === 0) { 
    error.value = t('errors.no_csv_file')
    return 
  }
  
  if (!validParams.value) { 
    error.value = validation.value.message || t('errors.invalid_params')
    return 
  }
  
  const req = { 
    strategy: strategy.value, 
    params: { ...params }, 
    dates: { 
      startDate: startDate.value || undefined, 
      endDate: endDate.value || undefined 
    },
    // Add Monte Carlo parameters
    monte_carlo_runs: monteCarloRuns.value,
    method: monteCarloMethod.value || undefined,
    sample_fraction: sampleFraction.value,
    gaussian_scale: gaussianScale.value
  }
  
  // Use the new unified backtest function that handles both single and multiple files
  await store.runBacktestUnified(allFiles, req)
}

function onReset() {
  store.reset()
  selectedFiles.value = []
  selectedDatasets.value = []
  error.value = null
  strategy.value = 'sma_crossover'
  initParams()
  startDate.value = ''
  endDate.value = ''
  // Reset Monte Carlo parameters
  monteCarloRuns.value = 1
  monteCarloMethod.value = 'bootstrap'
  sampleFraction.value = 1.0
  gaussianScale.value = 1.0
}
</script>

<template>
  <div class="space-y-4">
    <!-- File Upload Section avec design premium -->
    <div class="space-y-2">
      <Label class="text-sm font-medium flex items-center gap-2">
        <div class="rounded-lg bg-trading-blue/10 p-1.5 text-trading-blue">
          <Upload class="size-3.5" />
        </div>
        {{ t('simulate.form.labels.csv_file') }}
      </Label>
      <div
        class="group relative overflow-hidden rounded-xl border-2 border-dashed p-4 text-sm transition-all duration-300 cursor-pointer"
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
        
        <input ref="inputEl" type="file" accept=".csv" multiple @change="onFileChange" class="hidden" />
        
        <div class="relative z-10 flex flex-col items-center gap-3">
          <div class="rounded-full bg-secondary/50 p-3 group-hover:bg-trading-blue/10 transition-colors">
            <FileSpreadsheet class="size-6 text-muted-foreground group-hover:text-trading-blue transition-colors" />
          </div>
          <div class="text-center">
            <p class="font-medium">{{ t('simulate.form.csv.drop_hint') }}</p>
            <p class="text-xs text-muted-foreground mt-1">{{ t('simulate.form.csv.max_files') }}</p>
            <div v-if="selectedFiles.length > 0" class="mt-3 space-y-2">
              <p class="text-xs text-trading-green font-medium flex items-center justify-center gap-2">
                <CheckCircle class="size-4" />
                {{ selectedFiles.length }} {{ t('simulate.form.csv.files_selected') }}
              </p>
              <div class="max-h-32 overflow-y-auto space-y-1">
                <div v-for="(file, index) in selectedFiles" :key="index" 
                     class="flex items-center justify-between bg-secondary/30 rounded-lg px-3 py-2 text-xs">
                  <span class="truncate flex-1">{{ file.name }}</span>
                  <button @click.stop="removeFile(index)" 
                          class="ml-2 p-1 hover:bg-red-100 rounded-full transition-colors">
                    <X class="size-3 text-red-500" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Dataset Selection Section -->
    <div class="space-y-2">
      <Label class="text-sm font-medium flex items-center gap-2">
        <div class="rounded-lg bg-trading-cyan/10 p-1.5 text-trading-cyan">
          <Database class="size-3.5" />
        </div>
        {{ t('simulate.form.labels.datasets') }}
      </Label>
      <div class="space-y-3">
        <p class="text-xs text-muted-foreground">{{ t('simulate.form.labels.datasets_description') }}</p>
        <MultiLineToggleGroup 
          v-model="selectedDatasets" 
          type="multiple" 
          variant="outline" 
          size="sm"
          :items-per-row="3"
          class="w-full"
        >
          <ToggleGroupItem 
            v-for="dataset in AVAILABLE_DATASETS" 
            :key="dataset.id" 
            :value="dataset.id"
            class="text-xs px-3 py-2 font-medium transition-all duration-200 
                   !rounded-md !border-2 !border-gray-200
                   data-[state=on]:!bg-gradient-to-r data-[state=on]:!from-[oklch(0.55_0.18_260)] data-[state=on]:!to-[oklch(0.65_0.2_300)]
                   data-[state=on]:!text-white data-[state=on]:!shadow-md data-[state=on]:!border-transparent
                   data-[state=on]:!scale-[1.02] data-[state=on]:!font-semibold
                   hover:data-[state=on]:!opacity-90
                   data-[state=off]:hover:!border-purple-300/30 data-[state=off]:hover:!bg-purple-50/5"
          >
            {{ dataset.name }}
          </ToggleGroupItem>
        </MultiLineToggleGroup>
        <div v-if="selectedDatasets.length > 0" class="mt-2">
          <p class="text-xs text-trading-green font-medium flex items-center gap-2">
            <CheckCircle class="size-4" />
            {{ selectedDatasets.length }} dataset{{ selectedDatasets.length > 1 ? 's' : '' }} selected
          </p>
        </div>
      </div>
    </div>

    <!-- Strategy Selection avec style moderne -->
    <div class="space-y-2">
      <Label class="text-sm font-medium flex items-center gap-2">
        <div class="rounded-lg bg-trading-purple/10 p-1.5 text-trading-purple">
          <TrendingUp class="size-3.5" />
        </div>
        {{ t('simulate.form.labels.strategy') }}
      </Label>
      <div class="relative">
        <select 
          v-model="strategy" 
          class="w-full h-11 rounded-xl border-0 bg-gradient-to-r from-secondary/50 to-accent/30 px-4 pr-10 text-sm font-medium shadow-soft hover:shadow-medium transition-all duration-300 focus:ring-2 focus:ring-trading-blue/50 focus:outline-none appearance-none"
        >
          <option v-for="id in Object.keys(BACKTEST_STRATEGIES)" :key="id" :value="id" class="bg-background">
            {{ t('simulate.form.strategy.names.' + (id as string)) }}
          </option>
        </select>
        <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
      </div>
    </div>

    <!-- Parameters Grid avec animations -->
    <div class="space-y-2">
      <Label class="text-sm font-medium flex items-center gap-2">
        <div class="rounded-lg bg-trading-green/10 p-1.5 text-trading-green">
          <Settings class="size-3.5" />
        </div>
        {{ t('simulate.form.labels.strategy_params') }}
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

    <!-- Monte Carlo Parameters Section -->
    <div class="space-y-2">
      <Label class="text-sm font-medium flex items-center gap-2">
        <div class="rounded-lg bg-trading-purple/10 p-1.5 text-trading-purple">
          <TrendingUp class="size-3.5" />
        </div>
        {{ t('simulate.form.monte_carlo.title') }}
      </Label>
      <div class="space-y-4">
        <!-- Number of Runs -->
        <div class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground">
            {{ t('simulate.form.monte_carlo.runs') }}
          </Label>
          <div class="relative group">
            <Input
              v-model.number="monteCarloRuns"
              type="number"
              :min="1"
              :max="20000"
              :step="1"
              class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-purple/50"
            />
            <div class="absolute inset-0 rounded-lg bg-gradient-to-r from-trading-purple/0 via-trading-purple/5 to-trading-purple/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
          </div>
          <p class="text-xs text-muted-foreground">{{ t('simulate.form.monte_carlo.runs_description') }}</p>
        </div>

        <!-- Method Selection (only show when Monte Carlo is enabled) -->
        <div v-if="isMonteCarloEnabled" class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground">
            {{ t('simulate.form.monte_carlo.method') }}
          </Label>
          <MultiLineToggleGroup 
            v-model="monteCarloMethod" 
            type="single" 
            variant="outline" 
            size="sm"
            :items-per-row="2"
            class="w-full"
          >
            <ToggleGroupItem 
              value="bootstrap"
              class="text-xs px-3 py-2 font-medium transition-all duration-200 
                     !rounded-md !border-2 !border-gray-200
                     data-[state=on]:!bg-gradient-to-r data-[state=on]:!from-[oklch(0.55_0.18_260)] data-[state=on]:!to-[oklch(0.65_0.2_300)]
                     data-[state=on]:!text-white data-[state=on]:!shadow-md data-[state=on]:!border-transparent
                     data-[state=on]:!scale-[1.02] data-[state=on]:!font-semibold
                     hover:data-[state=on]:!opacity-90
                     data-[state=off]:hover:!border-purple-300/30 data-[state=off]:hover:!bg-purple-50/5"
            >
              {{ t('simulate.form.monte_carlo.bootstrap') }}
            </ToggleGroupItem>
            <ToggleGroupItem 
              value="gaussian"
              class="text-xs px-3 py-2 font-medium transition-all duration-200 
                     !rounded-md !border-2 !border-gray-200
                     data-[state=on]:!bg-gradient-to-r data-[state=on]:!from-[oklch(0.55_0.18_260)] data-[state=on]:!to-[oklch(0.65_0.2_300)]
                     data-[state=on]:!text-white data-[state=on]:!shadow-md data-[state=on]:!border-transparent
                     data-[state=on]:!scale-[1.02] data-[state=on]:!font-semibold
                     hover:data-[state=on]:!opacity-90
                     data-[state=off]:hover:!border-purple-300/30 data-[state=off]:hover:!bg-purple-50/5"
            >
              {{ t('simulate.form.monte_carlo.gaussian') }}
            </ToggleGroupItem>
          </MultiLineToggleGroup>
        </div>

        <!-- Method-specific parameters -->
        <div v-if="isMonteCarloEnabled" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- Sample Fraction (for bootstrap) -->
          <div v-if="monteCarloMethod === 'bootstrap'" class="space-y-2">
            <Label class="text-xs font-medium text-muted-foreground">
              {{ t('simulate.form.monte_carlo.sample_fraction') }}
            </Label>
            <div class="relative group">
              <Input
                v-model.number="sampleFraction"
                type="number"
                :min="0.1"
                :max="2.0"
                :step="0.1"
                class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-purple/50"
              />
              <div class="absolute inset-0 rounded-lg bg-gradient-to-r from-trading-purple/0 via-trading-purple/5 to-trading-purple/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
            </div>
          </div>

          <!-- Gaussian Scale (for gaussian) -->
          <div v-if="monteCarloMethod === 'gaussian'" class="space-y-2">
            <Label class="text-xs font-medium text-muted-foreground">
              {{ t('simulate.form.monte_carlo.gaussian_scale') }}
            </Label>
            <div class="relative group">
              <Input
                v-model.number="gaussianScale"
                type="number"
                :min="0.1"
                :max="5.0"
                :step="0.1"
                class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-purple/50"
              />
              <div class="absolute inset-0 rounded-lg bg-gradient-to-r from-trading-purple/0 via-trading-purple/5 to-trading-purple/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Date Range avec design élégant -->
    <div class="space-y-2">
      <Label class="text-sm font-medium flex items-center gap-2">
        <div class="rounded-lg bg-trading-cyan/10 p-1.5 text-trading-cyan">
          <Calendar class="size-3.5" />
        </div>
        {{ t('simulate.form.labels.analysis_period') }}
      </Label>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground">
            {{ t('simulate.form.labels.start_date_optional') }}
          </Label>
          <Input 
            v-model="startDateDisplay" 
            type="text"
            placeholder="dd/mm/yyyy"
            pattern="[0-9]{2}/[0-9]{2}/[0-9]{4}"
            class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-cyan/50"
          />
        </div>
        <div class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground">
            {{ t('simulate.form.labels.end_date_optional') }}
          </Label>
          <Input 
            v-model="endDateDisplay" 
            type="text"
            placeholder="dd/mm/yyyy"
            pattern="[0-9]{2}/[0-9]{2}/[0-9]{4}"
            class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-cyan/50"
          />
        </div>
      </div>
    </div>

    <!-- Action Buttons avec effets premium -->
    <div class="flex items-center gap-3 pt-2">
      <Button 
        :disabled="!canSubmit" 
        class="flex-1 h-12 rounded-xl bg-trading-blue text-white font-semibold shadow-medium hover:shadow-strong transition-all duration-300 hover:bg-trading-blue/90 disabled:opacity-70 disabled:cursor-not-allowed"
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