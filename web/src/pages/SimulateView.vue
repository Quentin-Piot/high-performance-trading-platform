<script setup lang="ts">
import BacktestForm from "@/components/backtest/BacktestForm.vue";
import BacktestChart from "@/components/backtest/BacktestChart.vue";
import MultiLineChart from "@/components/backtest/MultiLineChart.vue";
import EquityEnvelopeChart from "@/components/backtest/EquityEnvelopeChart.vue";
import MetricsCard from "@/components/common/MetricsCard.vue";
import DistributionMetricsCard from "@/components/common/DistributionMetricsCard.vue";
import Spinner from "@/components/ui/spinner/Spinner.vue";
import { useBacktestStore } from "@/stores/backtestStore";
import { computed, ref, watch, onBeforeUnmount } from "vue";
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
import { RefreshCw, Download, BarChart3, LineChart, Activity, Clock, Zap, Wifi } from "lucide-vue-next";
import BaseLayout from "@/components/layouts/BaseLayout.vue";
import { buildEquityPoints } from "@/composables/useEquitySeries";
import { buildWsUrl } from "@/services/apiClient";
import { toast } from "vue-sonner";
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

// --- Monte Carlo progress via WebSocket ---
const mcWs = ref<WebSocket | null>(null);
const mcConnected = ref(false);
const mcConnecting = ref(false);
const mcActiveJobId = ref<string | null>(null);
const mcStatus = ref("");
const mcPercent = ref(0);
const mcCurrent = ref(0);
const mcTotal = ref(0);
const mcEtaSeconds = ref<number | null>(null);
const mcProgressVisible = computed(() => !!store.monteCarloJobId);

// Nouvelles variables pour les informations détaillées du WebSocket
const mcJobSubmissionTime = ref<number | null>(null);
const mcWsConnectionTime = ref<number | null>(null);
const mcFirstMessageTime = ref<number | null>(null);
const mcJobStartTime = ref<number | null>(null);
const mcMessageCount = ref(0);
const mcSpeed = ref<number | null>(null);
const mcConnectionDelay = ref<number | null>(null);
const mcProcessingDelay = ref<number | null>(null);
const mcTotalDuration = ref<number | null>(null);
const mcShowDetailedInfo = ref(false);

