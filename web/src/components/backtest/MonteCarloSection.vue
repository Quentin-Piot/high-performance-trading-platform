<template>
  <div class="space-y-2">
    <Label class="text-sm font-medium flex items-center gap-2">
      <div class="rounded-lg bg-trading-purple/10 p-1.5 text-trading-purple">
        <TrendingUp class="size-3.5" />
      </div>
      {{ t('simulate.form.monte_carlo.title') }}
    </Label>
    <div class="space-y-4">
      <div class="space-y-2">
        <Label class="text-xs font-medium text-muted-foreground">
          {{ t('simulate.form.monte_carlo.runs') }}
        </Label>
        <div class="relative group">
          <Input
            :model-value="monteCarloRuns"
            type="number"
            :min="1"
            :max="20000"
            :step="1"
            class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-purple/50"
            @update:model-value="(value: string | number) => $emit('update:monteCarloRuns', Number(value))"
          />
          <div class="absolute inset-0 rounded-lg bg-gradient-to-r from-trading-purple/0 via-trading-purple/5 to-trading-purple/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
        </div>
        <p class="text-xs text-muted-foreground">{{ t('simulate.form.monte_carlo.runs_description') }}</p>
      </div>
      <div v-if="isMonteCarloEnabled" class="space-y-2">
        <Label class="text-xs font-medium text-muted-foreground">
          {{ t('simulate.form.monte_carlo.method') }}
        </Label>
        <MultiLineToggleGroup 
          :model-value="monteCarloMethod" 
          type="single" 
          variant="outline" 
          size="sm"
          :items-per-row="2"
          class="w-full"
          @update:model-value="(value: any) => $emit('update:monteCarloMethod', value as string)"
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
      <div v-if="isMonteCarloEnabled" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div v-if="monteCarloMethod === 'bootstrap'" class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground">
            {{ t('simulate.form.monte_carlo.sample_fraction') }}
          </Label>
          <div class="relative group">
            <Input
              :model-value="sampleFraction"
              type="number"
              :min="0.1"
              :max="2.0"
              :step="0.1"
              class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-purple/50"
              @update:model-value="(value: string | number) => $emit('update:sampleFraction', Number(value))"
            />
            <div class="absolute inset-0 rounded-lg bg-gradient-to-r from-trading-purple/0 via-trading-purple/5 to-trading-purple/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
          </div>
        </div>
        <div v-if="monteCarloMethod === 'gaussian'" class="space-y-2">
          <Label class="text-xs font-medium text-muted-foreground">
            {{ t('simulate.form.monte_carlo.gaussian_scale') }}
          </Label>
          <div class="relative group">
            <Input
              :model-value="gaussianScale"
              type="number"
              :min="0.1"
              :max="5.0"
              :step="0.1"
              class="h-10 border-0 bg-gradient-to-r from-secondary/30 to-accent/20 shadow-soft hover:shadow-medium focus:shadow-strong transition-all duration-300 focus:ring-2 focus:ring-trading-purple/50"
              @update:model-value="(value: string | number) => $emit('update:gaussianScale', Number(value))"
            />
            <div class="absolute inset-0 rounded-lg bg-gradient-to-r from-trading-purple/0 via-trading-purple/5 to-trading-purple/0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { MultiLineToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { TrendingUp } from 'lucide-vue-next'
interface Props {
  monteCarloRuns: number
  monteCarloMethod: string
  sampleFraction: number
  gaussianScale: number
  isMonteCarloEnabled: boolean
}
interface Emits {
  (e: 'update:monteCarloRuns', value: number): void
  (e: 'update:monteCarloMethod', value: string): void
  (e: 'update:sampleFraction', value: number): void
  (e: 'update:gaussianScale', value: number): void
}
defineProps<Props>()
defineEmits<Emits>()
const { t } = useI18n()
</script>