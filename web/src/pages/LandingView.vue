<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { Button } from "@/components/ui/button";
import { TrendingUp, BarChart3, Zap, Shield } from "lucide-vue-next";
import { useRouter } from "@/router";
import BaseLayout from "@/components/layouts/BaseLayout.vue";
import ArchitectureDialog from "@/components/landing/ArchitectureDialog.vue";
const { t } = useI18n();
const { navigate } = useRouter();
function goToSimulate() {
    navigate("/simulate");
}
const architectureCards = [
    {
        id: "frontend",
        icon: Zap,
        gradient: "from-green-400 to-emerald-600",
        glowColor: "rgba(16, 185, 129, 0.6)",
        sections: [
            {
                icon: Zap,
                titleKey: "landing.architecture.sections.stack.title",
                points: [
                    "landing.architecture.sections.stack.points.0",
                    "landing.architecture.sections.stack.points.1",
                    "landing.architecture.sections.stack.points.2",
                ],
            },
            {
                icon: TrendingUp,
                title: "Expérience Utilisateur",
                points: ["landing.architecture.frontend.experience"],
            },
        ],
    },
    {
        id: "backend",
        icon: BarChart3,
        gradient: "from-purple-400 to-purple-600",
        glowColor: "rgba(168, 85, 247, 0.6)",
        sections: [
            {
                icon: BarChart3,
                titleKey: "landing.architecture.sections.data_cache.title",
                points: [
                    "landing.architecture.sections.data_cache.points.0",
                    "landing.architecture.sections.data_cache.points.1",
                    "landing.architecture.sections.data_cache.points.2",
                ],
            },
            {
                icon: TrendingUp,
                titleKey: "landing.architecture.sections.alignment.title",
                points: [
                    "landing.architecture.sections.alignment.points.0",
                    "landing.architecture.sections.alignment.points.1",
                    "landing.architecture.sections.alignment.points.2",
                ],
            },
        ],
    },
    {
        id: "infrastructure",
        icon: Shield,
        gradient: "from-orange-400 to-red-600",
        glowColor: "rgba(249, 115, 22, 0.6)",
        sections: [
            {
                icon: Shield,
                titleKey: "landing.architecture.sections.infra.title",
                points: [
                    "landing.architecture.sections.infra.points.0",
                    "landing.architecture.sections.infra.points.1",
                    "landing.architecture.sections.infra.points.2",
                    "landing.architecture.sections.infra.points.3",
                    "landing.architecture.sections.infra.points.4",
                    "landing.architecture.sections.infra.points.5",
                    "landing.architecture.sections.infra.points.6",
                    "landing.architecture.sections.infra.points.7",
                ],
            },
        ],
    },
];
</script>
<template>
    <div
        class="min-h-screen flex flex-col bg-background"
    >
        <BaseLayout main-class="flex-1 flex flex-col" container-class="">
            <section
                class="flex-1 flex items-center justify-center relative overflow-hidden pt-8 md:pt-12"
            >
                <div
                    class="hero-container rounded-3xl p-12 md:p-16 lg:p-20 relative z-10"
                >
                    <div class="hero-bg"></div>
                    <div class="hero-glow"></div>
                    <div class="relative z-20 text-center space-y-8">
                        <div class="space-y-6">
                            <h1
                                class="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold tracking-tight gradient-text hero-title"
                            >
                                {{ t("landing.title") }}
                            </h1>
                            <p
                                class="text-lg sm:text-xl lg:text-2xl hero-description max-w-3xl mx-auto leading-relaxed"
                            >
                                {{ t("landing.subtitle") }}
                            </p>
                        </div>
                        <div
                            class="flex flex-col sm:flex-row gap-4 justify-center pt-4"
                        >
                            <Button
                                size="lg"
                                class="px-8 py-4 text-lg font-semibold bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white border-0 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
                                @click="goToSimulate"
                            >
                                <TrendingUp class="mr-2 h-5 w-5" />
                                {{ t("landing.cta.startBacktest") }}
                            </Button>
                        </div>
                    </div>
                </div>
            </section>
            <section class="py-20 px-4 sm:px-6 lg:px-8">
                <div class="max-w-7xl mx-auto">
                    <div class="text-center mb-16">
                        <h2
                            class="text-4xl sm:text-5xl font-bold bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-transparent mb-6"
                        >
                            {{ t("landing.project.title") }}
                        </h2>
                        <p
                            class="text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed"
                        >
                            {{ t("landing.project.description") }}
                        </p>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
                        <ArchitectureDialog
                            v-for="card in architectureCards"
                            :key="card.id"
                            :card-id="card.id"
                            :icon="card.icon"
                            :gradient="card.gradient"
                            :glow-color="card.glowColor"
                            :sections="card.sections"
                        />
                    </div>
                </div>
            </section>
        </BaseLayout>
        <footer class="relative mt-4 sm:mt-6">
            <div class="footer-container">
                <div class="footer-bg"></div>
                <div
                    class="relative z-10 max-w-7xl mx-auto flex items-center justify-between py-3 px-4 sm:py-4 sm:px-6"
                >
                    <div class="text-xs sm:text-sm text-white/80">
                        <span class="text-white/90 font-semibold"
                            >Quentin Piot</span
                        >
                    </div>
                    <div class="text-xs text-white/60 font-semibold">
                        © 2025 HPTP
                    </div>
                </div>
            </div>
        </footer>
    </div>
</template>
<style scoped>

.hero-container {
    position: relative;
    border: 1px solid rgba(96, 165, 250, 0.15);
    overflow: hidden;
    transition: border-color 0.3s ease;
}

.hero-container:hover {
    border-color: rgba(96, 165, 250, 0.25);
}

.hero-bg {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        135deg,
        rgba(26, 29, 40, 0.98) 0%,
        rgba(30, 34, 48, 0.98) 100%
    );
    border-radius: inherit;
}

.hero-glow {
    position: absolute;
    inset: -1px;
    background: linear-gradient(
        135deg,
        rgba(96, 165, 250, 0.1) 0%,
        transparent 40%,
        rgba(147, 51, 234, 0.1) 100%
    );
    border-radius: inherit;
    opacity: 0.6;
    pointer-events: none;
}


.footer-container {
    position: relative;
    border-top: 1px solid rgba(96, 165, 250, 0.1);
    overflow: hidden;
}

.footer-bg {
    position: absolute;
    inset: 0;
    background: rgba(26, 29, 40, 0.95);
}


.gradient-text {
    background: linear-gradient(
        135deg,
        rgba(255, 255, 255, 0.95) 0%,
        rgba(147, 197, 253, 0.9) 50%,
        rgba(255, 255, 255, 0.95) 100%
    );
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-title {
    letter-spacing: -0.02em;
}

.hero-description {
    color: rgba(255, 255, 255, 0.85);
}
</style>
