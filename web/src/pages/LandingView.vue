<script setup lang="ts">
import { useRouter } from "@/router";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
} from "@/components/ui/card";
import { useI18n } from "vue-i18n";
import { LineChart, ShieldCheck, BarChart3 } from "lucide-vue-next";
import TopNav from "@/components/common/TopNav.vue";
import { ref, watch } from "vue";

const i18n = useI18n();

const { navigate } = useRouter();
const { t } = useI18n();
const localeRef = (i18n as unknown as { locale: { value: "en" | "fr" } })
    .locale;
const selectedLocale = ref<"en" | "fr">("en");
watch(selectedLocale, (val) => {
    if (localeRef) localeRef.value = val;
});
function go(path: string) {
    navigate(path);
}
</script>

<template>
    <main
        class="container mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-6 sm:space-y-10 animate-fade-in"
    >
        <TopNav />

        <section
            class="liquid-glass-hero relative overflow-hidden rounded-xl sm:rounded-2xl px-4 sm:px-8 py-8 sm:py-16 text-center"
        >
            <!-- Liquid Glass Background Layers -->
            <div class="liquid-glass-bg"></div>
            <div class="liquid-glass-overlay"></div>
            <div class="liquid-glass-reflection"></div>
            <div class="liquid-glass-shimmer"></div>

            <div class="relative z-10 animate-slide-up space-y-4 sm:space-y-6">
                <h1
                    class="text-2xl sm:text-4xl md:text-5xl font-bold tracking-tight gradient-text leading-tight px-2"
                >
                    {{ t("landing.title") }}
                </h1>
                <p
                    class="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed px-2"
                >
                    {{ t("landing.subtitle") }}
                </p>
                <div class="flex justify-center gap-4 pt-2 sm:pt-4">
                    <Button
                        size="lg"
                        @click="go('/simulate')"
                        class="gradient-primary text-white font-semibold px-6 sm:px-8 py-3 sm:py-4 rounded-xl shadow-medium hover-glow hover-scale transition-bounce text-sm sm:text-base"
                    >
                        <BarChart3 class="mr-2 h-4 w-4 sm:h-5 sm:w-5" />
                        {{ t("landing.cta.startBacktest") }}
                    </Button>
                </div>
            </div>
        </section>

        <section class="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-8">
            <Card
                class="group relative overflow-hidden border-0 shadow-soft hover-lift hover-glow transition-smooth animate-scale-in bg-gradient-to-br from-card via-card to-secondary/30"
            >
                <div
                    class="absolute inset-0 bg-gradient-to-br from-trading-blue/5 to-trading-purple/5 opacity-0 group-hover:opacity-100 transition-smooth"
                ></div>
                <CardHeader class="relative z-10 p-3 sm:p-5">
                    <div
                        class="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4"
                    >
                        <div
                            class="rounded-xl sm:rounded-2xl bg-trading-blue/10 p-3 sm:p-4 text-trading-blue group-hover:bg-trading-blue/20 transition-smooth shadow-soft"
                        >
                            <LineChart class="size-5 sm:size-6" />
                        </div>
                        <div class="flex-1">
                            <CardTitle
                                class="text-lg sm:text-xl font-semibold"
                                >{{
                                    t("landing.sections.simulation.title")
                                }}</CardTitle
                            >
                            <CardDescription
                                class="text-muted-foreground mt-1 text-sm"
                                >{{ t("landing.sections.simulation.description") }}</CardDescription
                            >
                        </div>
                    </div>
                </CardHeader>
                <CardContent class="relative z-10 p-3 sm:p-5 pt-0">
                    <p class="text-sm text-muted-foreground leading-relaxed">
                        {{ t("landing.sections.simulation.text") }}
                    </p>
                </CardContent>
            </Card>

            <Card
                class="group relative overflow-hidden border-0 shadow-soft hover-lift hover-glow transition-smooth animate-scale-in bg-gradient-to-br from-card via-card to-secondary/30"
                style="animation-delay: 0.1s"
            >
                <div
                    class="absolute inset-0 bg-gradient-to-br from-trading-green/5 to-trading-cyan/5 opacity-0 group-hover:opacity-100 transition-smooth"
                ></div>
                <CardHeader class="relative z-10 p-3 sm:p-5">
                    <div
                        class="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4"
                    >
                        <div
                            class="rounded-xl sm:rounded-2xl bg-trading-green/10 p-3 sm:p-4 text-trading-green group-hover:bg-trading-green/20 transition-smooth shadow-soft"
                        >
                            <ShieldCheck class="size-5 sm:size-6" />
                        </div>
                        <div class="flex-1">
                            <CardTitle
                                class="text-lg sm:text-xl font-semibold"
                                >{{
                                    t("landing.sections.auth.title")
                                }}</CardTitle
                            >
                            <CardDescription
                                class="text-muted-foreground mt-1 text-sm"
                                >{{ t("landing.sections.auth.description") }}</CardDescription
                            >
                        </div>
                    </div>
                </CardHeader>
                <CardContent class="relative z-10 p-3 sm:p-5 pt-0">
                    <p class="text-sm text-muted-foreground leading-relaxed">
                        {{ t("landing.sections.auth.text") }}
                    </p>
                </CardContent>
            </Card>

            <Card
                class="group relative overflow-hidden border-0 shadow-soft hover-lift hover-glow transition-smooth animate-scale-in bg-gradient-to-br from-card via-card to-secondary/30"
                style="animation-delay: 0.2s"
            >
                <div
                    class="absolute inset-0 bg-gradient-to-br from-trading-orange/5 to-trading-red/5 opacity-0 group-hover:opacity-100 transition-smooth"
                ></div>
                <CardHeader class="relative z-10 p-3 sm:p-5">
                    <div
                        class="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4"
                    >
                        <div
                            class="rounded-xl sm:rounded-2xl bg-trading-orange/10 p-3 sm:p-4 text-trading-orange group-hover:bg-trading-orange/20 transition-smooth shadow-soft"
                        >
                            <BarChart3 class="size-5 sm:size-6" />
                        </div>
                        <div class="flex-1">
                            <CardTitle
                                class="text-lg sm:text-xl font-semibold"
                                >{{
                                    t("landing.sections.visualization.title")
                                }}</CardTitle
                            >
                            <CardDescription
                                class="text-muted-foreground mt-1 text-sm"
                                >{{ t("landing.sections.visualization.description") }}</CardDescription
                            >
                        </div>
                    </div>
                </CardHeader>
                <CardContent class="relative z-10 p-3 sm:p-5 pt-0">
                    <p class="text-sm text-muted-foreground leading-relaxed">
                        {{ t("landing.sections.visualization.text") }}
                    </p>
                </CardContent>
            </Card>
        </section>
    </main>
