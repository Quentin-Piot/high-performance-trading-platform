<template>
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
              :model-value="params[p.key]"
              type="number"
              :min="p.min ?? undefined"
              :step="p.type==='float' ? 0.1 : 1"
              class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-blue/50"
              @update:model-value="(value: string | number) => $emit('update:params', { ...params, [p.key]: Number(value) })"
            />
          <div class="absolute inset-0 rounded-lg bg-gradient-to-r from-trading-blue/0 via-trading-blue/5 to-trading-blue/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Settings } from 'lucide-vue-next'
interface StrategyParam {
  key: string
  type: 'int' | 'float'
  min?: number
  max?: number
}
interface StrategyConfig {
  params: StrategyParam[]
}
interface Props {
  strategy: string
  params: Record<string, number>
  currentCfg: StrategyConfig
}
interface Emits {
  (e: 'update:params', params: Record<string, number>): void
}
defineProps<Props>()
defineEmits<Emits>()
const { t } = useI18n()
</script>