function formatEta(sec: number | null): string {
    if (sec == null) return "";
    const s = Math.max(0, Math.round(sec));
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}m ${rem}s`;
}

const mcStatusLabel = computed(() => {
    const s = (mcStatus.value || "").toUpperCase();
    if (s.includes("PROCESSING")) return "En cours";
    if (s.includes("QUEUED") || s.includes("PENDING")) return "En file";
    if (s.includes("COMPLETED")) return "Terminé";
    if (s.includes("FAILED")) return "Échec";
    if (s.includes("CANCELLED")) return "Annulé";
    return mcStatus.value || "";
});

function connectMonteCarloWs(jobId: string) {
    try {
        const url = buildWsUrl(`/monte-carlo/jobs/${jobId}/progress`);
        // Guard: avoid multiple simultaneous connection attempts for the same job
        if (mcConnecting.value) {
            console.log("Skipping WebSocket connect: already connecting");
            return;
        }
        if (
            mcWs.value &&
            (mcWs.value.readyState === WebSocket.OPEN ||
                mcWs.value.readyState === WebSocket.CONNECTING) &&
            mcActiveJobId.value === jobId
        ) {
            console.log("WebSocket already open/connecting for this job, skipping");
            return;
        }

        console.log(`Connecting to WebSocket: ${url}`);

        // Close any previous socket if it was for a different job or is closed
        if (mcWs.value && mcActiveJobId.value !== jobId) {
            try {
                mcWs.value.close();
            } catch {
                /* ignore */
            }
            mcWs.value = null;
            mcConnected.value = false;
        }
        
        // Initialiser les timings (sauf mcJobSubmissionTime qui est déjà défini)
        mcMessageCount.value = 0;
        mcSpeed.value = null;
        mcConnectionDelay.value = null;
        mcProcessingDelay.value = null;
        mcTotalDuration.value = null;
        
        // 🔧 CORRECTION: Réinitialiser les valeurs de progression pour éviter d'afficher les valeurs du run précédent
        mcCurrent.value = 0;
        // 🎯 NOUVELLE FONCTIONNALITÉ: Initialiser mcTotal avec le nombre de runs du store si disponible
        mcTotal.value = store.monteCarloJobRuns || 0;
        mcPercent.value = 0;
        mcStatus.value = "";
        mcEtaSeconds.value = null;
        
        mcConnecting.value = true;
        mcActiveJobId.value = jobId;
        mcWs.value = new WebSocket(url);
        
        mcWs.value.onopen = () => {
            console.log("WebSocket connected successfully");
            mcConnected.value = true;
            mcConnecting.value = false;
            mcWsConnectionTime.value = Date.now();
            mcConnectionDelay.value = (mcWsConnectionTime.value - mcJobSubmissionTime.value!) / 1000;
            
            toast.success("Worker Monte Carlo connecté", {
                description: "Streaming de la progression en temps réel.",
            });
        };
        
        mcWs.value.onmessage = (evt) => {
            try {
                const msg = JSON.parse(evt.data);
                console.log("WebSocket message received:", msg);
                
                mcMessageCount.value++;
                const messageTime = Date.now();
                
                // Marquer le premier message
                if (mcFirstMessageTime.value === null) {
                    mcFirstMessageTime.value = messageTime;
                    console.log(`🎯 PREMIER MESSAGE REÇU! (délai depuis soumission: ${((messageTime - mcJobSubmissionTime.value!) / 1000).toFixed(3)}s)`);
                }
                
                // Détecter le message de connexion
                if (msg.status === "connecting") {
                    console.log(`🔗 Msg#${mcMessageCount.value} (+${((messageTime - mcJobSubmissionTime.value!) / 1000).toFixed(3)}s): CONNEXION - ${msg.message || 'Connexion établie'}`);
                    return; // Ne pas traiter ce message comme un message de progression
                }
                
                mcStatus.value = String(msg.status || "");
                const p = Number(msg.progress ?? 0);
                mcPercent.value = Math.max(
                    0,
                    Math.min(100, Math.round(p * 100)),
                );
                mcCurrent.value = Number(msg.current_run ?? 0);
                // 🎯 AMÉLIORATION: Mettre à jour mcTotal seulement si le message contient total_runs, sinon garder la valeur initiale
                if (msg.total_runs !== undefined && msg.total_runs !== null) {
                    mcTotal.value = Number(msg.total_runs);
                }
                
                // Détecter le début du traitement
                if (mcJobStartTime.value === null && mcCurrent.value > 0) {
                    mcJobStartTime.value = messageTime;
                    mcProcessingDelay.value = (mcJobStartTime.value - mcJobSubmissionTime.value!) / 1000;
                    console.log(`🏃 DÉBUT DU TRAITEMENT DÉTECTÉ! (délai: ${mcProcessingDelay.value.toFixed(3)}s)`);
                }
                
                // Calculer la vitesse
                if (mcJobStartTime.value && mcCurrent.value > 0) {
                    const processingTime = (messageTime - mcJobStartTime.value) / 1000;
                    mcSpeed.value = mcCurrent.value / processingTime;
                }
                
                // Log de progression avec timing comme dans le script Python
                const msgDelay = (messageTime - mcJobSubmissionTime.value!) / 1000;
                const progressPercent = Math.round((Number(msg.progress) || 0) * 100 * 10) / 10;
                
                if (mcCurrent.value > 0 && mcTotal.value > 0) {
                    const speedStr = mcSpeed.value ? ` (${mcSpeed.value.toFixed(1)} runs/s)` : "";
                    const etaStr = msg.eta_seconds ? ` (ETA: ${msg.eta_seconds}s)` : "";
                    console.log(`📊 Msg#${mcMessageCount.value} (+${msgDelay.toFixed(3)}s): ${msg.status} - ${mcCurrent.value}/${mcTotal.value} runs (${progressPercent}%)${speedStr}${etaStr}`);
                } else {
                    console.log(`📊 Msg#${mcMessageCount.value} (+${msgDelay.toFixed(3)}s): ${msg.status} - ${progressPercent}%`);
                }
                
                // Log spécial pour détecter les messages problématiques
                if (mcCurrent.value === 0 && mcTotal.value === 0 && mcMessageCount.value > 1) {
                    console.log(`⚠️  Message avec 0/0 runs détecté! Contenu:`, msg);
                }
                
                // Support both eta_seconds and estimated_completion_time
                if (typeof msg.eta_seconds === "number") {
                    mcEtaSeconds.value = msg.eta_seconds;
                } else if (msg.estimated_completion_time) {
                    const etaMs = Date.parse(
                        String(msg.estimated_completion_time),
                    );
                    if (!Number.isNaN(etaMs)) {
                        const diffSec = Math.max(
                            0,
                            Math.round((etaMs - Date.now()) / 1000),
                        );
                        mcEtaSeconds.value = diffSec;
                    } else {
                        mcEtaSeconds.value = null;
                    }
                } else {
                    mcEtaSeconds.value = null;
                }

                const term = (mcStatus.value || "").toUpperCase();
                if (mcCurrent.value === 1 && mcTotal.value > 0) {
                    toast.info("Job Monte Carlo démarré", {
                        description: `${mcTotal.value} runs en cours…`,
                    });
                }
                if (
                    term.includes("COMPLETED") ||
                    term.includes("FAILED") ||
                    term.includes("CANCELLED")
                ) {
                    // Calculer la durée totale
                    mcTotalDuration.value = (Date.now() - mcJobSubmissionTime.value!) / 1000;
                    
                    console.log(`🏁 Job terminé avec le statut: ${term} (durée totale: ${mcTotalDuration.value.toFixed(3)}s)`);
                    
                    try {
                        mcWs.value?.close();
                    } catch {
                        /* ignore */
                    }
                    
                    // Clear the job ID to hide progress bar and prevent reconnection
                    store.monteCarloJobId = null;
                    mcActiveJobId.value = null;
                    
                    if (term.includes("COMPLETED")) {
                        toast.success("Monte Carlo terminé", {
                            description: `${mcTotal.value} runs terminés en ${mcTotalDuration.value?.toFixed(1)}s`,
                        });
                    } else if (term.includes("FAILED")) {
                        toast.error("Monte Carlo échoué", {
                            description:
                                "Consultez les logs du worker pour plus de détails.",
                        });
                    } else if (term.includes("CANCELLED")) {
                        toast.warning("Monte Carlo annulé", {
                            description: "Le job a été interrompu.",
                        });
                    }
                    
                    // Return early to prevent retry logic from running
                    return;
                }
            } catch (error) {
                console.error("Error parsing WebSocket message:", error);
            }
        };
        
        mcWs.value.onclose = (event) => {
            console.log("WebSocket closed:", event.code, event.reason);
            mcConnected.value = false;
            mcConnecting.value = false;
            
            // Don't retry if job is cleared (terminal state reached)
            if (!store.monteCarloJobId) {
                console.log("Job completed, not retrying WebSocket connection");
                return;
            }
        };
        
        mcWs.value.onerror = (error) => {
            console.error("WebSocket error:", error);
            mcConnecting.value = false;
            toast.error("Erreur de connexion WebSocket", {
                description: "Impossible de se connecter au serveur. Vérifiez que le backend est démarré.",
            });
        };
        
        // Retry connection after a delay if it fails (only if job is still active)
        setTimeout(() => {
            if (
                !mcConnected.value &&
                mcWs.value?.readyState !== WebSocket.OPEN &&
                store.monteCarloJobId &&
                !mcConnecting.value
            ) {
                console.log("WebSocket connection failed, retrying...");
                toast.warning("Reconnexion au worker…", {
                    description: "Tentative de reconnexion en cours.",
                });
                // Retry once after 2 seconds
                setTimeout(() => {
                    if (!mcConnected.value && store.monteCarloJobId && !mcConnecting.value) {
                        connectMonteCarloWs(jobId);
                    }
                }, 2000);
            }
        }, 1500);
    } catch (error) {
        console.error("Error creating WebSocket connection:", error);
        mcConnecting.value = false;
        toast.error("Erreur WebSocket", {
            description: "Impossible de créer la connexion WebSocket.",
        });
    }
}

