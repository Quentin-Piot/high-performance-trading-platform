<script setup lang="ts">
import { computed } from 'vue'
import { TrendingUp, TrendingDown, Minus } from 'lucide-vue-next'
const props = defineProps<{ label: string; value: number | null | undefined; percentage?: boolean }>()
const formattedValue = computed(() => {
  if (props.value === null || props.value === undefined) return '—'
  const p = props.percentage ? (props.value * 100) : props.value
  const s = p.toFixed(2) + (props.percentage ? '%' : '')
  return s.startsWith('-') ? s : '+' + s
})
const isPositive = computed(() => (props.value ?? 0) >= 0)
const isNeutral = computed(() => props.value === null || props.value === 0)
const trendIcon = computed(() => {
  if (isNeutral.value) return Minus
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
</script>
<template>
  <div class="group relative overflow-hidden rounded-xl border-0 p-6 shadow-medium hover-lift transition-smooth bg-gradient-to-br from-card via-card to-secondary/20 animate-fade-in">
    <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-smooth -translate-x-full group-hover:translate-x-full duration-1000"></div>
    <div :class="['absolute top-0 right-0 w-16 h-16 rounded-full -translate-y-8 translate-x-8 transition-smooth', `bg-gradient-to-br ${bgGradient}`]"></div>
    <div class="relative z-10 space-y-3">
      <div class="flex items-center justify-between">
        <div class="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {{ props.label }}
        </div>
        <div :class="['rounded-full p-1.5 transition-smooth', isNeutral ? 'bg-muted/20' : isPositive ? 'bg-trading-green/10' : 'bg-trading-red/10']">
          <component :is="trendIcon" :class="['size-3 transition-smooth', colorClasses]" />
        </div>
      </div>
      <div class="space-y-1">
        <div :class="['text-2xl font-bold tabular-nums transition-smooth group-hover:scale-105', colorClasses]">
          {{ formattedValue }}
        </div>
        <div class="h-1 w-full bg-muted/20 rounded-full overflow-hidden">
          <div 
            :class="['h-full rounded-full transition-all duration-1000 ease-out', isNeutral ? 'bg-muted/40' : isPositive ? 'bg-trading-green/60' : 'bg-trading-red/60']"
            :style="{ width: isNeutral ? '50%' : isPositive ? '75%' : '25%' }"
          ></div>
        </div>
      </div>
    </div>
    <div 
      v-if="!isNeutral && Math.abs(props.value ?? 0) > (props.percentage ? 0.1 : 1000)"
      :class="['absolute inset-0 rounded-xl opacity-20 animate-pulse-glow', isPositive ? 'bg-trading-green/20' : 'bg-trading-red/20']"
    ></div>
  </div>
</template>