<template>
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
        :model-value="selectedDatasets[0] || ''" 
        type="single" 
        variant="outline" 
        size="sm"
        :items-per-row="3"
        class="w-full"
        @update:model-value="(value: any) => onDatasetsChange(value ? [String(value)] : [])"
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
          {{ selectedDatasets.length }} dataset selected
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Label } from '@/components/ui/label'
import { MultiLineToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Database, CheckCircle } from 'lucide-vue-next'
import { AVAILABLE_DATASETS } from '@/config/datasets'

interface Props {
  selectedDatasets: string[]
}

interface Emits {
  (e: 'update:selectedDatasets', datasets: string[]): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const { t } = useI18n()

function onDatasetsChange(newDatasets: string[]) {
  emit('update:selectedDatasets', newDatasets)
}
</script>