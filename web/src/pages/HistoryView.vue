<template>
  <BaseLayout>
    <section class="animate-scale-in" style="animation-delay: 0.1s">
      <Card class="border-0 shadow-medium bg-gradient-to-br from-card via-card to-secondary/20 mb-6">
        <CardHeader class="pb-3 sm:pb-4 p-4 sm:p-6">
          <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div class="space-y-1">
              <CardTitle class="flex items-center gap-3 text-2xl sm:text-3xl">
                <div class="rounded-xl bg-trading-cyan/10 p-3 text-trading-cyan">
                  <BarChart3 class="size-6 sm:size-7" />
                </div>
                <span>{{ t('history.title') }}</span>
              </CardTitle>
              <p class="text-muted-foreground text-sm sm:text-base">{{ t('history.description') }}</p>
            </div>
            <div class="flex items-center gap-3 w-full sm:w-auto">
              <Select v-model="selectedStrategy">
                <SelectTrigger class="w-full sm:w-48 border-0 bg-secondary/50 hover:bg-secondary/70 transition-smooth shadow-soft">
                  <SelectValue :placeholder="t('history.filter_by_strategy')" />
                </SelectTrigger>
                <SelectContent class="border-0 shadow-strong">
                  <SelectItem value="all">{{ t('history.all_strategies') }}</SelectItem>
                  <SelectItem
                    v-for="strategy in BACKTEST_STRATEGIES"
                    :key="strategy.id"
                    :value="strategy.id"
                  >
                    {{ strategy.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <Button 
                :disabled="loading" 
                variant="ghost" 
                size="sm"
                class="rounded-lg hover:bg-trading-green/10 hover:text-trading-green transition-smooth shadow-soft hover-scale h-10 w-10 p-0"
                @click="loadHistory"
              >
                <RefreshCw :class="{ 'animate-spin': loading }" class="size-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>
    </section>
    <section v-if="stats" class="animate-scale-in mb-6" style="animation-delay: 0.2s">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card class="border-0 shadow-medium bg-gradient-to-br from-card via-card to-secondary/10 hover:shadow-strong transition-all duration-300 hover-scale">
          <CardContent class="p-3">
            <div class="flex items-center">
              <div class="rounded-xl bg-trading-blue/10 p-3 text-trading-blue">
                <BarChart3 class="size-6 sm:size-7" />
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-muted-foreground">{{ t('history.stats.total_backtests') }}</p>
                <p class="text-2xl font-bold">{{ stats.total_backtests }}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card class="border-0 shadow-medium bg-gradient-to-br from-card via-card to-secondary/10 hover:shadow-strong transition-all duration-300 hover-scale">
          <CardContent class="p-3">
            <div class="flex items-center">
              <div class="rounded-xl bg-trading-green/10 p-3 text-trading-green">
                <TrendingUp class="size-6 sm:size-7" />
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-muted-foreground">{{ t('history.stats.avg_return') }}</p>
                <p class="text-2xl font-bold">
                  {{ stats.avg_return ? `${stats.avg_return.toFixed(2)}%` : 'N/A' }}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card class="border-0 shadow-medium bg-gradient-to-br from-card via-card to-secondary/10 hover:shadow-strong transition-all duration-300 hover-scale">
          <CardContent class="p-3">
            <div class="flex items-center">
              <div class="rounded-xl bg-trading-purple/10 p-3 text-trading-purple">
                <Activity class="size-6 sm:size-7" />
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-muted-foreground">{{ t('history.stats.avg_sharpe') }}</p>
                <p class="text-2xl font-bold">
                  {{ stats.avg_sharpe ? stats.avg_sharpe.toFixed(3) : 'N/A' }}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card class="border-0 shadow-medium bg-gradient-to-br from-card via-card to-secondary/10 hover:shadow-strong transition-all duration-300 hover-scale">
          <CardContent class="p-3">
            <div class="flex items-center">
              <div class="rounded-xl bg-trading-orange/10 p-3 text-trading-orange">
                <Zap class="size-6 sm:size-7" />
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-muted-foreground">{{ t('history.stats.monte_carlo_runs') }}</p>
                <p class="text-2xl font-bold">{{ stats.total_monte_carlo_runs }}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
    <section class="animate-scale-in" style="animation-delay: 0.3s">
      <Card class="border-0 shadow-strong bg-gradient-to-br from-card via-card to-secondary/10 overflow-hidden">
        <CardHeader class="pb-3 sm:pb-4 p-4 sm:p-6">
          <CardTitle class="flex items-center gap-3 text-xl">
            <div class="rounded-xl bg-trading-cyan/10 p-2 text-trading-cyan">
              <BarChart3 class="size-5" />
            </div>
            {{ t('history.backtest_history') }}
          </CardTitle>
        </CardHeader>
        <CardContent class="p-4 sm:p-6 pt-0">
          <div v-if="loading" class="flex items-center justify-center py-12">
            <div class="flex flex-col items-center gap-3">
              <Loader2 class="size-8 animate-spin text-trading-blue" />
              <span class="text-sm text-muted-foreground">{{ t('common.loading') }}</span>
            </div>
          </div>
          <div v-else-if="error" class="text-center py-12">
            <div class="rounded-xl bg-trading-red/5 text-trading-red p-4 shadow-soft animate-slide-up">
              <div class="flex items-center justify-center gap-3 mb-4">
                <div class="rounded-full bg-trading-red/10 p-2">
                  <AlertCircle class="size-6" />
                </div>
                <span class="font-medium">{{ error }}</span>
              </div>
              <Button variant="outline" size="sm" class="border-trading-red/20 hover:border-trading-red hover:bg-trading-red/5 hover:text-trading-red" @click="loadHistory">
                {{ t('common.retry') }}
              </Button>
            </div>
          </div>
          <div v-else-if="!history.length" class="text-center py-12">
            <div class="flex flex-col items-center gap-4">
              <div class="rounded-xl bg-secondary/50 p-4">
                <BarChart3 class="size-12 text-muted-foreground" />
              </div>
              <div class="space-y-2">
                <p class="text-muted-foreground">{{ t('history.no_history') }}</p>
                <Button class="bg-trading-blue hover:bg-trading-blue/90 transition-smooth shadow-soft hover-scale" @click="navigateToSimulate">
                  {{ t('history.run_first_backtest') }}
                </Button>
              </div>
            </div>
          </div>
        <div v-else class="space-y-4">
          <div v-for="item in history" :key="item.id" class="border-0 rounded-xl p-4 sm:p-6 bg-gradient-to-br from-secondary/30 via-secondary/20 to-secondary/10 hover:shadow-medium transition-all duration-300 hover-scale shadow-soft">
            <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
              <div class="flex-1 w-full">
                <div class="flex flex-wrap items-center gap-2 mb-4">
                  <Badge :variant="getStrategyVariant(item.strategy)" class="rounded-lg px-3 py-1 font-medium shadow-soft">
                    {{ getStrategyLabel(item.strategy) }}
                  </Badge>
                  <Badge v-if="item.monte_carlo_runs > 1" variant="secondary" class="rounded-lg px-3 py-1 font-medium shadow-soft border-trading-purple/30 text-trading-purple">
                    Monte Carlo ({{ item.monte_carlo_runs }} runs)
                  </Badge>
                  <Badge :variant="getStatusVariant(item.status)" class="rounded-lg px-3 py-1 font-medium shadow-soft">
                    {{ getStatusLabel(item.status) }}
                  </Badge>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 text-sm mb-4">
                  <div class="space-y-1">
                    <p class="text-muted-foreground font-medium">{{ t('history.date_range') }}</p>
                    <p class="font-semibold text-foreground">
                      {{ item.start_date || 'N/A' }} - {{ item.end_date || 'N/A' }}
                    </p>
                  </div>
                  <div v-if="item.total_return !== null" class="space-y-1">
                    <p class="text-muted-foreground font-medium">{{ t('history.total_return') }}</p>
                    <p class="font-bold text-lg" :class="getReturnColor(item.total_return)">
                      {{ item.total_return.toFixed(2) }}%
                    </p>
                  </div>
                  <div v-if="item.sharpe_ratio !== null" class="space-y-1">
                    <p class="text-muted-foreground font-medium">{{ t('history.sharpe_ratio') }}</p>
                    <p class="font-bold text-lg text-trading-purple">{{ item.sharpe_ratio.toFixed(3) }}</p>
                  </div>
                  <div v-if="item.max_drawdown !== null" class="space-y-1">
                    <p class="text-muted-foreground font-medium">{{ t('history.max_drawdown') }}</p>
                    <p class="font-bold text-lg text-trading-red">{{ item.max_drawdown.toFixed(2) }}%</p>
                  </div>
                  <div class="space-y-1">
                    <p class="text-muted-foreground font-medium">{{ t('history.created_at') }}</p>
                    <p class="font-semibold text-foreground">{{ formatDate(item.created_at) }}</p>
                  </div>
                </div>
                <div class="mt-3 p-3 rounded-lg bg-secondary/30 text-xs">
                  <span class="font-semibold text-trading-blue">{{ t('history.parameters') }}:</span>
                  <span class="text-muted-foreground ml-2">{{ formatStrategyParams(item.strategy_params) }}</span>
                </div>
                <div v-if="item.datasets_used && item.datasets_used.length" class="mt-2 p-3 rounded-lg bg-secondary/30 text-xs">
                  <span class="font-semibold text-trading-cyan">{{ t('history.datasets') }}:</span>
                  <span class="text-muted-foreground ml-2">{{ item.datasets_used.join(', ') }}</span>
                </div>
              </div>
              <div class="flex flex-wrap items-center gap-2 w-full lg:w-auto">
                <Button 
                  size="sm" 
                  class="h-10 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white font-semibold shadow-lg shadow-blue-500/25 transition-all duration-300 border-0"
                  @click="rerunBacktest(item)"
                >
                  <div class="flex items-center gap-2">
                    <Play class="size-4" />
                    {{ t('history.rerun') }}
                  </div>
                </Button>
                <AlertDialog>
                  <AlertDialogTrigger as-child>
                    <Button variant="destructive" size="sm" class="rounded-lg border-0 bg-trading-red/10 hover:bg-trading-red/20 text-trading-red hover:text-trading-red transition-smooth shadow-soft hover-scale">
                      <Trash2 class="size-4" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent class="border-0 shadow-strong bg-gradient-to-br from-card via-card to-secondary/10">
                    <AlertDialogHeader>
                      <AlertDialogTitle class="flex items-center gap-3 text-trading-red">
                        <div class="rounded-full bg-trading-red/10 p-2">
                          <Trash2 class="size-5" />
                        </div>
                        {{ t('history.confirm_delete_title') }}
                      </AlertDialogTitle>
                      <AlertDialogDescription class="text-muted-foreground">
                        {{ t('history.confirm_delete_description') }}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel class="rounded-lg border-0 bg-secondary/50 hover:bg-secondary/70 transition-smooth shadow-soft">
                        {{ t('common.cancel') }}
                      </AlertDialogCancel>
                      <AlertDialogAction 
                        class="rounded-lg border-0 bg-trading-red hover:bg-trading-red/90 text-white transition-smooth shadow-soft hover-scale"
                        @click="confirmDelete(item.id)"
                      >
                        {{ t('common.delete') }}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>
          </div>
          <div v-if="pagination.total > pagination.per_page" class="pt-6">
            <Card class="border-0 shadow-medium bg-gradient-to-br from-card via-card to-secondary/10">
              <CardContent class="p-4 sm:p-6">
                <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
                  <p class="text-sm text-muted-foreground font-medium">
                    {{ t('history.showing') }} {{ (pagination.page - 1) * pagination.per_page + 1 }} - 
                    {{ Math.min(pagination.page * pagination.per_page, pagination.total) }} 
                    {{ t('history.of') }} {{ pagination.total }} {{ t('history.results') }}
                  </p>
                  <div class="flex items-center gap-3">
                    <Button 
                      :disabled="!pagination.has_prev" 
                      variant="outline"
                      size="sm" 
                      class="rounded-lg border-0 bg-secondary/50 hover:bg-secondary/70 transition-smooth shadow-soft hover-scale"
                      @click="loadHistory(pagination.page - 1)"
                    >
                      <ChevronLeft class="size-4" />
                      {{ t('common.previous') }}
                    </Button>
                    <span class="text-sm font-medium px-3 py-1 rounded-lg bg-trading-blue/10 text-trading-blue">{{ pagination.page }}</span>
                    <Button 
                      :disabled="!pagination.has_next" 
                      variant="outline"
                      size="sm" 
                      class="rounded-lg border-0 bg-secondary/50 hover:bg-secondary/70 transition-smooth shadow-soft hover-scale"
                      @click="loadHistory(pagination.page + 1)"
                    >
                      {{ t('common.next') }}
                      <ChevronRight class="size-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
        </CardContent>
      </Card>
    </section>
  </BaseLayout>
</template>
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from '@/router'
import { useI18n } from 'vue-i18n'
import { BACKTEST_STRATEGIES, type StrategyId } from '@/config/backtestStrategies'
import {
  BarChart3,
  TrendingUp,
  Activity,
  Zap,
  RefreshCw,
  Loader2,
  AlertCircle,
  Play,
  Trash2,
  ChevronLeft,
  ChevronRight
} from 'lucide-vue-next'
import BaseLayout from '@/components/layouts/BaseLayout.vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { 
  AlertDialog, 
  AlertDialogAction, 
  AlertDialogCancel, 
  AlertDialogContent, 
  AlertDialogDescription, 
  AlertDialogFooter, 
  AlertDialogHeader, 
  AlertDialogTitle, 
  AlertDialogTrigger 
} from '@/components/ui/alert-dialog'
import { fetchJson } from '@/services/apiClient'
const { t } = useI18n()
const { navigate } = useRouter()
const loading = ref(false)
const error = ref<string | null>(null)
const history = ref<any[]>([])
const stats = ref<any>(null)
const selectedStrategy = ref('all')
const pagination = ref({
  page: 1,
  per_page: 10,
  total: 0,
  has_prev: false,
  has_next: false
})
const loadHistory = async (page = 1) => {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: pagination.value.per_page.toString()
    })
    if (selectedStrategy.value && selectedStrategy.value !== 'all') {
      params.append('strategy', selectedStrategy.value)
    }
    const response = await fetchJson<any>(`/history/?${params}`)
    history.value = response.items || []
    pagination.value = {
      page: response.page || pagination.value.page,
      per_page: response.per_page || pagination.value.per_page,
      total: response.total || pagination.value.total,
      has_prev: response.has_prev || pagination.value.has_prev,
      has_next: response.has_next || pagination.value.has_next
    }
  } catch (err: any) {
    error.value = err.message || t('history.error_loading')
  } finally {
    loading.value = false
  }
}
const loadStats = async () => {
  try {
    const response = await fetchJson<any>('/history/stats')
    stats.value = response
  } catch (err: any) {
    console.error('Error loading stats:', err)
  }
}
const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString()
}
const getStrategyVariant = (strategyId: StrategyId) => {
  const variants: Record<StrategyId, 'default' | 'secondary' | 'outline'> = {
    'sma_crossover': 'default',
    'rsi': 'secondary'
  };
  return variants[strategyId] || 'default' as const;
}
const getStatusVariant = (status: string) => {
  const variants = {
    'completed': 'default' as const,
    'running': 'secondary' as const,
    'failed': 'destructive' as const
  }
  return variants[status as keyof typeof variants] || 'outline' as const
}
const getStrategyLabel = (strategyId: StrategyId) => {
  const strategyConfig = BACKTEST_STRATEGIES[strategyId];
  return strategyConfig?.name || strategyId;
}
const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    'completed': t('history.status.completed'),
    'running': t('history.status.running'),
    'failed': t('history.status.failed')
  }
  return labels[status] || status
}
const getReturnColor = (returnValue: number) => {
  if (returnValue > 0) return 'text-trading-green'
  if (returnValue < 0) return 'text-trading-red'
  return 'text-muted-foreground'
}
const formatStrategyParams = (params: any) => {
  if (!params) return 'N/A'
  return Object.entries(params)
    .filter(([, value]) => value !== null && value !== undefined && value !== '')
    .map(([key, value]) => `${key}: ${value}`)
    .join(', ')
}
const rerunBacktest = (item: any) => {
  const queryParams: Record<string, string | number | undefined> = {
    strategy: item.strategy,
    startDate: item.start_date,
    endDate: item.end_date,
    monteCarloRuns: item.monte_carlo_runs,
    monteCarloMethod: item.monte_carlo_method,
    sampleFraction: item.sample_fraction,
    gaussianScale: item.gaussian_scale,
    priceType: item.price_type,
    datasets: item.datasets_used && item.datasets_used.length > 0 ? item.datasets_used.join(',') : undefined
  };

  const strategyConfig = BACKTEST_STRATEGIES[item.strategy];
  if (strategyConfig && item.strategy_params) {
    for (const p of strategyConfig.params) {
      if (item.strategy_params[p.key] !== null && item.strategy_params[p.key] !== undefined) {
        queryParams[p.key] = item.strategy_params[p.key];
      }
    }
  }

  const filteredQueryParams = Object.fromEntries(
    Object.entries(queryParams).filter(([, value]) => value !== null && value !== undefined && value !== '')
  );

  const queryString = new URLSearchParams(
    Object.entries(filteredQueryParams).map(([key, value]) => [key, String(value)])
  ).toString();

  navigate(`/simulate?${queryString}`);
}
const confirmDelete = async (id: string) => {
  try {
    await fetchJson(`/history/${id}`, { method: 'DELETE' })
    await loadHistory()
    await loadStats()
  } catch (err: any) {
    error.value = err.message || t('history.error_deleting')
  }
}
const navigateToSimulate = () => {
  navigate('/simulate')
}
watch(selectedStrategy, () => {
  pagination.value.page = 1
  loadHistory()
})
onMounted(() => {
  loadHistory()
  loadStats()
})
</script>