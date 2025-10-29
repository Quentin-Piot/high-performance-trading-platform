<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import {
  ProgressIndicator,
  ProgressRoot,

} from "reka-ui"
import { cn } from "@/lib/utils"

defineOptions({ name: "UiProgress" })

type Variant = "default" | "gradient"

const props = withDefaults(defineProps<{ value?: number; class?: HTMLAttributes["class"]; variant?: Variant }>(), {
  value: 0,
  variant: "default",
  class: "",
})

const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <ProgressRoot
    data-slot="progress"
    :value="props.value"
    v-bind="delegatedProps"
    :class="
      cn(
        props.variant === 'gradient'
          ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20'
          : 'bg-primary/20',
        'relative h-2 w-full overflow-hidden rounded-full',
        props.class,
      )
    "
  >
    <ProgressIndicator
      data-slot="progress-indicator"
      :class="
        cn(
          props.variant === 'gradient'
            ? 'bg-gradient-to-r from-blue-500 to-purple-500'
            : 'bg-primary',
          'h-full w-full flex-1 transition-all',
        )
      "
      :style="`transform: translateX(-${100 - (props.value ?? 0)}%);`"
    />
  </ProgressRoot>
</template>
