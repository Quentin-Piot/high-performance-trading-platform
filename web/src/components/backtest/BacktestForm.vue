<script setup lang="ts">
import { ref, computed, reactive, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBacktestStore } from '@/stores/backtestStore'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { BACKTEST_STRATEGIES, type StrategyId } from '@/config/backtestStrategies'
import { AVAILABLE_DATASETS, fetchDatasetFile } from '@/config/datasets'
import FileUploadSection from './FileUploadSection.vue'
import DatasetSelectionSection from './DatasetSelectionSection.vue'
import DateRangeSelector from './DateRangeSelector.vue'
import StrategyParametersSection from './StrategyParametersSection.vue'
import MonteCarloSection from './MonteCarloSection.vue'
import PriceTypeSection from './PriceTypeSection.vue'
import {
  validateDateRange,
  calculateDateRangeWithCsvFiles
} from '@/services/frontendDateValidationService'
import type { DateValue } from "@internationalized/date"
import {
  CalendarDate
} from "@internationalized/date"
import { 
  TrendingUp, 
  ChevronDown, 
  Play, 
  RotateCcw, 
  AlertTriangle, 
  XCircle, 
  AlertCircle,
  Calendar
} from 'lucide-vue-next'

const store = useBacktestStore()
const { t } = useI18n()
const selectedFiles = ref<File[]>([])
const selectedDatasets = ref<string[]>([])
const strategy = ref<StrategyId>('sma_crossover')
const params = reactive<Record<string, number>>({})
const startDate = ref<string>('')
const endDate = ref<string>('')
const startDateValue = ref<DateValue>()
const endDateValue = ref<DateValue>()
const error = ref<string | null>(null)

// Date validation state
const dateValidationError = ref<string | null>(null)

// Monte Carlo parameters
const monteCarloRuns = ref<number>(1)
const monteCarloMethod = ref<'bootstrap' | 'gaussian' | ''>('bootstrap')
const sampleFraction = ref<number>(0.8)
const gaussianScale = ref<number>(0.1)

// Price type selection
const priceType = ref<'close' | 'adj_close'>('close')

// Computed property to check if Monte Carlo is enabled
const isMonteCarloEnabled = computed(() => monteCarloRuns.value > 1)

// Watch for Monte Carlo runs changes to ensure method is selected
watch(monteCarloRuns, (newValue) => {
  if (newValue > 1 && !monteCarloMethod.value) {
    monteCarloMethod.value = 'bootstrap'
  }
})

// Watch for date value changes to sync with ISO strings
watch(startDateValue, (value) => {
  if (value) {
    startDate.value = value.toString()
  } else {
    startDate.value = ''
  }
})

watch(endDateValue, (value) => {
  if (value) {
    endDate.value = value.toString()
  } else {
    endDate.value = ''
  }
})

// Watch for ISO string changes to sync with DateValue (for auto-adjustment)
watch(startDate, (value) => {
  if (value && value !== startDateValue.value?.toString()) {
    try {
      // Parse date without timezone issues by splitting the ISO string
      const [year, month, day] = value.split('-').map(Number)
      if (year && month && day && !isNaN(year) && !isNaN(month) && !isNaN(day)) {
        startDateValue.value = new CalendarDate(year, month, day)
      }
    } catch (error) {
      console.warn('Failed to parse start date:', error)
    }
  } else if (!value) {
    startDateValue.value = undefined
  }
})

