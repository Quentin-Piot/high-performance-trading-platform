<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import {
    createChart,
    ColorType,
    type ChartApi,
    type LineSeriesApi,
} from "lightweight-charts";
import { TrendingUp, Activity, BarChart3, Eye, EyeOff } from "lucide-vue-next";
import { useI18n } from "vue-i18n";
import type { BacktestResult } from "@/services/backtestService";

const { t } = useI18n();

type LinePoint = { time: number; value: number };

interface ChartSeries {
    id: string;
    name: string;
    data: LinePoint[];
    color: string;
    visible: boolean;
}

const props = defineProps<{
    results?: BacktestResult[];
    aggregatedData?: LinePoint[];
    activeRange?: "1W" | "1M" | "YTD" | "All";
}>();

const el = ref<HTMLDivElement | null>(null);
let chart: ChartApi | null = null;
const loaded = ref(false);
let ro: ResizeObserver | null = null;
const seriesMap = new Map<string, LineSeriesApi>();

// Couleurs distinctes pour chaque ligne
const colors = [
    "#10b981", // emerald-500
    "#3b82f6", // blue-500
    "#f59e0b", // amber-500
    "#ef4444", // red-500
    "#8b5cf6", // violet-500
    "#06b6d4", // cyan-500
    "#f97316", // orange-500
    "#84cc16", // lime-500
    "#ec4899", // pink-500
    "#6366f1", // indigo-500
];

const seriesVisibility = ref<Record<string, boolean>>({});

// Function to apply time range filtering to data points
function applyTimeRangeFilter(data: LinePoint[]): LinePoint[] {
    if (!props.activeRange || props.activeRange === "All" || data.length === 0) {
        return data;
    }

    const times = data.map(d => d.time);
    const maxTime = Math.max(...times);
    let cutoff = maxTime;

    if (props.activeRange === "1W") cutoff = maxTime - 7 * 86400;
    else if (props.activeRange === "1M") cutoff = maxTime - 30 * 86400;
    else if (props.activeRange === "YTD") {
        const d = new Date(maxTime * 1000);
        const jan1 = Date.UTC(d.getUTCFullYear(), 0, 1) / 1000;
        cutoff = jan1;
    }

    return data.filter(d => d.time >= cutoff);
}

const chartSeries = computed<ChartSeries[]>(() => {
    const series: ChartSeries[] = [];

    if (props.results) {
        props.results.forEach((result, index) => {
            let data = result.timestamps.map((timestamp, i) => ({
                time: Math.floor(new Date(timestamp).getTime() / 1000),
                value: result.equity_curve[i] || 0,
            }));

            // Apply time range filtering
            data = applyTimeRangeFilter(data);

            const seriesId = `result-${index}`;
            series.push({
                id: seriesId,
                name: result.filename.replace(/\.(csv|CSV)$/, ""),
                data,
                color: colors[index % colors.length] || "#10b981",
                visible: seriesVisibility.value[seriesId] !== false,
            });
        });
    }

    if (props.aggregatedData && props.aggregatedData.length > 0) {
        const aggregatedId = "aggregated";
        // Apply time range filtering to aggregated data
        const filteredAggregatedData = applyTimeRangeFilter(props.aggregatedData);
        
        series.push({
            id: aggregatedId,
            name: t("simulate.chart.aggregated"),
            data: filteredAggregatedData,
            color: "#1f2937", // gray-800
            visible: seriesVisibility.value[aggregatedId] !== false,
        });
    }

    return series;
});

watch(
    () => props.results,
    () => {
        if (props.results) {
            props.results.forEach((_, index) => {
                const seriesId = `result-${index}`;
                if (!(seriesId in seriesVisibility.value)) {
                    seriesVisibility.value[seriesId] = true;
                }
            });
        }
        if (props.aggregatedData && !("aggregated" in seriesVisibility.value)) {
            seriesVisibility.value["aggregated"] = true;
        }
    },
    { immediate: true },
);

const hasData = computed(() => chartSeries.value.length > 0);
const visibleSeries = computed(() =>
    chartSeries.value.filter((s) => s.visible),
);

function toggleSeriesVisibility(seriesId: string) {
    seriesVisibility.value[seriesId] = !seriesVisibility.value[seriesId];
    updateChartSeries();
}

function updateChartSeries() {
    if (!chart) return;

    seriesMap.forEach((series) => {
        try {
            (chart as any)?.removeSeries(series);
        } catch (error) {
            console.warn("Error removing series:", error);
        }
    });
    seriesMap.clear();

    visibleSeries.value.forEach((series) => {
        if (chart) {
            const lineSeries = chart.addLineSeries({
                color: series.color,
                lineWidth: series.id === "aggregated" ? 4 : 2,
                crosshairMarkerVisible: true,
                crosshairMarkerRadius: 4,
                priceLineVisible: false,
            } as any);

            lineSeries.setData(series.data);
            seriesMap.set(series.id, lineSeries);
        }
    });
}

