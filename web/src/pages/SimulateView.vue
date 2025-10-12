<script setup lang="ts">
import BacktestForm from "@/components/backtest/BacktestForm.vue";
import BacktestChart from "@/components/backtest/BacktestChart.vue";
import MultiLineChart from "@/components/backtest/MultiLineChart.vue";
import MetricsCard from "@/components/common/MetricsCard.vue";
import Spinner from "@/components/ui/spinner/Spinner.vue";
import { useBacktestStore } from "@/stores/backtestStore";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { RefreshCw, Download, BarChart3, LineChart } from "lucide-vue-next";
import TopNav from "@/components/common/TopNav.vue";
import { buildEquityPoints } from "@/composables/useEquitySeries";
// Local chart types avoiding dependency on lightweight-charts TS exports
type BusinessDay = { year: number; month: number; day: number };
type ChartTime = number | BusinessDay;
type ChartPoint = { time: ChartTime; value: number };
type LinePoint = { time: number; value: number };

const store = useBacktestStore();
const loading = computed(() => store.status === "loading");
const { t } = useI18n();
// Toolbar state and helpers
const selectedResolution = ref<"1m" | "5m" | "1h" | "1d">("1d");
const activeRange = ref<"1W" | "1M" | "YTD" | "All">("All");

type EquitySeries = ChartPoint[];

function timeToSeconds(p: ChartPoint): number {
    if (typeof p.time === "number") return p.time;
    const bd = p.time as BusinessDay;
    if (
        bd &&
        typeof bd.year === "number" &&
        typeof bd.month === "number" &&
        typeof bd.day === "number"
    ) {
        return Math.floor(Date.UTC(bd.year, bd.month - 1, bd.day) / 1000);
    }
    return Number(p.time) || 0;
}

function downsample(
    series: EquitySeries,
    resolution: "1m" | "5m" | "1h" | "1d",
): EquitySeries {
    const stepMap: Record<"1m" | "5m" | "1h" | "1d", number> = {
        "1m": 60,
        "5m": 300,
        "1h": 3600,
        "1d": 86400,
    };
    const step = stepMap[resolution];
    const out: EquitySeries = [];
    let bucketStart: number | null = null;
    for (const p of series) {
        const t = timeToSeconds(p);
        if (!Number.isFinite(t)) continue;
        if (bucketStart === null) bucketStart = t;
        const inBucket = t < bucketStart + step;
        if (!inBucket) {
            bucketStart = t;
            out.push(p);
        } else if (out.length === 0) {
            out.push(p);
        } else {
            out[out.length - 1] = p;
        }
    }
    return out;
}

function applyRange(
    series: EquitySeries,
    range: "1W" | "1M" | "YTD" | "All",
): EquitySeries {
    if (range === "All" || series.length === 0) return series;
    const times = series.map((s) => timeToSeconds(s)).filter(Number.isFinite);
    const maxTime = Math.max(...times);
    let cutoff = maxTime;
    if (range === "1W") cutoff = maxTime - 7 * 86400;
    else if (range === "1M") cutoff = maxTime - 30 * 86400;
    else if (range === "YTD") {
        const d = new Date(maxTime * 1000);
        const jan1 = Date.UTC(d.getUTCFullYear(), 0, 1) / 1000;
        cutoff = jan1;
    }
    return series.filter((s) => timeToSeconds(s) >= cutoff);
}

const displaySeries = computed<EquitySeries>(() => {
    const base: EquitySeries = store.equitySeries || [];
    const ranged = applyRange(base, activeRange.value);
    return downsample(ranged, selectedResolution.value);
});

const chartSeries = computed<LinePoint[]>(() =>
    displaySeries.value.map((p) => ({
        time: timeToSeconds(p),
        value: p.value,
    })),
);

// Computed properties pour le graphique multi-lignes
const hasMultipleResults = computed(() => store.isMultipleResults && store.results.length > 1);

// Données agrégées pour le graphique multi-lignes
const aggregatedData = computed<LinePoint[]>(() => {
    if (!hasMultipleResults.value || !store.results.length) return [];
    
    // Créer un map des timestamps vers les valeurs moyennes
    const timestampMap = new Map<number, { sum: number; count: number }>();
    
    // Parcourir tous les résultats pour calculer les moyennes
    store.results.forEach(result => {
        const points = buildEquityPoints(result.timestamps, result.equity_curve);
        points.forEach(point => {
            const existing = timestampMap.get(point.time);
            if (existing) {
                existing.sum += point.value;
                existing.count += 1;
            } else {
                timestampMap.set(point.time, { sum: point.value, count: 1 });
            }
        });
    });
    
    // Convertir en points de ligne avec moyennes
    const aggregatedPoints = Array.from(timestampMap.entries())
        .map(([time, { sum, count }]) => ({
            time,
            value: sum / count
        }))
        .sort((a, b) => a.time - b.time);
    
    return aggregatedPoints;
});

