<script setup lang="ts">
import type { PrimitiveProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import type { ButtonVariants } from "."
import { Primitive } from "reka-ui"
import { cn } from "@/lib/utils"
import { buttonVariants } from "."

interface Props extends PrimitiveProps {
  variant?: ButtonVariants["variant"]
  size?: ButtonVariants["size"]
  class?: HTMLAttributes["class"]
}

const props = withDefaults(defineProps<Props>(), {
  as: "button",
  variant: "default",
  size: "default",
  class: undefined,
})

// Ensure listeners/attrs like @click are forwarded to the underlying element
defineOptions({ name: 'UiButton', inheritAttrs: false })
</script>

<template>
  <Primitive
    data-slot="button"
    :as="as"
    :as-child="asChild"
    v-bind="$attrs"
    :class="cn('cursor-pointer', buttonVariants({ variant, size }), props.class)"
  >
    <slot />
  </Primitive>
</template>
