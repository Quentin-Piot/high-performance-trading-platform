<template>
    <div class="space-y-2">
        <Label class="text-sm font-medium flex items-center gap-2">
            <div class="rounded-lg bg-trading-cyan/10 p-1.5 text-trading-cyan">
                <Database class="size-3.5" />
            </div>
            {{ t("simulate.form.labels.datasets") }}
        </Label>
        <div class="space-y-3">
            <p class="text-xs text-muted-foreground">
                {{ t("simulate.form.labels.datasets_description") }}
            </p>
            <MultiLineToggleGroup
                :model-value="selectedDatasets[0] || ''"
                type="single"
                variant="outline"
                size="sm"
                :items-per-row="3"
                class="w-full"
                @update:model-value="
                    (value: any) =>
                        onDatasetsChange(value ? [String(value)] : [])
                "
            >
                <ToggleGroupItem
                    v-for="dataset in AVAILABLE_DATASETS"
                    :key="dataset.id"
                    :value="dataset.id"
                    class="text-xs px-3 py-2 font-medium transition-all duration-200 rounded-lg border border-border bg-secondary/30 hover:bg-secondary/50 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground data-[state=on]:border-primary data-[state=on]:shadow-md data-[state=on]:scale-[1.02] data-[state=on]:font-semibold hover:data-[state=on]:opacity-90"
                >
                    {{ dataset.name }}
                </ToggleGroupItem>
            </MultiLineToggleGroup>
        </div>
    </div>
</template>
<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { Label } from "@/components/ui/label";
import {
	MultiLineToggleGroup,
	ToggleGroupItem,
} from "@/components/ui/toggle-group";
import { Database } from "lucide-vue-next";
import { AVAILABLE_DATASETS } from "@/config/datasets";
interface Props {
	selectedDatasets: string[];
}
interface Emits {
	(e: "update:selectedDatasets", datasets: string[]): void;
}
defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();
function onDatasetsChange(newDatasets: string[]) {
	emit("update:selectedDatasets", newDatasets);
}
</script>