function downloadCsv() {
    const rows = [
        ["time", "value"],
        ...displaySeries.value.map((p) => [
            String(timeToSeconds(p)),
            String(p.value),
        ]),
    ];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "equity_series.csv";
    a.click();
    URL.revokeObjectURL(url);
}
</script>

<template>
    <main
        class="container mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-6 sm:space-y-10 animate-fade-in"
    >
        <TopNav />

        <!-- Header avec effet premium - responsive -->
        <header class="flex flex-col gap-2 animate-slide-up">
            <h1
                class="text-2xl sm:text-3xl font-bold tracking-tight bg-gradient-to-r from-primary via-trading-purple to-trading-cyan bg-clip-text text-transparent"
            >
                {{ t("simulate.header.title") }}
            </h1>
            <p class="text-sm sm:text-base text-muted-foreground">
                {{ t("simulate.header.subtitle") }}
            </p>
        </header>

        <!-- Layout: mobile empilé, desktop côte à côte -->
        <section
            class="flex flex-col lg:grid lg:grid-cols-3 gap-2 sm:gap-8 animate-scale-in"
            style="animation-delay: 0.2s"
        >
            <!-- Form panel avec design moderne - responsive -->
            <Card
                class="lg:col-span-1 order-1 lg:order-1 border-0 shadow-medium bg-gradient-to-br from-card via-card to-secondary/20"
            >
                <CardHeader class="pb-3 sm:pb-4 p-3 sm:p-4">
                    <CardTitle
                        class="flex items-center gap-2 sm:gap-3 text-lg sm:text-xl"
                    >
                        <div
                            class="rounded-lg sm:rounded-xl bg-trading-blue/10 p-2 text-trading-blue"
                        >
                            <BarChart3 class="size-4 sm:size-5" />
                        </div>
                        <span class="text-base sm:text-lg">{{
                            t("simulate.form.title")
                        }}</span>
                    </CardTitle>
                </CardHeader>
                <CardContent class="p-3 sm:p-4 pt-0">
                    <BacktestForm />
                </CardContent>
            </Card>

            <!-- Chart panel avec interface TradingView - responsive -->
            <div
                class="lg:col-span-2 order-2 lg:order-2 space-y-4 sm:space-y-6"
            >
                <!-- Error banner avec style moderne -->
                <div
                    v-if="store.status === 'error'"
                    class="rounded-lg sm:rounded-xl border border-trading-red/20 bg-trading-red/5 text-trading-red p-3 sm:p-4 shadow-soft animate-slide-up"
                >
                    <div class="flex items-center gap-2 sm:gap-3">
                        <div
                            class="rounded-full bg-trading-red/10 p-1.5 sm:p-2"
                        >
                            <RefreshCw class="size-3 sm:size-4" />
                        </div>
                        <span class="font-medium text-sm sm:text-base">{{
                            t("simulate.errors.backtest")
                        }}</span>
                    </div>
                </div>

                <!-- Chart card avec toolbar TradingView style - responsive -->
                <Card
                    class="border-0 shadow-strong bg-gradient-to-br from-card via-card to-secondary/10 overflow-hidden"
                >
                    <CardHeader
                        class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4 pb-3 sm:pb-4 p-3 sm:p-4"
                    >
                        <div class="space-y-1 flex-1">
                            <CardTitle
                                class="flex items-center gap-2 sm:gap-3 text-lg sm:text-xl"
                            >
                                <div
                                    class="rounded-lg sm:rounded-xl bg-trading-green/10 p-2 text-trading-green"
                                >
                                    <LineChart class="size-4 sm:size-5" />
                                </div>
                                <span class="text-base sm:text-lg">{{
                                    t("simulate.results.title")
                                }}</span>
                            </CardTitle>
                            <p
                                class="text-xs sm:text-sm text-muted-foreground hidden sm:block"
                            >
                                {{ t("simulate.header.subtitle") }}
                            </p>
                        </div>

                        <!-- Toolbar type TradingView avec design premium - mobile optimisé -->
                        <div
                            class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3 w-full sm:w-auto"
                        >
                            <!-- Sélecteur de résolution avec style moderne -->
                            <div class="flex items-center gap-2">
                                <Select v-model="selectedResolution">
                                    <SelectTrigger
                                        class="w-full sm:w-32 h-9 border-0 bg-secondary/50 hover:bg-secondary/70 transition-smooth shadow-soft text-sm"
                                    >
                                        <SelectValue
                                            :placeholder="
                                                t(
                                                    'simulate.chart.resolution.' +
                                                        selectedResolution,
                                                )
                                            "
                                        />
                                    </SelectTrigger>
                                    <SelectContent
                                        class="border-0 shadow-strong"
                                    >
                                        <SelectItem
                                            value="1m"
                                            class="hover:bg-trading-blue/10 text-sm"
                                            >{{
                                                t(
                                                    "simulate.chart.resolution.1m",
                                                )
                                            }}</SelectItem
                                        >
                                        <SelectItem
                                            value="5m"
                                            class="hover:bg-trading-blue/10 text-sm"
                                            >{{
                                                t(
                                                    "simulate.chart.resolution.5m",
                                                )
                                            }}</SelectItem
                                        >
                                        <SelectItem
                                            value="1h"
                                            class="hover:bg-trading-blue/10 text-sm"
                                            >{{
                                                t(
                                                    "simulate.chart.resolution.1h",
                                                )
                                            }}</SelectItem
                                        >
                                        <SelectItem
                                            value="1d"
                                            class="hover:bg-trading-blue/10 text-sm"
                                            >{{
                                                t(
                                                    "simulate.chart.resolution.1d",
                                                )
                                            }}</SelectItem
                                        >
                                    </SelectContent>
                                </Select>
                            </div>

                            <!-- Boutons de plage temporelle avec style TradingView - mobile adapté -->
                            <div
                                class="flex items-center gap-1 bg-secondary/30 rounded-lg p-1"
                            >
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    :class="[
                                        'rounded-md transition-smooth font-medium text-xs px-2 py-1 h-7',
                                        activeRange === '1W'
                                            ? 'bg-trading-blue text-white shadow-soft'
                                            : 'hover:bg-secondary/50',
                                    ]"
                                    @click="activeRange = '1W'"
                                >
                                    {{ t("simulate.chart.range.1W") }}
                                </Button>
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    :class="[
                                        'rounded-md transition-smooth font-medium text-xs px-2 py-1 h-7',
                                        activeRange === '1M'
                                            ? 'bg-trading-blue text-white shadow-soft'
                                            : 'hover:bg-secondary/50',
                                    ]"
                                    @click="activeRange = '1M'"
                                >
                                    {{ t("simulate.chart.range.1M") }}
                                </Button>
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    :class="[
                                        'rounded-md transition-smooth font-medium text-xs px-2 py-1 h-7 hidden sm:inline-flex',
                                        activeRange === 'YTD'
                                            ? 'bg-trading-blue text-white shadow-soft'
                                            : 'hover:bg-secondary/50',
                                    ]"
                                    @click="activeRange = 'YTD'"
                                >
                                    {{ t("simulate.chart.range.YTD") }}
                                </Button>
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    :class="[
                                        'rounded-md transition-smooth font-medium text-xs px-2 py-1 h-7',
                                        activeRange === 'All'
                                            ? 'bg-trading-blue text-white shadow-soft'
                                            : 'hover:bg-secondary/50',
                                    ]"
                                    @click="activeRange = 'All'"
                                >
                                    {{ t("simulate.chart.range.All") }}
                                </Button>
                            </div>

                            <!-- Actions avec effets visuels - mobile optimisé -->
                            <div class="flex items-center gap-1 sm:gap-2">
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    class="rounded-lg hover:bg-trading-green/10 hover:text-trading-green transition-smooth shadow-soft hover-scale h-9 w-9 p-0"
                                    @click="store.retryLast()"
                                >
                                    <RefreshCw class="size-4" />
                                </Button>
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    class="rounded-lg hover:bg-trading-purple/10 hover:text-trading-purple transition-smooth shadow-soft hover-scale h-9 w-9 p-0"
                                    @click="downloadCsv"
                                >
                                    <Download class="size-4" />
                                </Button>
                            </div>
                        </div>
                    </CardHeader>

                    <CardContent class="p-3 sm:p-4">
                        <div
                            v-if="loading"
                            class="h-[300px] sm:h-[400px] w-full relative overflow-hidden flex items-center justify-center"
                        >
                            <!-- Spinner moderne -->
                            <div class="flex flex-col items-center gap-3">
                                <Spinner class="h-8 w-8 text-trading-blue" />
                                <span class="text-sm text-muted-foreground">{{ t("simulate.loading") }}</span>
                            </div>
                        </div>
                        <div v-else>
                            <!-- Graphique multi-lignes pour plusieurs résultats -->
                            <MultiLineChart 
                                v-if="hasMultipleResults"
                                :results="store.results"
                                :aggregated-data="aggregatedData"
                            />
                            <!-- Graphique simple pour un seul résultat -->
                            <BacktestChart 
                                v-else
                                :series="chartSeries" 
                            />
                        </div>
                    </CardContent>
                </Card>

                <!-- KPI grid avec design premium - mobile responsive -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
                    <div
                        class="relative overflow-hidden rounded-lg sm:rounded-xl border-0 shadow-medium bg-gradient-to-br from-card to-trading-green/5"
                    >
                        <div
                            class="absolute top-0 right-0 w-16 sm:w-20 h-16 sm:h-20 bg-trading-green/10 rounded-full -translate-y-8 sm:-translate-y-10 translate-x-8 sm:translate-x-10"
                        ></div>
                        <MetricsCard
                            :label="t('simulate.metrics.pnl')"
                            :value="store.pnl"
                            percentage
                            class="relative z-10 bg-transparent border-0 shadow-none p-4 sm:p-6"
                        />
                    </div>

                    <div
                        class="relative overflow-hidden rounded-lg sm:rounded-xl border-0 shadow-medium bg-gradient-to-br from-card to-trading-red/5"
                    >
                        <div
                            class="absolute top-0 right-0 w-16 sm:w-20 h-16 sm:h-20 bg-trading-red/10 rounded-full -translate-y-8 sm:-translate-y-10 translate-x-8 sm:translate-x-10"
                        ></div>
                        <MetricsCard
                            :label="t('simulate.metrics.drawdown')"
                            :value="store.drawdown"
                            percentage
                            class="relative z-10 bg-transparent border-0 shadow-none p-4 sm:p-6"
                        />
                    </div>

                    <div
                        class="relative overflow-hidden rounded-lg sm:rounded-xl border-0 shadow-medium bg-gradient-to-br from-card to-trading-blue/5"
                    >
                        <div
                            class="absolute top-0 right-0 w-16 sm:w-20 h-16 sm:h-20 bg-trading-blue/10 rounded-full -translate-y-8 sm:-translate-y-10 translate-x-8 sm:translate-x-10"
                        ></div>
                        <MetricsCard
                            :label="t('simulate.metrics.sharpe')"
                            :value="store.sharpe"
                            class="relative z-10 bg-transparent border-0 shadow-none p-4 sm:p-6"
                        />
                    </div>
                </div>
            </div>
        </section>
    </main>
