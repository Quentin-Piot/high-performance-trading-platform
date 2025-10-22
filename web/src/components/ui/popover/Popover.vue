<script setup lang="ts">
import { PopoverRoot, type PopoverRootEmits, type PopoverRootProps, useForwardPropsEmits } from "reka-ui"

defineOptions({
  name: 'PopoverComponent'
})

const props = defineProps<PopoverRootProps>()
const emits = defineEmits<PopoverRootEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <PopoverRoot
    data-slot="popover"
    v-bind="forwarded"
  >
    <slot />
  </PopoverRoot>
</template>
