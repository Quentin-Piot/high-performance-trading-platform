<template>
  <div class="space-y-2">
    <Label class="text-sm font-medium flex items-center gap-2">
      <div class="rounded-lg bg-trading-green/10 p-1.5 text-trading-green">
        <DollarSign class="size-3.5" />
      </div>
      {{ t('simulate.form.price_type.label') }}
    </Label>
    <div class="grid grid-cols-2 gap-2">
      <button
        type="button"
        :class="[
          'h-11 rounded-xl px-4 text-sm font-medium transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-trading-green/50',
          priceType === 'close'
            ? 'bg-gradient-to-r from-trading-green/20 to-trading-green/10 text-trading-green border-2 border-trading-green/30 shadow-medium'
            : 'bg-gradient-to-r from-secondary/30 to-accent/20 text-muted-foreground border-2 border-transparent hover:border-trading-green/20 shadow-soft hover:shadow-medium'
        ]"
        @click="$emit('update:priceType', 'close')"
      >
        {{ t('simulate.form.price_type.close') }}
      </button>
      <button
        type="button"
        :class="[
          'h-11 rounded-xl px-4 text-sm font-medium transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-trading-green/50',
          priceType === 'adj_close'
            ? 'bg-gradient-to-r from-trading-green/20 to-trading-green/10 text-trading-green border-2 border-trading-green/30 shadow-medium'
            : 'bg-gradient-to-r from-secondary/30 to-accent/20 text-muted-foreground border-2 border-transparent hover:border-trading-green/20 shadow-soft hover:shadow-medium'
        ]"
        @click="$emit('update:priceType', 'adj_close')"
      >
        {{ t('simulate.form.price_type.adj_close') }}
      </button>
    </div>
    <p class="text-xs text-muted-foreground">
      {{ t('simulate.form.price_type.description') }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Label } from '@/components/ui/label'
import { DollarSign } from 'lucide-vue-next'

interface Props {
  priceType: 'close' | 'adj_close'
}

interface Emits {
  (e: 'update:priceType', value: 'close' | 'adj_close'): void
}

defineProps<Props>()
defineEmits<Emits>()

const { t } = useI18n()
</script>