<template>
    <div class="space-y-4">
        <Label class="text-sm font-medium flex items-center gap-2">
            <div class="rounded-lg bg-trading-cyan/10 p-1.5 text-trading-cyan">
                <CalendarIcon class="size-3.5" />
            </div>
            {{ t("simulate.form.labels.date_range") }}
        </Label>
        <div v-if="availableDateRange && !dateValidationError" class="text-xs text-muted-foreground bg-blue-50/50 dark:bg-blue-900/20 p-3 rounded-lg border border-blue-200/50 dark:border-blue-800/50">
            <div class="flex items-center gap-2 mb-1">
                <CalendarIcon class="size-3" />
                <span class="font-medium">{{ t("simulate.form.labels.available_date_range") }}</span>
            </div>
            <span>{{ t('errors.date_validation.available_range', { 
              minDate: formatDateString(availableDateRange.minDate), 
              maxDate: formatDateString(availableDateRange.maxDate) 
            }) }}</span>
        </div>
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
                                    startDateError && 'border-red-500 text-red-600'
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
                            :min-value="minDateValue"
                            :max-value="maxStartDateValue"
                            :is-date-disabled="isStartDateDisabled"
                            @update:model-value="onStartDateChange"
                        />
                    </PopoverContent>
                </Popover>
                <div v-if="startDateError" class="text-xs text-red-600 flex items-center gap-1 mt-1">
                    <AlertCircle class="size-3" />
                    <span class="text-xs">{{ startDateError }}</span>
                </div>
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
                                    endDateError && 'border-red-500 text-red-600'
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
                            :min-value="minEndDateValue"
                            :max-value="maxDateValue"
                            :is-date-disabled="isEndDateDisabled"
                            @update:model-value="onEndDateChange"
                        />
                    </PopoverContent>
                </Popover>
                <div v-if="endDateError" class="text-xs text-red-600 flex items-center gap-1 mt-1">
                    <AlertCircle class="size-3" />
                    <span class="text-xs">{{ endDateError }}</span>
                </div>
            </div>
        </div>
        <div v-if="dateValidationError" class="rounded-lg border border-red-200/50 bg-red-50/50 dark:bg-red-900/20 dark:border-red-800/50 text-red-700 dark:text-red-300 p-3">
            <div class="flex items-center gap-2 mb-1">
                <AlertCircle class="size-3" />
                <span class="text-xs font-medium">{{ t('errors.date_validation.title') }}</span>
            </div>
            <div class="text-xs">{{ dateValidationError }}</div>
            <div v-if="availableDateRange" class="text-xs text-muted-foreground mt-2 pt-2 border-t border-red-200/30 dark:border-red-800/30">
                <span class="font-medium">{{ t("simulate.form.labels.available_date_range") }}:</span>
                {{ t('errors.date_validation.available_range', { 
                  minDate: formatDateString(availableDateRange.minDate), 
                  maxDate: formatDateString(availableDateRange.maxDate) 
                }) }}
            </div>
        </div>
    </div>