</template>

<style scoped>
/* Optimisations tactiles pour mobile */
@media (hover: none) and (pointer: coarse) {
    .hover-lift:hover {
        transform: none;
    }

    .hover-lift:active {
        transform: translateY(1px);
    }

    .hover-glow:hover {
        box-shadow: none;
    }

    .hover-scale:hover {
        transform: none;
    }

    .hover-scale:active {
        transform: scale(0.98);
    }

    /* Améliorer la zone de toucher pour les boutons */
    .hover-scale {
        min-height: 44px;
        min-width: 44px;
    }
}

/* Amélioration des performances sur mobile */
@media (max-width: 640px) {
    .shadow-strong {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .shadow-medium {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .shadow-soft {
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    }

    /* Réduire le blur pour les performances */
    .backdrop-blur-sm {
        backdrop-filter: blur(4px);
    }

    /* Optimiser les transitions sur mobile */
    .transition-smooth {
        transition: all 0.2s ease;
    }
}

/* Améliorer l'accessibilité tactile */
@media (max-width: 1024px) {
    /* Augmenter la taille des éléments interactifs */
    .SelectTrigger {
        min-height: 40px;
    }

    button {
        min-height: 40px;
    }

    /* Espacement amélioré pour le tactile */
    .gap-1 {
        gap: 0.375rem;
    }

    .gap-2 {
        gap: 0.625rem;
    }
}

/* Animation d'entrée optimisée pour mobile */
@media (prefers-reduced-motion: reduce) {
    .animate-fade-in,
    .animate-slide-up,
    .animate-scale-in {
        animation: none;
    }

    .transition-smooth {
        transition: none;
    }
}

/* Optimisation de la grille KPI sur très petits écrans */
@media (max-width: 480px) {
    .grid-cols-1 {
        gap: 0.75rem;
    }
}
</style>
