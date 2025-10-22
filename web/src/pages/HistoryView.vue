<template>
  <div class="container mx-auto p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold">{{ t('history.title') }}</h1>
        <p class="text-muted-foreground mt-2">{{ t('history.description') }}</p>
      </div>
      <div class="flex items-center gap-4">
        <!-- Strategy Filter -->
        <Select v-model="selectedStrategy">
          <SelectTrigger class="w-48">
            <SelectValue :placeholder="t('history.filter_by_strategy')" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">{{ t('history.all_strategies') }}</SelectItem>
            <SelectItem value="sma_crossover">SMA Crossover</SelectItem>
            <SelectItem value="rsi">RSI</SelectItem>
          </SelectContent>
        </Select>
        
        <!-- Refresh Button -->
        <Button @click="loadHistory" :disabled="loading" variant="outline">
          <RefreshCw :class="{ 'animate-spin': loading }" class="w-4 h-4 mr-2" />
          {{ t('common.refresh') }}
        </Button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div v-if="stats" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <Card>
        <CardContent class="p-6">
          <div class="flex items-center">
            <BarChart3 class="h-8 w-8 text-blue-600" />
            <div class="ml-4">
              <p class="text-sm font-medium text-muted-foreground">{{ t('history.stats.total_backtests') }}</p>
              <p class="text-2xl font-bold">{{ stats.total_backtests }}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent class="p-6">
          <div class="flex items-center">
            <TrendingUp class="h-8 w-8 text-green-600" />
            <div class="ml-4">
              <p class="text-sm font-medium text-muted-foreground">{{ t('history.stats.avg_return') }}</p>
              <p class="text-2xl font-bold">
                {{ stats.avg_return ? `${stats.avg_return.toFixed(2)}%` : 'N/A' }}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent class="p-6">
          <div class="flex items-center">
            <Activity class="h-8 w-8 text-purple-600" />
            <div class="ml-4">
              <p class="text-sm font-medium text-muted-foreground">{{ t('history.stats.avg_sharpe') }}</p>
              <p class="text-2xl font-bold">
                {{ stats.avg_sharpe ? stats.avg_sharpe.toFixed(3) : 'N/A' }}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent class="p-6">
          <div class="flex items-center">
            <Zap class="h-8 w-8 text-orange-600" />
            <div class="ml-4">
              <p class="text-sm font-medium text-muted-foreground">{{ t('history.stats.monte_carlo_runs') }}</p>
              <p class="text-2xl font-bold">{{ stats.total_monte_carlo_runs }}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- History Table -->
    <Card>
      <CardHeader>
        <CardTitle>{{ t('history.backtest_history') }}</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="loading" class="flex items-center justify-center py-8">
          <Loader2 class="w-8 h-8 animate-spin" />
          <span class="ml-2">{{ t('common.loading') }}</span>
        </div>
        
        <div v-else-if="error" class="text-center py-8">
          <AlertCircle class="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p class="text-red-600">{{ error }}</p>
          <Button @click="loadHistory" class="mt-4" variant="outline">
            {{ t('common.retry') }}
          </Button>
        </div>
        
        <div v-else-if="!history.length" class="text-center py-8">
          <BarChart3 class="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p class="text-muted-foreground">{{ t('history.no_history') }}</p>
          <Button @click="navigateToSimulate" class="mt-4">
            {{ t('history.run_first_backtest') }}
          </Button>
        </div>
        
        <div v-else class="space-y-4">
          <!-- History Items -->
          <div v-for="item in history" :key="item.id" class="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-4 mb-2">
                  <Badge :variant="getStrategyVariant(item.strategy)">
                    {{ getStrategyLabel(item.strategy) }}
                  </Badge>
                  <Badge v-if="item.monte_carlo_runs > 1" variant="secondary">
                    Monte Carlo ({{ item.monte_carlo_runs }} runs)
                  </Badge>
                  <Badge :variant="getStatusVariant(item.status)">
                    {{ getStatusLabel(item.status) }}
                  </Badge>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 text-sm">
                  <div>
                    <p class="text-muted-foreground">{{ t('history.date_range') }}</p>
                    <p class="font-medium">
                      {{ item.start_date || 'N/A' }} - {{ item.end_date || 'N/A' }}
                    </p>
                  </div>
                  
                  <div v-if="item.total_return !== null">
                    <p class="text-muted-foreground">{{ t('history.total_return') }}</p>
                    <p class="font-medium" :class="getReturnColor(item.total_return)">
                      {{ item.total_return.toFixed(2) }}%
                    </p>
                  </div>
                  
                  <div v-if="item.sharpe_ratio !== null">
                    <p class="text-muted-foreground">{{ t('history.sharpe_ratio') }}</p>
                    <p class="font-medium">{{ item.sharpe_ratio.toFixed(3) }}</p>
                  </div>
                  
                  <div v-if="item.max_drawdown !== null">
                    <p class="text-muted-foreground">{{ t('history.max_drawdown') }}</p>
                    <p class="font-medium text-red-600">{{ item.max_drawdown.toFixed(2) }}%</p>
                  </div>
                  
                  <div>
                    <p class="text-muted-foreground">{{ t('history.created_at') }}</p>
                    <p class="font-medium">{{ formatDate(item.created_at) }}</p>
                  </div>
                </div>
                
                <!-- Strategy Parameters -->
                <div class="mt-3 text-xs text-muted-foreground">
                  <span class="font-medium">{{ t('history.parameters') }}:</span>
                  {{ formatStrategyParams(item.strategy_params) }}
                </div>
                
                <!-- Datasets Used -->
                <div v-if="item.datasets_used && item.datasets_used.length" class="mt-2 text-xs text-muted-foreground">
                  <span class="font-medium">{{ t('history.datasets') }}:</span>
                  {{ item.datasets_used.join(', ') }}
                </div>
              </div>
              
              <div class="flex items-center gap-2 ml-4">
                <Button @click="viewDetails(item)" variant="outline" size="sm">
                  <Eye class="w-4 h-4 mr-1" />
                  {{ t('history.view_details') }}
                </Button>
                
                <Button @click="rerunBacktest(item)" variant="outline" size="sm">
                  <Play class="w-4 h-4 mr-1" />
                  {{ t('history.rerun') }}
                </Button>
                
                <Button @click="deleteBacktest(item)" variant="destructive" size="sm">
                  <Trash2 class="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
          
          <!-- Pagination -->
          <div v-if="pagination.total > pagination.per_page" class="flex items-center justify-between pt-4">
            <p class="text-sm text-muted-foreground">
              {{ t('history.showing') }} {{ (pagination.page - 1) * pagination.per_page + 1 }} - 
              {{ Math.min(pagination.page * pagination.per_page, pagination.total) }} 
              {{ t('history.of') }} {{ pagination.total }} {{ t('history.results') }}
            </p>
            
            <div class="flex items-center gap-2">
              <Button 
                @click="loadHistory(pagination.page - 1)" 
                :disabled="!pagination.has_prev"
                variant="outline" 
                size="sm"
              >
                <ChevronLeft class="w-4 h-4" />
                {{ t('common.previous') }}
              </Button>
              
              <span class="px-3 py-1 text-sm">{{ pagination.page }}</span>
              
              <Button 
                @click="loadHistory(pagination.page + 1)" 
                :disabled="!pagination.has_next"
                variant="outline" 
                size="sm"
              >
                {{ t('common.next') }}
                <ChevronRight class="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from '@/router'
