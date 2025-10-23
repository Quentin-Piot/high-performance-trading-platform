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
const dateValidationError = ref<string | null>(null)
const monteCarloRuns = ref<number>(1)
const monteCarloMethod = ref<'bootstrap' | 'gaussian' | ''>('bootstrap')
const sampleFraction = ref<number>(0.8)
const gaussianScale = ref<number>(0.1)
const priceType = ref<'close' | 'adj_close'>('close')
const isMonteCarloEnabled = computed(() => monteCarloRuns.value > 1)
watch(monteCarloRuns, (newValue) => {
  if (newValue > 1 && !monteCarloMethod.value) {
    monteCarloMethod.value = 'bootstrap'
  }
})
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
watch(startDate, (value) => {
  if (value && value !== startDateValue.value?.toString()) {
    try {
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
onMounted(async () => {
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.size > 0) {
    console.log('Loading parameters from URL:', Object.fromEntries(urlParams.entries()))
    const urlStrategy = urlParams.get('strategy')
    if (urlStrategy && urlStrategy in BACKTEST_STRATEGIES) {
      strategy.value = urlStrategy as StrategyId
    }
    const urlDatasets = urlParams.get('datasets')
    if (urlDatasets) {
      const datasetIds = urlDatasets.split(',').filter(Boolean).map(dataset => {
        if (dataset.includes('.csv')) {
          const filename = dataset
          const foundDataset = AVAILABLE_DATASETS.find(d => d.filename === filename)
          return foundDataset ? foundDataset.id : dataset.toLowerCase().replace('.csv', '')
        }
        return dataset
      })
      selectedDatasets.value = datasetIds
    }
    const urlStartDate = urlParams.get('startDate')
    const urlEndDate = urlParams.get('endDate')
    if (urlStartDate) startDate.value = urlStartDate
    if (urlEndDate) endDate.value = urlEndDate
    const urlMonteCarloRuns = urlParams.get('monteCarloRuns')
    if (urlMonteCarloRuns) monteCarloRuns.value = parseInt(urlMonteCarloRuns, 10) || 1
    const urlMonteCarloMethod = urlParams.get('monteCarloMethod')
    if (urlMonteCarloMethod && (urlMonteCarloMethod === 'bootstrap' || urlMonteCarloMethod === 'gaussian')) {
      monteCarloMethod.value = urlMonteCarloMethod
    }
    const urlSampleFraction = urlParams.get('sampleFraction')
    if (urlSampleFraction) sampleFraction.value = parseFloat(urlSampleFraction) || 0.8
    const urlGaussianScale = urlParams.get('gaussianScale')
    if (urlGaussianScale) gaussianScale.value = parseFloat(urlGaussianScale) || 0.1
    const urlPriceType = urlParams.get('priceType')
    if (urlPriceType && (urlPriceType === 'close' || urlPriceType === 'adj_close')) {
      priceType.value = urlPriceType
    }
    const currentStrategy = BACKTEST_STRATEGIES[strategy.value]
    if (currentStrategy) {
      for (const param of currentStrategy.params) {
        const urlValue = urlParams.get(param.key)
        if (urlValue !== null) {
          const numValue = parseFloat(urlValue)
          if (!isNaN(numValue)) {
            params[param.key] = numValue
          }
        }
      }
    }
    setTimeout(async () => {
      if (canSubmit.value) {
        console.log('Auto-running backtest with URL parameters')
        await onSubmit()
      } else {
        console.warn('Cannot auto-run backtest: validation failed', {
          canSubmit: canSubmit.value,
          validParams: validParams.value,
          hasData: selectedFiles.value.length > 0 || selectedDatasets.value.length > 0,
          dateValidationError: dateValidationError.value
        })
      }
    }, 500)
  }
})
watch([startDate, endDate, selectedDatasets], () => {
  dateValidationError.value = null
  if (selectedDatasets.value.length === 0) {
    return
  }
  if (!startDate.value || !endDate.value) {
    return
  }
  setTimeout(() => {
    const validation = validateDateRange(startDate.value, endDate.value, selectedDatasets.value)
    if (!validation.valid) {
      dateValidationError.value = validation.errorMessage || 'Plage de dates invalide'
    }
  }, 100)
})
watch([selectedDatasets, selectedFiles], async ([newDatasets, newFiles]) => {
  if (newDatasets.length === 0 && newFiles.length === 0) {
    return
  }
  const fullRange = await calculateDateRangeWithCsvFiles(newDatasets, newFiles)
  if (fullRange) {
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
  (!isMonteCarloEnabled.value || (isMonteCarloEnabled.value && monteCarloMethod.value)) &&
  !dateValidationError.value
)
async function onSubmit() {
  error.value = null
  if (isMonteCarloEnabled.value && !monteCarloMethod.value) {
    error.value = t('simulate.form.monte_carlo.method_required')
    return
  }
  let allFiles = [...selectedFiles.value]
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
    monte_carlo_runs: monteCarloRuns.value,
    method: monteCarloMethod.value || undefined,
    sample_fraction: sampleFraction.value,
    gaussian_scale: gaussianScale.value,
    price_type: priceType.value
  }
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
  monteCarloRuns.value = 1
  monteCarloMethod.value = 'bootstrap'
  sampleFraction.value = 1.0
  gaussianScale.value = 1.0
}
</script>
<template>
  <div class="space-y-4">
    <!-- Dataset Selection Section -->
    <DatasetSelectionSection
      v-model:selected-datasets="selectedDatasets"
    />
    <!-- File Upload Section -->
    <FileUploadSection
      v-if="selectedDatasets.length === 0"
      v-model:selected-files="selectedFiles"
      v-model:error="error"
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