<script setup lang="ts">
import { computed } from 'vue'
import { TrendingUp, TrendingDown, BarChart3, Activity } from 'lucide-vue-next'
interface DistributionData {
  mean: number
  std: number
  p5: number
  p25: number
  median: number
  p75: number
  p95: number
}
const props = defineProps<{ 
  label: string
  distribution: DistributionData | null
  percentage?: boolean 
}>()
const hasData = computed(() => props.distribution !== null)
const formatValue = (value: number | null) => {
  if (value === null || value === undefined) return '—'
  const p = props.percentage ? (value * 100) : value
  const s = p.toFixed(2) + (props.percentage ? '%' : '')
  return s.startsWith('-') ? s : '+' + s
}
const medianValue = computed(() => props.distribution?.median ?? null)
const isPositive = computed(() => (medianValue.value ?? 0) >= 0)
const isNeutral = computed(() => medianValue.value === null || medianValue.value === 0)
const trendIcon = computed(() => {
  if (isNeutral.value) return Activity
  return isPositive.value ? TrendingUp : TrendingDown
})
const colorClasses = computed(() => {
  if (isNeutral.value) return 'text-muted-foreground'
  return isPositive.value ? 'text-trading-green' : 'text-trading-red'
})
const bgGradient = computed(() => {
  if (isNeutral.value) return 'from-muted/20 to-muted/10'
  return isPositive.value ? 'from-trading-green/10 to-trading-green/5' : 'from-trading-red/10 to-trading-red/5'
})
const confidenceRange = computed(() => {
  if (!hasData.value || !props.distribution) return null
  const p25 = formatValue(props.distribution.p25)
  const p75 = formatValue(props.distribution.p75)
  return `${p25} to ${p75}`
})
const volatility = computed(() => {
  if (!hasData.value || !props.distribution) return null
  return formatValue(props.distribution.std)
})
</script>
<template>
  <div class="group relative overflow-hidden rounded-xl border-0 p-6 shadow-medium hover-lift transition-smooth bg-gradient-to-br from-card via-card to-secondary/20 animate-fade-in">
    <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-smooth -translate-x-full group-hover:translate-x-full duration-1000"></div>
    <div :class="['absolute top-0 right-0 w-16 h-16 rounded-full -translate-y-8 translate-x-8 transition-smooth', `bg-gradient-to-br ${bgGradient}`]"></div>
    <div class="relative z-10 space-y-4">
      <div class="flex items-center justify-between">
        <div class="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {{ props.label }}
        </div>
        <div :class="['rounded-full p-1.5 transition-smooth', isNeutral ? 'bg-muted/20' : isPositive ? 'bg-trading-green/10' : 'bg-trading-red/10']">
          <component :is="trendIcon" :class="['size-3 transition-smooth', colorClasses]" />
        </div>
      </div>
      <div class="space-y-2">
        <div class="flex items-baseline gap-2">
          <div :class="['text-2xl font-bold tabular-nums transition-smooth group-hover:scale-105', colorClasses]">
            {{ formatValue(medianValue) }}
          </div>
          <div class="text-xs text-muted-foreground font-medium">
            median
          </div>
        </div>
        <div class="h-1.5 w-full bg-muted/20 rounded-full overflow-hidden">
          <div 
            :class="['h-full rounded-full transition-all duration-1000 ease-out', isNeutral ? 'bg-muted/40' : isPositive ? 'bg-gradient-to-r from-trading-green/40 to-trading-green/60' : 'bg-gradient-to-r from-trading-red/40 to-trading-red/60']"
            :style="{ width: isNeutral ? '50%' : isPositive ? '75%' : '25%' }"
          ></div>
        </div>
      </div>
      <div v-if="hasData && distribution" class="space-y-3 pt-2 border-t border-border/30">
        <div class="flex items-center justify-between text-xs">
          <span class="text-muted-foreground font-medium">50% Range:</span>
          <span class="font-mono text-foreground">{{ confidenceRange }}</span>
        </div>
        <div class="flex items-center justify-between text-xs">
          <span class="text-muted-foreground font-medium">Volatility:</span>
          <span class="font-mono text-foreground">{{ volatility }}</span>
        </div>
        <div class="grid grid-cols-2 gap-3 text-xs">
          <div class="space-y-1">
            <div class="text-muted-foreground font-medium">5th %ile</div>
            <div class="font-mono text-trading-red">{{ formatValue(distribution.p5) }}</div>
          </div>
          <div class="space-y-1">
            <div class="text-muted-foreground font-medium">95th %ile</div>
            <div class="font-mono text-trading-green">{{ formatValue(distribution.p95) }}</div>
          </div>
        </div>
      </div>
      <div v-else class="flex items-center justify-center py-4 text-muted-foreground">
        <div class="text-center space-y-2">
          <BarChart3 class="size-6 mx-auto opacity-50" />
          <div class="text-xs">No distribution data</div>
        </div>
      </div>
    </div>
    <div 
      v-if="hasData && !isNeutral && Math.abs(medianValue ?? 0) > (props.percentage ? 0.1 : 1000)"
      :class="['absolute inset-0 rounded-xl opacity-20 animate-pulse-glow', isPositive ? 'bg-trading-green/20' : 'bg-trading-red/20']"
    ></div>
  </div>
</template>
<style scoped>
@keyframes pulse-glow {
  0%, 100% { opacity: 0.1; }
  50% { opacity: 0.3; }
}
.animate-pulse-glow {
  animation: pulse-glow 2s ease-in-out infinite;
}
</style>