onMounted(() => {
    if (!el.value) return;
    const rootEl = el.value!;
    const width = Math.max(
        320,
        rootEl.clientWidth || rootEl.getBoundingClientRect().width || 600,
    );

    const textColor = "#e2e8f0";
    const gridColor = "#1e293b";

    rootEl.style.color = textColor;
    chart = createChart(rootEl, {
        layout: {
            background: { type: ColorType.Solid, color: "transparent" },
            textColor,
        },
        width,
        height: 400,
        rightPriceScale: {
            borderVisible: false,
        },
        timeScale: {
            borderVisible: false,
            timeVisible: true,
            secondsVisible: false,
        },
        grid: {
            vertLines: { color: gridColor },
            horzLines: { color: gridColor },
        },
    });

    if (!chart) return;

    updateChartSeries();
    loaded.value = true;

    ro = new ResizeObserver(() => {
        if (rootEl && chart) {
            const w = Math.max(
                320,
                rootEl.clientWidth ||
                    rootEl.getBoundingClientRect().width ||
                    600,
            );
            chart.applyOptions({ width: w });
        }
    });
    ro.observe(rootEl);
});

onUnmounted(() => {
    chart?.remove();
    if (ro && el.value) ro.unobserve(el.value);
    chart = null;
    seriesMap.clear();
});

watch(
    () => [props.results, props.aggregatedData],
    () => {
        if (chart && loaded.value) {
            updateChartSeries();
        }
    },
    { deep: true },
);

watch(
    () => seriesVisibility.value,
    () => {
        if (chart && loaded.value) {
            updateChartSeries();
        }
    },
    { deep: true },
);
</script>

<template>
    <div class="relative group">
        <div class="flex items-center justify-between mb-4 px-2">
            <div class="flex items-center gap-3">
                <div
                    class="rounded-xl bg-trading-blue/10 p-2 text-trading-blue group-hover:bg-trading-blue/20 transition-smooth"
                >
                    <BarChart3 class="size-4" />
                </div>
                <div>
                    <h3 class="font-semibold text-sm">
                        {{ t("simulate.chart.multi_title") }}
                    </h3>
                    <p class="text-xs text-muted-foreground" v-if="hasData">
                        {{ visibleSeries.length }}
                        {{ t("simulate.chart.series_visible") }} /
                        {{ chartSeries.length }}
                        {{ t("simulate.chart.series_total") }}
                    </p>
                </div>
            </div>

            <div v-if="hasData" class="flex items-center gap-2 text-xs">
                <div
                    class="rounded-lg bg-trading-green/10 p-1.5 text-trading-green"
                >
                    <TrendingUp class="size-3" />
                </div>
                <span class="text-muted-foreground">{{
                    t("simulate.chart.multi_analysis")
                }}</span>
            </div>
        </div>

        <div
            v-if="hasData"
            class="mb-4 p-3 bg-secondary/20 rounded-lg border border-border/50"
        >
            <h4
                class="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide"
            >
                {{ t("simulate.chart.legend") }}
            </h4>
            <div class="flex flex-wrap gap-2">
                <button
                    v-for="series in chartSeries"
                    :key="series.id"
                    :class="[
                        'flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200',
                        'border border-transparent hover:border-border/50',
                        series.visible
                            ? 'bg-card shadow-sm'
                            : 'bg-muted/50 opacity-60 hover:opacity-80',
                    ]"
                    @click="toggleSeriesVisibility(series.id)"
                >
                    <div
                        class="w-3 h-0.5 rounded-full"
                        :style="{ backgroundColor: series.color }"
                    ></div>
                    <span
                        :class="
                            series.visible
                                ? 'text-foreground'
                                : 'text-muted-foreground'
                        "
                    >
                        {{ series.name }}
                    </span>
                    <component
                        :is="series.visible ? Eye : EyeOff"
                        class="size-3 opacity-60"
                    />
                </button>
            </div>
        </div>

        <div
            ref="el"
            class="w-full h-[400px] rounded-lg bg-card/50 border border-border/20 shadow-inner"
            :class="{ 'animate-pulse': !loaded }"
        />

        <div
            v-if="!hasData"
            class="absolute inset-0 flex items-center justify-center bg-card/80 rounded-lg border-2 border-dashed border-border/50"
        >
            <div class="text-center space-y-2">
                <Activity
                    class="size-8 text-muted-foreground mx-auto opacity-50"
                />
                <p class="text-sm text-muted-foreground">
                    {{ t("simulate.chart.no_data") }}
                </p>
            </div>
        </div>
    </div>
</template>
