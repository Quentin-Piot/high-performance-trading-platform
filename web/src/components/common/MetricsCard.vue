<script setup lang="ts">
const props = defineProps<{ label: string; value: number | null; percentage?: boolean }>()
function fmt(n: number | null) {
  if (n === null || n === undefined) return '—'
  const p = props.percentage ? (n * 100) : n
  const s = p.toFixed(2) + (props.percentage ? '%' : '')
  return s.startsWith('-') ? s : '+' + s
}
</script>

<template>
  <div class="rounded-md border p-3">
    <div class="text-xs text-muted-foreground">{{ props.label }}</div>
    <div :class="['text-lg font-semibold tabular-nums', (props.value ?? 0) >= 0 ? 'text-emerald-500' : 'text-red-500']">{{ fmt(props.value) }}</div>
  </div>
</template>