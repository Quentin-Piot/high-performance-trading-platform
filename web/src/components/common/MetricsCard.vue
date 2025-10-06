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
  <div class="rounded-xl border p-4 shadow-sm transition-all hover:shadow-md bg-card text-card-foreground">
    <div class="text-xs text-muted-foreground">{{ props.label }}</div>
    <div :class="['text-2xl font-semibold tabular-nums', (props.value ?? 0) >= 0 ? 'text-emerald-500' : 'text-red-500']">{{ fmt(props.value) }}</div>
  </div>
</template>