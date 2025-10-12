<script setup lang="ts">
import type { VariantProps } from "class-variance-authority"
import type { ToggleGroupRootEmits, ToggleGroupRootProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import type { toggleVariants } from '@/components/ui/toggle'
import { reactiveOmit } from "@vueuse/core"
import { ToggleGroupRoot, useForwardPropsEmits } from "reka-ui"
import { provide } from "vue"
import { cn } from "@/lib/utils"

type ToggleGroupVariants = VariantProps<typeof toggleVariants>

const props = defineProps<ToggleGroupRootProps & {
  class?: HTMLAttributes["class"]
  variant?: ToggleGroupVariants["variant"]
  size?: ToggleGroupVariants["size"]
  /** Maximum number of items per row before wrapping */
  itemsPerRow?: number
  /** Gap between items */
  gap?: string
}>()
const emits = defineEmits<ToggleGroupRootEmits>()

provide("toggleGroup", {
  variant: props.variant,
  size: props.size,
})

const delegatedProps = reactiveOmit(props, "class", "size", "variant", "itemsPerRow", "gap")
const forwarded = useForwardPropsEmits(delegatedProps, emits)

// Calculate grid template columns based on itemsPerRow
const gridCols = props.itemsPerRow ? `repeat(${props.itemsPerRow}, 1fr)` : 'repeat(auto-fit, minmax(120px, 1fr))'
const gapClass = props.gap || 'gap-2'
</script>

<template>
  <ToggleGroupRoot
    v-slot="slotProps"
    data-slot="toggle-group"
    :data-size="size"
    :data-variant="variant"
    v-bind="forwarded"
    :class="cn(
      'group/toggle-group grid w-full rounded-md data-[variant=outline]:shadow-xs',
      gapClass,
      props.class
    )"
    :style="{ gridTemplateColumns: gridCols }"
  >
    <slot v-bind="slotProps" />
  </ToggleGroupRoot>
</template>