</template>

<style scoped>
.hero-glow {
    position: relative;
}

.hero-glow::before {
    content: "";
    position: absolute;
    inset: -10px; /* Augmenté pour faire déborder le glow */
    border-radius: inherit;
    padding: 2px;
    background: linear-gradient(
        135deg,
        var(--trading-blue),
        var(--trading-purple),
        var(--trading-cyan),
        var(--trading-green)
    );
    mask:
        linear-gradient(#fff 0 0) content-box,
        linear-gradient(#fff 0 0);
    mask-composite: xor;
    -webkit-mask-composite: xor;
    opacity: 0.9; /* Opacité augmentée pour un glow plus intense */
    filter: blur(5px); /* Ajout d'un flou pour un effet plus diffus */
}

@keyframes particle-float {
    0%,
    100% {
        transform: translateY(0px) rotate(0deg);
        opacity: 0.7;
    }
    33% {
        transform: translateY(-15px) rotate(120deg);
        opacity: 1;
    }
    66% {
        transform: translateY(-8px) rotate(240deg);
        opacity: 0.8;
    }
}

@media (min-width: 640px) {
    @keyframes particle-float {
        0%,
        100% {
            transform: translateY(0px) rotate(0deg);
            opacity: 0.7;
        }
        33% {
            transform: translateY(-20px) rotate(120deg);
            opacity: 1;
        }
        66% {
            transform: translateY(-10px) rotate(240deg);
            opacity: 0.8;
        }
    }
}

.particle {
    animation: particle-float 8s ease-in-out infinite;
}

.card-shine {
    position: relative;
    overflow: hidden;
}

.card-shine::after {
    content: "";
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: linear-gradient(
        45deg,
        transparent,
        rgba(255, 255, 255, 0.1),
        transparent
    );
    transform: rotate(45deg) translate(-100%, -100%);
    transition: transform 0.6s ease;
}

.card-shine:hover::after {
    transform: rotate(45deg) translate(100%, 100%);
}

@keyframes gradient-shift {
    0%,
    100% {
        background-position: 0% 50%;
    }
    50% {
        background-position: 100% 50%;
    }
}

.gradient-text {
    background: linear-gradient(
        270deg,
        var(--primary),
        var(--trading-purple),
        var(--trading-cyan),
        var(--trading-blue),
        var(--primary)
    );
    background-size: 400% 400%;
    animation: gradient-shift 4s ease infinite;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}

.pulse-ring {
    position: relative;
}

.pulse-ring::before {
    content: "";
    position: absolute;
    inset: -4px;
    border-radius: inherit;
    background: var(--gradient-primary);
    opacity: 0;
    animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
    0% {
        transform: scale(1);
        opacity: 0.8;
    }
    100% {
        transform: scale(1.2);
        opacity: 0;
    }
}

/* Lumières SF latérales dans le hero - animation fluide */
.sf-light {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 160px;
    pointer-events: none;
    filter: blur(16px);
    opacity: 0;
    mix-blend-mode: screen;
    z-index: 1;
    will-change: opacity, transform;
    animation: sf-pulse 6s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@media (min-width: 640px) {
    .sf-light {
        width: 180px;
        filter: blur(18px);
    }
}

.sf-light-left {
    left: -20px;
    animation-delay: -0.8s;
    background: radial-gradient(
        closest-side,
        rgba(99, 102, 241, 0.45),
        /* indigo */ rgba(168, 85, 247, 0.25),
        /* purple */ transparent 65%
    );
    box-shadow:
        0 0 60px rgba(99, 102, 241, 0.35),
        0 0 100px rgba(168, 85, 247, 0.25);
}

@media (min-width: 640px) {
    .sf-light-left {
        left: -30px;
        background: radial-gradient(
            closest-side,
            rgba(99, 102, 241, 0.55),
            /* indigo */ rgba(168, 85, 247, 0.35),
            /* purple */ transparent 65%
        );
    }
}

.sf-light-right {
    right: -20px;
    animation-delay: 0.4s;
    background: radial-gradient(
        closest-side,
        rgba(6, 182, 212, 0.45),
        /* cyan */ rgba(34, 197, 94, 0.25),
        /* green */ transparent 65%
    );
    box-shadow:
        0 0 60px rgba(6, 182, 212, 0.35),
        0 0 100px rgba(34, 197, 94, 0.25);
}

@media (min-width: 640px) {
    .sf-light-right {
        right: -30px;
        background: radial-gradient(
            closest-side,
            rgba(6, 182, 212, 0.55),
            /* cyan */ rgba(34, 197, 94, 0.35),
            /* green */ transparent 65%
        );
    }
}

@keyframes sf-pulse {
    0% {
        opacity: 0;
        transform: translateY(2px) scale(0.98);
    }
    20% {
        opacity: 0.45;
        transform: translateY(0) scale(1);
    }
    50% {
        opacity: 0.85;
        transform: translateY(-6px) scale(1.02);
    }
    80% {
        opacity: 0.45;
        transform: translateY(0) scale(1);
    }
    100% {
        opacity: 0;
        transform: translateY(2px) scale(0.98);
    }
}

@media (min-width: 640px) {
    @keyframes sf-pulse {
        0% {
            opacity: 0;
            transform: translateY(2px) scale(0.98);
        }
        20% {
            opacity: 0.55;
            transform: translateY(0) scale(1);
        }
        50% {
            opacity: 0.95;
            transform: translateY(-8px) scale(1.03);
        }
        80% {
            opacity: 0.55;
            transform: translateY(0) scale(1);
        }
        100% {
            opacity: 0;
            transform: translateY(2px) scale(0.98);
        }
    }
}

.gradient-hero {
    position: relative;
    background:
        radial-gradient(
            120% 80% at 20% 20%,
            rgba(99, 102, 241, 0.08),
            transparent 60%
        ),
        radial-gradient(
            120% 80% at 80% 80%,
            rgba(34, 197, 94, 0.08),
            transparent 60%
        );
}

@media (hover: none) and (pointer: coarse) {
    .hover-lift:hover {
        transform: none;
    }

    .hover-lift:active {
        transform: translateY(2px);
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

    .animate-float {
        animation-duration: 12s;
    }

    .gradient-text {
        animation-duration: 6s;
    }
}

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

    .backdrop-blur-sm {
        backdrop-filter: blur(4px);
    }
}

/* Liquid Glass Effect - Apple-inspired */
.liquid-glass-hero {
    position: relative;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    background: rgba(255, 255, 255, 0.05);
    box-shadow:
        0 8px 32px rgba(0, 0, 0, 0.12),
        inset 0 1px 0 rgba(255, 255, 255, 0.2),
        inset 0 -1px 0 rgba(255, 255, 255, 0.1);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.liquid-glass-hero:hover {
    background: rgba(255, 255, 255, 0.08);
    box-shadow:
        0 12px 40px rgba(0, 0, 0, 0.15),
        inset 0 1px 0 rgba(255, 255, 255, 0.25),
        inset 0 -1px 0 rgba(255, 255, 255, 0.15);
    transform: translateY(-2px);
}

.liquid-glass-bg {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        135deg,
        rgba(99, 102, 241, 0.1) 0%,
        rgba(168, 85, 247, 0.08) 25%,
        rgba(6, 182, 212, 0.06) 50%,
        rgba(34, 197, 94, 0.08) 75%,
        rgba(99, 102, 241, 0.1) 100%
    );
    background-size: 400% 400%;
    animation: liquid-gradient 8s ease-in-out infinite;
    border-radius: inherit;
}

.liquid-glass-overlay {
    position: absolute;
    inset: 0;
    background: radial-gradient(
        circle at 30% 20%,
        rgba(255, 255, 255, 0.15) 0%,
        rgba(255, 255, 255, 0.05) 40%,
        transparent 70%
    );
    border-radius: inherit;
    opacity: 0.8;
}

.liquid-glass-reflection {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 50%;
    background: linear-gradient(
        180deg,
        rgba(255, 255, 255, 0.12) 0%,
        rgba(255, 255, 255, 0.06) 50%,
        transparent 100%
    );
    border-radius: inherit;
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
}

.liquid-glass-shimmer {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        45deg,
        transparent 30%,
        rgba(255, 255, 255, 0.1) 50%,
        transparent 70%
    );
    background-size: 200% 200%;
    animation: shimmer 3s ease-in-out infinite;
    border-radius: inherit;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.liquid-glass-hero:hover .liquid-glass-shimmer {
    opacity: 1;
}

@keyframes liquid-gradient {
    0%,
    100% {
        background-position: 0% 50%;
    }
    50% {
        background-position: 100% 50%;
    }
}

@keyframes shimmer {
    0% {
        background-position: -200% -200%;
    }
    100% {
        background-position: 200% 200%;
    }
}

/* Dark mode adjustments */
@media (prefers-color-scheme: dark) {
    .liquid-glass-hero {
        background: rgba(0, 0, 0, 0.3);
        border-color: rgba(255, 255, 255, 0.15);
        box-shadow:
            0 8px 32px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.15),
            inset 0 -1px 0 rgba(255, 255, 255, 0.08);
    }

    .liquid-glass-hero:hover {
        background: rgba(0, 0, 0, 0.4);
        box-shadow:
            0 12px 40px rgba(0, 0, 0, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.2),
            inset 0 -1px 0 rgba(255, 255, 255, 0.1);
    }

    .liquid-glass-overlay {
        background: radial-gradient(
            circle at 30% 20%,
            rgba(255, 255, 255, 0.08) 0%,
            rgba(255, 255, 255, 0.03) 40%,
            transparent 70%
        );
    }

    .liquid-glass-reflection {
        background: linear-gradient(
            180deg,
            rgba(255, 255, 255, 0.08) 0%,
            rgba(255, 255, 255, 0.04) 50%,
            transparent 100%
        );
    }
}
</style>
