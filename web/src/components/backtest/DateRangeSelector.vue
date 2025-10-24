<template>
    <div class="space-y-4">
        <Label class="text-sm font-medium flex items-center gap-2">
            <div class="rounded-lg bg-trading-cyan/10 p-1.5 text-trading-cyan">
                <CalendarIcon class="size-3.5" />
            </div>
            {{ t("simulate.form.labels.date_range") }}
        </Label>
        <div class="flex flex-col gap-4">
            <div class="space-y-2">
                <Label class="text-xs text-muted-foreground">{{
                    t("simulate.form.labels.start_date")
                }}</Label>
                <Popover>
                    <PopoverTrigger as-child>
                        <Button
                            variant="outline"
                            :class="
                                cn(
                                    'w-full justify-start text-left font-normal',
                                    !startDateValue && 'text-muted-foreground',
                                )
                            "
                        >
                            <CalendarIcon class="mr-2 h-4 w-4" />
                            {{
                                startDateValue
                                    ? formatDate(startDateValue)
                                    : t(
                                          "simulate.form.placeholders.select_start_date",
                                      )
                            }}
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent class="w-auto p-0" align="start">
                        <Calendar
                            v-model="startDateValue"
                            initial-focus
                            @update:model-value="onStartDateChange"
                        />
                    </PopoverContent>
                </Popover>
            </div>
            <div class="space-y-2">
                <Label class="text-xs text-muted-foreground">{{
                    t("simulate.form.labels.end_date")
                }}</Label>
                <Popover>
                    <PopoverTrigger as-child>
                        <Button
                            variant="outline"
                            :class="
                                cn(
                                    'w-full justify-start text-left font-normal',
                                    !endDateValue && 'text-muted-foreground',
                                )
                            "
                        >
                            <CalendarIcon class="mr-2 h-4 w-4" />
                            {{
                                endDateValue
                                    ? formatDate(endDateValue)
                                    : t(
                                          "simulate.form.placeholders.select_end_date",
                                      )
                            }}
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent class="w-auto p-0" align="start">
                        <Calendar
                            v-model="endDateValue"
                            initial-focus
                            @update:model-value="onEndDateChange"
                        />
                    </PopoverContent>
                </Popover>
            </div>
        </div>
    </div>
</template>
<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { DateValue } from "@internationalized/date";
import { CalendarDate } from "@internationalized/date";
import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { CalendarIcon } from "lucide-vue-next";
interface Props {
    startDate: string;
    endDate: string;
}
interface Emits {
    (e: "update:startDate", date: string): void;
    (e: "update:endDate", date: string): void;
}
const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();
const startDateValue = computed({
    get: () => {
        if (!props.startDate) return undefined;
        const parts = props.startDate.split("-").map(Number);
        if (parts.length !== 3 || parts.some(isNaN)) return undefined;
        const [year, month, day] = parts;
        if (year === undefined || month === undefined || day === undefined)
            return undefined;
        return new CalendarDate(year, month, day);
    },
    set: (value: DateValue | undefined) => {
        if (value) {
            const dateStr = `${value.year}-${String(value.month).padStart(2, "0")}-${String(value.day).padStart(2, "0")}`;
            emit("update:startDate", dateStr);
        }
    },
});
const endDateValue = computed({
    get: () => {
        if (!props.endDate) return undefined;
        const parts = props.endDate.split("-").map(Number);
        if (parts.length !== 3 || parts.some(isNaN)) return undefined;
        const [year, month, day] = parts;
        if (year === undefined || month === undefined || day === undefined)
            return undefined;
        return new CalendarDate(year, month, day);
    },
    set: (value: DateValue | undefined) => {
        if (value) {
            const dateStr = `${value.year}-${String(value.month).padStart(2, "0")}-${String(value.day).padStart(2, "0")}`;
            emit("update:endDate", dateStr);
        }
    },
});
function formatDate(date: DateValue): string {
    return `${String(date.day).padStart(2, "0")}/${String(date.month).padStart(2, "0")}/${date.year}`;
}
function onStartDateChange(value: DateValue | undefined) {
    startDateValue.value = value;
}
function onEndDateChange(value: DateValue | undefined) {
    endDateValue.value = value;
}
</script>