import { useI18n } from 'vue-i18n'
import { 
  Activity, 
  AlertCircle, 
  BarChart3, 
  ChevronLeft, 
  ChevronRight, 
  Eye, 
  Loader2, 
  Play, 
  RefreshCw, 
  TrendingUp, 
  Trash2, 
  Zap 
} from 'lucide-vue-next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

import { fetchJson } from '@/services/apiClient'

const { t } = useI18n()
const { navigate } = useRouter()

// State
const loading = ref(false)
const error = ref<string | null>(null)
const history = ref<any[]>([])
const stats = ref<any>(null)
const selectedStrategy = ref('')
const pagination = ref({
  page: 1,
  per_page: 20,
  total: 0,
  has_next: false,
  has_prev: false
})

// Load history data
const loadHistory = async (page = 1) => {
  loading.value = true
  error.value = null
  
  try {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: pagination.value.per_page.toString()
    })
    
    if (selectedStrategy.value) {
      params.set('strategy', selectedStrategy.value)
    }
    
    const response = await fetchJson<any>(`/history?${params.toString()}`)
    
    history.value = response.items
    pagination.value = {
      page: response.page,
      per_page: response.per_page,
      total: response.total,
      has_next: response.has_next,
      has_prev: response.has_prev
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load history'
  } finally {
    loading.value = false
  }
}

// Load user stats
const loadStats = async () => {
  try {
    const response = await fetchJson<any>('/history/stats')
    stats.value = response
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

// Helper functions
const getStrategyVariant = (strategy: string) => {
  switch (strategy) {
    case 'sma_crossover': return 'default'
    case 'rsi': return 'secondary'
    default: return 'outline'
  }
}

const getStrategyLabel = (strategy: string) => {
  switch (strategy) {
    case 'sma_crossover': return 'SMA Crossover'
    case 'rsi': return 'RSI'
    default: return strategy
  }
}

const getStatusVariant = (status: string) => {
  switch (status) {
    case 'completed': return 'default'
    case 'running': return 'secondary'
    case 'failed': return 'destructive'
    default: return 'outline'
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'completed': return t('history.status.completed')
    case 'running': return t('history.status.running')
    case 'failed': return t('history.status.failed')
    default: return status
  }
}

const getReturnColor = (returnValue: number) => {
  return returnValue >= 0 ? 'text-green-600' : 'text-red-600'
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString()
}

const formatStrategyParams = (params: any) => {
  const formatted = []
  if (params.sma_short) formatted.push(`Short SMA: ${params.sma_short}`)
  if (params.sma_long) formatted.push(`Long SMA: ${params.sma_long}`)
  if (params.period) formatted.push(`Period: ${params.period}`)
  if (params.overbought) formatted.push(`Overbought: ${params.overbought}`)
  if (params.oversold) formatted.push(`Oversold: ${params.oversold}`)
  return formatted.join(', ') || 'Default parameters'
}

// Actions
const viewDetails = (item: any) => {
  // Navigate to a detailed view or show modal
  navigate(`/history/${item.id}`)
}

const rerunBacktest = async (item: any) => {
  try {
    // Navigate to simulate page with pre-filled parameters
    const params = new URLSearchParams({
      strategy: item.strategy,
      start_date: item.start_date || '',
      end_date: item.end_date || '',
      ...item.strategy_params
    })
    
    navigate(`/simulate?${params.toString()}`)
  } catch (err) {
    console.error('Failed to rerun backtest:', err)
  }
}

const deleteBacktest = async (item: any) => {
  if (!confirm(t('history.confirm_delete'))) return
  
  try {
    await fetchJson(`/history/${item.id}`, { method: 'DELETE' })
    await loadHistory(pagination.value.page)
    await loadStats()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to delete backtest'
  }
}

const navigateToSimulate = () => {
  navigate('/simulate')
}

// Watchers
watch(selectedStrategy, () => {
  loadHistory(1)
})

// Lifecycle
onMounted(() => {
  loadHistory()
  loadStats()
})
</script>