</template>
<script setup lang="ts">
import { computed, watch, ref } from "vue";
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
import { CalendarIcon, AlertCircle } from "lucide-vue-next";
import { calculateDateRangeWithCsvFiles, type DateRange } from "@/services/frontendDateValidationService";
interface Props {
    startDate: string;
    endDate: string;
    startDateValue?: DateValue;
    endDateValue?: DateValue;
    selectedDatasets: string[];
    dateValidationError?: string | null;
}
interface Emits {
    (e: "update:startDate", date: string): void;
    (e: "update:endDate", date: string): void;
    (e: "update:startDateValue", date: DateValue | undefined): void;
    (e: "update:endDateValue", date: DateValue | undefined): void;
}
const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();
const startDateError = ref<string | null>(null);
const endDateError = ref<string | null>(null);
const availableDateRange = ref<DateRange | null>(null);
const startDateValue = computed({
    get: () => {
        if (props.startDateValue) return props.startDateValue;
        if (!props.startDate) return undefined;
        const parts = props.startDate.split("-").map(Number);
        if (parts.length !== 3 || parts.some(isNaN)) return undefined;
        const [year, month, day] = parts;
        if (year === undefined || month === undefined || day === undefined)
            return undefined;
        return new CalendarDate(year, month, day);
    },
    set: (value: DateValue | undefined) => {
        emit("update:startDateValue", value);
        if (value) {
            const dateStr = `${value.year}-${String(value.month).padStart(2, "0")}-${String(value.day).padStart(2, "0")}`;
            emit("update:startDate", dateStr);
        }
    },
});
const endDateValue = computed({
    get: () => {
        if (props.endDateValue) return props.endDateValue;
        if (!props.endDate) return undefined;
        const parts = props.endDate.split("-").map(Number);
        if (parts.length !== 3 || parts.some(isNaN)) return undefined;
        const [year, month, day] = parts;
        if (year === undefined || month === undefined || day === undefined)
            return undefined;
        return new CalendarDate(year, month, day);
    },
    set: (value: DateValue | undefined) => {
        emit("update:endDateValue", value);
        if (value) {
            const dateStr = `${value.year}-${String(value.month).padStart(2, "0")}-${String(value.day).padStart(2, "0")}`;
            emit("update:endDate", dateStr);
        }
    },
});
const minDateValue = computed(() => {
    if (!availableDateRange.value) return undefined;
    const parts = availableDateRange.value.minDate.split("-").map(Number);
    if (parts.length !== 3 || parts.some(isNaN)) return undefined;
    const [year, month, day] = parts;
    return new CalendarDate(year, month, day);
});
const maxDateValue = computed(() => {
    if (!availableDateRange.value) return undefined;
    const parts = availableDateRange.value.maxDate.split("-").map(Number);
    if (parts.length !== 3 || parts.some(isNaN)) return undefined;
    const [year, month, day] = parts;
    return new CalendarDate(year, month, day);
});
const maxStartDateValue = computed(() => {
    if (endDateValue.value && maxDateValue.value) {
        return endDateValue.value.compare(maxDateValue.value) <= 0 ? endDateValue.value : maxDateValue.value;
    }
    return maxDateValue.value;
});
const minEndDateValue = computed(() => {
    if (startDateValue.value && minDateValue.value) {
        return startDateValue.value.compare(minDateValue.value) >= 0 ? startDateValue.value : minDateValue.value;
    }
    return minDateValue.value;
});
function isStartDateDisabled(date: DateValue): boolean {
    if (!availableDateRange.value) return false;
    const dateStr = `${date.year}-${String(date.month).padStart(2, "0")}-${String(date.day).padStart(2, "0")}`;
    const dateObj = new Date(dateStr);
    const minDate = new Date(availableDateRange.value.minDate);
    const maxDate = new Date(availableDateRange.value.maxDate);
    if (dateObj < minDate || dateObj > maxDate) return true;
    if (endDateValue.value) {
        const endDateStr = `${endDateValue.value.year}-${String(endDateValue.value.month).padStart(2, "0")}-${String(endDateValue.value.day).padStart(2, "0")}`;
        const endDateObj = new Date(endDateStr);
        if (dateObj > endDateObj) return true;
    }
    return false;
}
function isEndDateDisabled(date: DateValue): boolean {
    if (!availableDateRange.value) return false;
    const dateStr = `${date.year}-${String(date.month).padStart(2, "0")}-${String(date.day).padStart(2, "0")}`;
    const dateObj = new Date(dateStr);
    const minDate = new Date(availableDateRange.value.minDate);
    const maxDate = new Date(availableDateRange.value.maxDate);
    if (dateObj < minDate || dateObj > maxDate) return true;
    if (startDateValue.value) {
        const startDateStr = `${startDateValue.value.year}-${String(startDateValue.value.month).padStart(2, "0")}-${String(startDateValue.value.day).padStart(2, "0")}`;
        const startDateObj = new Date(startDateStr);
        if (dateObj < startDateObj) return true;
    }
    return false;
}
function formatDate(date: DateValue): string {
    return `${String(date.day).padStart(2, "0")}/${String(date.month).padStart(2, "0")}/${date.year}`;
}
function formatDateString(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR');
}
function onStartDateChange(value: DateValue | undefined) {
    startDateError.value = null;
    if (value && availableDateRange.value) {
        const dateStr = `${value.year}-${String(value.month).padStart(2, "0")}-${String(value.day).padStart(2, "0")}`;
        const dateObj = new Date(dateStr);
        const minDate = new Date(availableDateRange.value.minDate);
        const maxDate = new Date(availableDateRange.value.maxDate);
        if (dateObj < minDate) {
            startDateError.value = t("errors.date_validation.date_outside_range");
            return;
        }
        if (dateObj > maxDate) {
            startDateError.value = t("errors.date_validation.date_outside_range");
            return;
        }
        if (endDateValue.value) {
            const endDateStr = `${endDateValue.value.year}-${String(endDateValue.value.month).padStart(2, "0")}-${String(endDateValue.value.day).padStart(2, "0")}`;
            const endDateObj = new Date(endDateStr);
            if (dateObj > endDateObj) {
                startDateError.value = t("errors.date_validation.end_before_start");
                return;
            }
        }
    }
    startDateValue.value = value;
}
function onEndDateChange(value: DateValue | undefined) {
    endDateError.value = null;
    if (value && availableDateRange.value) {
        const dateStr = `${value.year}-${String(value.month).padStart(2, "0")}-${String(value.day).padStart(2, "0")}`;
        const dateObj = new Date(dateStr);
        const minDate = new Date(availableDateRange.value.minDate);
        const maxDate = new Date(availableDateRange.value.maxDate);
        if (dateObj < minDate) {
            endDateError.value = t("errors.date_validation.date_outside_range");
            return;
        }
        if (dateObj > maxDate) {
            endDateError.value = t("errors.date_validation.date_outside_range");
            return;
        }
        if (startDateValue.value) {
            const startDateStr = `${startDateValue.value.year}-${String(startDateValue.value.month).padStart(2, "0")}-${String(startDateValue.value.day).padStart(2, "0")}`;
            const startDateObj = new Date(startDateStr);
            if (dateObj < startDateObj) {
                endDateError.value = t("errors.date_validation.end_before_start");
                return;
            }
        }
    }
    endDateValue.value = value;
}
watch(() => props.selectedDatasets, async (newDatasets) => {
    if (newDatasets.length > 0) {
        const range = await calculateDateRangeWithCsvFiles(newDatasets, []);
        availableDateRange.value = range;
    } else {
        availableDateRange.value = null;
    }
}, { immediate: true });
</script>