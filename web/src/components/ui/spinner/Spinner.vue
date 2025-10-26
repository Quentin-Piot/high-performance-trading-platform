<script setup lang="ts">
import type { HTMLAttributes } from "vue";
import { VueSpinnerGridPop } from "vue3-spinners";
import { cn } from "@/lib/utils";

defineOptions({
    name: "SpinnerComponent",
});

const props = defineProps<{
    class?: HTMLAttributes["class"];
    size?: number;
    color?: string;
}>();
</script>

<template>
    <VueSpinnerGridPop
        role="status"
        aria-label="Loading"
        :class="cn('', props.class)"
        :size="props.size || 16"
        :color="props.color || '#535462'"
    />
</template>