watch(endDate, (value) => {
  if (value && value !== endDateValue.value?.toString()) {
    try {
      // Parse date without timezone issues by splitting the ISO string
      const [year, month, day] = value.split('-').map(Number)
      if (year && month && day && !isNaN(year) && !isNaN(month) && !isNaN(day)) {
        endDateValue.value = new CalendarDate(year, month, day)
      }
    } catch (error) {
      console.warn('Failed to parse end date:', error)
    }
  } else if (!value) {
    endDateValue.value = undefined
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

// Load available date ranges on component mount
onMounted(() => {
  // Plus besoin de charger les plages de dates depuis le backend
  // Les données sont maintenant disponibles directement dans la configuration des datasets
})

// Watch for date changes to validate them
watch([startDate, endDate, selectedDatasets], () => {
  dateValidationError.value = null
  
  if (selectedDatasets.value.length === 0) {
    return
  }
  
  // Only validate if both dates are provided
  if (!startDate.value || !endDate.value) {
    return
  }
  
  // Valider avec le nouveau service frontend
  const validation = validateDateRange(startDate.value, endDate.value, selectedDatasets.value)
  
  if (!validation.valid) {
    dateValidationError.value = validation.errorMessage || 'Plage de dates invalide'
  }
})

// Watch for dataset selection changes to auto-adjust dates
watch([selectedDatasets, selectedFiles], async ([newDatasets, newFiles]) => {
  if (newDatasets.length === 0 && newFiles.length === 0) {
    return
  }
  
  // Calculer la plage de dates complète incluant les CSV uploadés
  const fullRange = await calculateDateRangeWithCsvFiles(newDatasets, newFiles)
  
  if (fullRange) {
    // Toujours définir les dates avec la plage complète disponible
    startDate.value = fullRange.minDate
    endDate.value = fullRange.maxDate
  }
})

const validation = computed(() => currentCfg.value.validate(params))
const validParams = computed(() => validation.value.ok)
const canSubmit = computed(() => 
  (selectedFiles.value.length > 0 || selectedDatasets.value.length > 0) && 
  validParams.value && 
  store.status !== 'loading' &&
  // Add validation for Monte Carlo method when Monte Carlo is enabled
  (!isMonteCarloEnabled.value || (isMonteCarloEnabled.value && monteCarloMethod.value)) &&
  // Add date validation
  !dateValidationError.value
)

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
    gaussian_scale: gaussianScale.value,
    price_type: priceType.value
  }
  
  // Use the new unified backtest function that handles both single and multiple files
  await store.runBacktestUnified(allFiles, req, selectedDatasets.value)
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
    <!-- File Upload Section -->
    <FileUploadSection
      v-model:selected-files="selectedFiles"
      v-model:error="error"
    />

    <!-- Dataset Selection Section -->
    <DatasetSelectionSection
      v-model:selected-datasets="selectedDatasets"
    />

    <!-- Price Type Selection Section -->
    <PriceTypeSection
      :price-type="priceType"
      @update:price-type="(value) => priceType = value"
    />

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
    <StrategyParametersSection
      :strategy="strategy"
      :params="params"
      :current-cfg="currentCfg"
      @update:params="(newParams) => Object.assign(params, newParams)"
    />

    <!-- Monte Carlo Parameters Section -->
    <MonteCarloSection
      :monte-carlo-runs="monteCarloRuns"
      :monte-carlo-method="monteCarloMethod"
      :sample-fraction="sampleFraction"
      :gaussian-scale="gaussianScale"
      :is-monte-carlo-enabled="isMonteCarloEnabled"
      @update:monte-carlo-runs="(value) => monteCarloRuns = value"
      @update:monte-carlo-method="(value: string) => monteCarloMethod = value as 'bootstrap' | 'gaussian'"
      @update:sample-fraction="(value) => sampleFraction = value"
      @update:gaussian-scale="(value) => gaussianScale = value"
    />

    <!-- Date Range Section -->
    <DateRangeSelector
      v-model:start-date-value="startDateValue"
      v-model:end-date-value="endDateValue"
      v-model:start-date="startDate"
      v-model:end-date="endDate"
      :selected-datasets="selectedDatasets"
      :date-validation-error="dateValidationError"
    />



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
      
      <div v-if="dateValidationError" class="rounded-xl border border-trading-red/20 bg-gradient-to-r from-trading-red/5 to-red-50/30 text-trading-red p-4 shadow-soft animate-slide-up">
        <div class="flex items-center gap-3">
          <div class="rounded-full bg-trading-red/10 p-2">
            <Calendar class="size-4" />
          </div>
          <span class="text-sm font-medium">{{ dateValidationError }}</span>
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