watch(
    () => store.monteCarloJobId,
    (jobId) => {
        if (jobId && jobId !== mcActiveJobId.value) {
            // Initialiser le timing de soumission du job dès qu'on a l'ID
            mcJobSubmissionTime.value = Date.now();
            connectMonteCarloWs(jobId);
        }
    },
);
watch(loading, (isLoading) => {
    if (isLoading && store.monteCarloJobId && !mcConnected.value && !mcConnecting.value) {
        connectMonteCarloWs(store.monteCarloJobId);
    }
});

onBeforeUnmount(() => {
    try {
        mcWs.value?.close();
    } catch {
        /* ignore */
    }
});

const chartSeries = computed<LinePoint[]>(() =>
    displaySeries.value.map((p) => ({
        time: timeToSeconds(p),
        value: p.value,
    })),
);

// Computed properties pour le graphique multi-lignes
const hasMultipleResults = computed(
    () => store.isMultipleResults && store.results.length > 1,
);
const hasMonteCarloResults = computed(() => {
    return store.isMonteCarloResults && store.monteCarloResults.length > 0;
});

// Données agrégées pour le graphique multi-lignes
const aggregatedData = computed<LinePoint[]>(() => {
    if (!hasMultipleResults.value || !store.results.length) return [];

    // Créer un map des timestamps vers les valeurs moyennes
    const timestampMap = new Map<number, { sum: number; count: number }>();

    // Parcourir tous les résultats pour calculer les moyennes
    store.results.forEach((result) => {
        const points = buildEquityPoints(
            result.timestamps,
            result.equity_curve,
        );
        points.forEach((point) => {
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
    let aggregatedPoints = Array.from(timestampMap.entries())
        .map(([time, { sum, count }]) => ({
            time,
            value: sum / count,
        }))
        .sort((a, b) => a.time - b.time);

    // Appliquer le filtrage par plage temporelle
    if (activeRange.value !== "All" && aggregatedPoints.length > 0) {
        const times = aggregatedPoints.map((p) => p.time);
        const maxTime = Math.max(...times);
        let cutoff = maxTime;

        if (activeRange.value === "1W") cutoff = maxTime - 7 * 86400;
        else if (activeRange.value === "1M") cutoff = maxTime - 30 * 86400;
        else if (activeRange.value === "YTD") {
            const d = new Date(maxTime * 1000);
            const jan1 = Date.UTC(d.getUTCFullYear(), 0, 1) / 1000;
            cutoff = jan1;
        }

        aggregatedPoints = aggregatedPoints.filter((p) => p.time >= cutoff);
    }

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
    <BaseLayout>
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

                    <CardContent class="p-3 sm:p-4 relative">
                        <!-- Overlay de progression Monte Carlo (visible même hors état de chargement) -->
                        <div
                            v-if="mcProgressVisible"
                            class="absolute inset-x-0 top-0 z-10 p-3 sm:p-4"
                        >
                            <div
                                class="rounded-lg bg-gradient-to-r from-trading-blue/10 to-trading-purple/10 border border-secondary/40 shadow-soft"
                            >
                                <div
                                    class="flex items-center justify-between gap-3 p-2"
                                >
                                    <div
                                        class="text-xs sm:text-sm text-muted-foreground"
                                    >
                                        {{
                                            t(
                                                "simulate.results.monte_carlo.progress_title",
                                            ) || "Monte Carlo en cours"
                                        }}
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <div class="text-xs font-semibold">
                                            {{ mcPercent }}%
                                        </div>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            class="h-6 w-6 p-0 hover:bg-secondary/50"
                                            @click="mcShowDetailedInfo = !mcShowDetailedInfo"
                                        >
                                            <Activity class="size-3" />
                                        </Button>
                                    </div>
                                </div>
                                <div
                                    class="mx-2 mb-2 h-2 bg-secondary/50 rounded-full overflow-hidden"
                                >
                                    <div
                                        class="h-full bg-trading-blue"
                                        :style="{
                                            width: mcPercent + '%',
                                        }"
                                    ></div>
                                </div>
                                <div
                                    class="px-2 pb-2 text-[11px] text-muted-foreground"
                                >
                                    {{ mcCurrent }}/{{ mcTotal }} runs ·
                                    {{ mcStatusLabel }}
                                    <span v-if="mcEtaSeconds != null">
                                        · ETA {{ formatEta(mcEtaSeconds) }}</span
                                    >
                                    <span v-if="mcSpeed && mcSpeed > 0">
                                        · {{ mcSpeed.toFixed(1) }} runs/s</span
                                    >
                                </div>
                                
                                <!-- Panneau d'informations détaillées -->
                                <div
                                    v-if="mcShowDetailedInfo"
                                    class="mx-2 mb-2 p-3 bg-secondary/20 rounded-md border border-secondary/30"
                                >
                                    <div class="text-xs font-medium text-foreground mb-2 flex items-center gap-1">
                                        <Zap class="size-3" />
                                        Diagnostic WebSocket
                                    </div>
                                    <div class="grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
                                        <div class="flex items-center gap-1">
                                            <Wifi class="size-2.5" />
                                            <span>Connexion:</span>
                                            <span class="font-mono">{{ mcConnectionDelay?.toFixed(2) || '--' }}s</span>
                                        </div>
                                        <div class="flex items-center gap-1">
                                            <Clock class="size-2.5" />
                                            <span>Traitement:</span>
                                            <span class="font-mono">{{ mcProcessingDelay?.toFixed(2) || '--' }}s</span>
                                        </div>
                                        <div class="flex items-center gap-1">
                                            <Activity class="size-2.5" />
                                            <span>Messages:</span>
                                            <span class="font-mono">{{ mcMessageCount }}</span>
                                        </div>
                                        <div class="flex items-center gap-1">
                                            <Clock class="size-2.5" />
                                            <span>Durée totale:</span>
                                            <span class="font-mono">{{ mcTotalDuration?.toFixed(1) || '--' }}s</span>
                                        </div>
                                    </div>
                                    <div class="mt-2 pt-2 border-t border-secondary/30">
                                        <div class="text-[10px] text-muted-foreground">
                                            <span class="font-medium">Job ID:</span>
                                            <span class="font-mono ml-1">{{ mcActiveJobId?.slice(-8) || '--' }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <template v-if="loading">
                            <div
                                class="h-[300px] sm:h-[400px] w-full relative overflow-hidden flex items-center justify-center"
                            >
                                <!-- Spinner moderne -->
                                <div class="flex flex-col items-center gap-3">
                                    <Spinner
                                        class="h-8 w-8 text-trading-blue"
                                    />
                                    <span
                                        class="text-sm text-muted-foreground"
                                        >{{ t("simulate.loading") }}</span
                                    >
                                </div>
                            </div>
                        </template>
                        <template v-else>
                            <!-- Monte Carlo Results with Equity Envelope -->
                            <div v-if="hasMonteCarloResults" class="space-y-4">
                                <EquityEnvelopeChart
                                    :equity-envelope="
                                        store.equityEnvelope || undefined
                                    "
                                    :active-range="activeRange"
                                />
                            </div>
                            <MultiLineChart
                                v-else-if="hasMultipleResults"
                                :results="store.results"
                                :aggregated-data="aggregatedData"
                                :active-range="activeRange"
                            />
                            <!-- Graphique simple pour un seul résultat -->
                            <BacktestChart v-else :series="chartSeries" />
                        </template>
                    </CardContent>
                </Card>

                <!-- KPI grid avec design premium - mobile responsive -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
                    <!-- Monte Carlo Metrics Display -->
                    <div v-if="hasMonteCarloResults" class="col-span-full mb-4">
                        <div class="text-center mb-4">
                            <h3 class="text-lg font-semibold text-foreground">
                                Distribution Statistics
                            </h3>
                            <p class="text-sm text-muted-foreground">
                                Showing median values with distribution ranges
                            </p>
                        </div>
                        <div
                            class="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4"
                        >
                            <DistributionMetricsCard
                                :label="t('simulate.metrics.pnl')"
                                :distribution="
                                    store.metricsDistribution?.pnl || null
                                "
                                percentage
                            />
                            <DistributionMetricsCard
                                :label="t('simulate.metrics.drawdown')"
                                :distribution="
                                    store.metricsDistribution?.drawdown || null
                                "
                                percentage
                            />
                            <DistributionMetricsCard
                                :label="t('simulate.metrics.sharpe')"
                                :distribution="
                                    store.metricsDistribution?.sharpe || null
                                "
                            />
                        </div>
                    </div>

                    <!-- Regular Metrics Display -->
                    <div
                        v-if="!hasMonteCarloResults"
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
                        v-if="!hasMonteCarloResults"
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
                        v-if="!hasMonteCarloResults"
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
    </BaseLayout>
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

/* Optimisation de la grille KPI sur très petits écrans */
@media (max-width: 480px) {
    .grid-cols-1 {
        gap: 0.75rem;
    }
}
</style>