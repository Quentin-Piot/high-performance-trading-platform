<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { TrendingUp, BarChart3, Zap, Shield } from "lucide-vue-next";
import { useRouter } from "@/router";
import BaseLayout from "@/components/layouts/BaseLayout.vue";
import {
    Dialog,
    DialogTrigger,
    DialogScrollContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from "@/components/ui/dialog";
const { t } = useI18n();
const { navigate } = useRouter();
function goToSimulate() {
    navigate("/simulate");
}
</script>
<template>
    <div
        class="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900"
    >
        <BaseLayout main-class="flex-1 flex flex-col" container-class="">
            <section
                class="flex-1 flex items-center justify-center relative overflow-hidden pt-8 md:pt-12"
            >
                <div
                    class="liquid-glass-hero rounded-3xl p-12 md:p-16 lg:p-20 relative z-10"
                >
                    <div class="liquid-glass-bg"></div>
                    <div class="liquid-glass-overlay"></div>
                    <div class="liquid-glass-reflection"></div>
                    <div class="liquid-glass-shimmer"></div>
                    <div class="liquid-glass-noise"></div>
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
                                class="px-8 py-4 text-lg font-semibold bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white border-0 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
                                @click="goToSimulate"
                            >
                                <TrendingUp class="mr-2 h-5 w-5" />
                                {{ t("landing.cta.startBacktest") }}
                            </Button>
                        </div>
                    </div>
                </div>
            </section>
            <section class="py-16 px-4 sm:px-6 lg:px-8">
                <div class="max-w-7xl mx-auto">
                    <div class="text-center mb-12">
                        <h2
                            class="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-4"
                        >
                            {{ t("landing.project.title") }}
                        </h2>
                        <p
                            class="text-lg text-gray-600 dark:text-gray-300 max-w-3xl mx-auto"
                        >
                            {{ t("landing.project.description") }}
                        </p>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
                        <Dialog>
                            <DialogTrigger as-child>
                                <Card
                                    class="group hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border-0 shadow-lg cursor-pointer"
                                >
                                    <CardHeader class="text-center pb-4">
                                        <div
                                            class="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-green-400 to-blue-500 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300"
                                        >
                                            <Zap class="h-8 w-8 text-white" />
                                        </div>
                                        <CardTitle
                                            class="text-xl font-bold text-gray-900 dark:text-white"
                                        >
                                            {{
                                                t(
                                                    "landing.project.frontend.title",
                                                )
                                            }}
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <CardDescription
                                            class="text-gray-600 dark:text-gray-300 text-center"
                                        >
                                            {{
                                                t(
                                                    "landing.project.frontend.description",
                                                )
                                            }}
                                            <span
                                                class="block mt-2 text-sm font-semibold text-blue-600 dark:text-blue-400"
                                            >
                                                {{
                                                    t(
                                                        "landing.project.frontend.click_to_architecture",
                                                    )
                                                }}
                                            </span>
                                        </CardDescription>
                                    </CardContent>
                                </Card>
                            </DialogTrigger>
                            <DialogScrollContent class="sm:max-w-[600px]">
                                <DialogHeader>
                                    <DialogTitle
                                        class="text-blue-600 dark:text-blue-400"
                                    >
                                        {{
                                            t(
                                                "landing.architecture.frontend.title",
                                            )
                                        }}
                                    </DialogTitle>
                                    <DialogDescription>
                                        {{
                                            t(
                                                "landing.architecture.frontend.description",
                                            )
                                        }}
                                    </DialogDescription>
                                </DialogHeader>
                                <div class="py-4 space-y-4">
                                    <!-- Stack Applicative -->
                                    <div class="mt-6">
                                        <h4
                                            class="text-lg font-bold mb-3 flex items-center text-blue-600 dark:text-blue-400"
                                        >
                                            <Zap
                                                class="h-5 w-5 mr-2 text-blue-500"
                                            />
                                            {{
                                                t(
                                                    "landing.architecture.sections.stack.title",
                                                )
                                            }}
                                        </h4>
                                        <ul
                                            class="list-disc pl-6 space-y-2 text-gray-700 dark:text-gray-300"
                                        >
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.stack.points.0",
                                                    )
                                                }}
                                            </li>
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.stack.points.1",
                                                    )
                                                }}
                                            </li>
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.stack.points.2",
                                                    )
                                                }}
                                            </li>
                                        </ul>
                                    </div>
                                    <!-- Expérience Utilisateur -->
                                    <div class="mt-6">
                                        <h4
                                            class="text-lg font-bold mb-3 flex items-center text-blue-600 dark:text-blue-400"
                                        >
                                            <TrendingUp
                                                class="h-5 w-5 mr-2 text-blue-500"
                                            />
                                            Expérience Utilisateur
                                        </h4>
                                        <ul
                                            class="list-disc pl-6 space-y-2 text-gray-700 dark:text-gray-300"
                                        >
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.frontend.experience",
                                                    )
                                                }}
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </DialogScrollContent>
                        </Dialog>
                        <Dialog>
                            <DialogTrigger as-child>
                                <Card
                                    class="group hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border-0 shadow-lg cursor-pointer"
                                >
                                    <CardHeader class="text-center pb-4">
                                        <div
                                            class="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-purple-400 to-pink-500 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300"
                                        >
                                            <BarChart3
                                                class="h-8 w-8 text-white"
                                            />
                                        </div>
                                        <CardTitle
                                            class="text-xl font-bold text-gray-900 dark:text-white"
                                        >
                                            {{
                                                t(
                                                    "landing.project.backend.title",
                                                )
                                            }}
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <CardDescription
                                            class="text-gray-600 dark:text-gray-300 text-center"
                                        >
                                            {{
                                                t(
                                                    "landing.project.backend.description",
                                                )
                                            }}
                                            <span
                                                class="block mt-2 text-sm font-semibold text-purple-600 dark:text-purple-400"
                                            >
                                                {{
                                                    t(
                                                        "landing.project.backend.click_to_system_design",
                                                    )
                                                }}
                                            </span>
                                        </CardDescription>
                                    </CardContent>
                                </Card>
                            </DialogTrigger>
                            <DialogScrollContent class="sm:max-w-[600px]">
                                <DialogHeader>
                                    <DialogTitle
                                        class="text-blue-600 dark:text-blue-400"
                                    >
                                        {{
                                            t(
                                                "landing.architecture.backend.title",
                                            )
                                        }}
                                    </DialogTitle>
                                    <DialogDescription>
                                        {{
                                            t(
                                                "landing.architecture.backend.description",
                                            )
                                        }}
                                    </DialogDescription>
                                </DialogHeader>
                                <div class="py-4 space-y-4">
                                    <!-- Base de Données & Caching -->
                                    <div class="mt-6">
                                        <h4
                                            class="text-lg font-bold mb-3 flex items-center text-blue-600 dark:text-blue-400"
                                        >
                                            <BarChart3
                                                class="h-5 w-5 mr-2 text-blue-500"
                                            />
                                            {{
                                                t(
                                                    "landing.architecture.sections.data_cache.title",
                                                )
                                            }}
                                        </h4>
                                        <ul
                                            class="list-disc pl-6 space-y-2 text-gray-700 dark:text-gray-300"
                                        >
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.data_cache.points.0",
                                                    )
                                                }}
                                            </li>
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.data_cache.points.1",
                                                    )
                                                }}
                                            </li>
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.data_cache.points.2",
                                                    )
                                                }}
                                            </li>
                                        </ul>
                                    </div>
                                    <!-- Alignement Rôle Architecte/Lead -->
                                    <div class="mt-6">
                                        <h4
                                            class="text-lg font-bold mb-3 flex items-center text-blue-600 dark:text-blue-400"
                                        >
                                            <TrendingUp
                                                class="h-5 w-5 mr-2 text-blue-500"
                                            />
                                            {{
                                                t(
                                                    "landing.architecture.sections.alignment.title",
                                                )
                                            }}
                                        </h4>
                                        <ul
                                            class="list-disc pl-6 space-y-2 text-gray-700 dark:text-gray-300"
                                        >
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.alignment.points.0",
                                                    )
                                                }}
                                            </li>
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.alignment.points.1",
                                                    )
                                                }}
                                            </li>
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.alignment.points.2",
                                                    )
                                                }}
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </DialogScrollContent>
                        </Dialog>
                        <Dialog>
                            <DialogTrigger as-child>
                                <Card
                                    class="group hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border-0 shadow-lg cursor-pointer"
                                >
                                    <CardHeader class="text-center pb-4">
                                        <div
                                            class="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-orange-400 to-red-500 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300"
                                        >
                                            <Shield
                                                class="h-8 w-8 text-white"
                                            />
                                        </div>
                                        <CardTitle
                                            class="text-xl font-bold text-gray-900 dark:text-white"
                                        >
                                            {{
                                                t(
                                                    "landing.project.infrastructure.title",
                                                )
                                            }}
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <CardDescription
                                            class="text-gray-600 dark:text-gray-300 text-center"
                                        >
                                            {{
                                                t(
                                                    "landing.project.infrastructure.description",
                                                )
                                            }}
                                            <span
                                                class="block mt-2 text-sm font-semibold text-red-600 dark:text-red-400"
                                            >
                                                {{
                                                    t(
                                                        "landing.project.infrastructure.click_to_iac_cloud",
                                                    )
                                                }}
                                            </span>
                                        </CardDescription>
                                    </CardContent>
                                </Card>
                            </DialogTrigger>
                            <DialogScrollContent class="sm:max-w-[600px]">
                                <DialogHeader>
                                    <DialogTitle
                                        class="text-blue-600 dark:text-blue-400"
                                    >
                                        {{
                                            t(
                                                "landing.architecture.infra_dialog.title",
                                            )
                                        }}
                                    </DialogTitle>
                                    <DialogDescription>
                                        {{
                                            t(
                                                "landing.architecture.infra_dialog.description",
                                            )
                                        }}
                                    </DialogDescription>
                                </DialogHeader>
                                <div class="py-4 space-y-4">
                                    <!-- Infrastructure & Déploiement -->
                                    <div class="mt-6">
                                        <h4
                                            class="text-lg font-bold mb-3 flex items-center text-blue-600 dark:text-blue-400"
                                        >
                                            <Shield
                                                class="h-5 w-5 mr-2 text-blue-500"
                                            />
                                            {{
                                                t(
                                                    "landing.architecture.sections.infra.title",
                                                )
                                            }}
                                        </h4>
                                        <ul
                                            class="list-disc pl-6 space-y-2 text-gray-700 dark:text-gray-300"
                                        >
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.infra.points.0",
                                                    )
                                                }}
                                            </li>
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.infra.points.1",
                                                    )
                                                }}
                                            </li>
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.infra.points.2",
                                                    )
                                                }}
                                            </li>
                                            <li>
                                                {{
                                                    t(
                                                        "landing.architecture.sections.infra.points.3",
                                                    )
                                                }}
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </DialogScrollContent>
                        </Dialog>
                    </div>
                </div>
            </section>
        </BaseLayout>
        <footer class="relative mt-4 sm:mt-6">
            <div class="liquid-glass-hero">
                <div class="liquid-glass-bg"></div>
                <div class="liquid-glass-overlay"></div>
                <div class="liquid-glass-reflection"></div>
                <div class="liquid-glass-shimmer"></div>
                <div class="liquid-glass-noise"></div>
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
.liquid-glass-hero {
    position: relative;
    background: rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(24px) saturate(1.15);
    -webkit-backdrop-filter: blur(24px) saturate(1.15);
    border: 1px solid rgba(255, 255, 255, 0.18);
    box-shadow:
        0 12px 40px rgba(0, 0, 0, 0.18),
        inset 0 1px 0 rgba(255, 255, 255, 0.18),
        inset 0 -1px 0 rgba(255, 255, 255, 0.12);
    transition: none;
    overflow: hidden;
}
.liquid-glass-hero::before {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 600%; 
    height: 600%; 
    background: radial-gradient(
        circle closest-corner at 50% 50%,
        rgba(255, 255, 255, 0.1) 0%,
        rgba(255, 255, 255, 0.05) 5%,
         transparent 15%
    );
    transform: translate(-50%, -50%) scale(0);
    border-radius: 50%;
    transition:
        transform 1s cubic-bezier(0.25, 0.46, 0.45, 0.94),
        opacity 0.8s ease;
    opacity: 0;
    pointer-events: none;
    z-index: 1;
}
.liquid-glass-hero:hover::before {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1); 
}
.liquid-glass-bg {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        135deg,
        rgba(22, 28, 43, 0.88) 0%,
        rgba(28, 22, 46, 0.88) 55%,
        rgba(35, 24, 58, 0.88) 100%
    );
    background-size: 180% 180%;
    border-radius: inherit;
}
.liquid-glass-overlay {
    position: absolute;
    inset: 0;
    background: radial-gradient(
        circle at 30% 20%,
        rgba(255, 255, 255, 0.24) 0%,
        rgba(255, 255, 255, 0.1) 40%,
        transparent 70%
    );
    border-radius: inherit;
    opacity: 0.95;
}
.liquid-glass-reflection {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 42%;
    background: linear-gradient(
        180deg,
        rgba(255, 255, 255, 0.18) 0%,
        rgba(255, 255, 255, 0.08) 45%,
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
        90deg,
        transparent 30%,
        rgba(255, 255, 255, 0.12) 50%,
        transparent 70%
    );
    background-size: 300% 100%;
    border-radius: inherit;
    opacity: 0;
    transition: none;
}
.liquid-glass-noise {
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: radial-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px);
    background-size: 4px 4px;
    mix-blend-mode: overlay;
    opacity: 0.15;
    pointer-events: none;
}
.gradient-text {
    background:
        radial-gradient(
            50% 140% at -20% 50%,
            rgba(255, 255, 255, 0.42),
            transparent 64%
        ),
        linear-gradient(
            90deg,
            rgba(238, 242, 255, 0.98) 0%,
            rgba(245, 243, 255, 0.98) 50%,
            rgba(240, 245, 255, 0.98) 100%
        ),
        linear-gradient(
            180deg,
            rgba(255, 255, 255, 0.96) 0%,
            rgba(255, 255, 255, 0.86) 48%,
            rgba(255, 255, 255, 0.78) 100%
        );
    background-size: 100% 100%;
    background-position: 0% 0%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow:
        0 1px 2px rgba(0, 0, 0, 0.1),
        0 8px 22px rgba(0, 0, 0, 0.2),
        0 -1px 8px rgba(255, 255, 255, 0.2);
}
.hero-title {
    text-shadow:
        0 1px 2px rgba(0, 0, 0, 0.06),
        0 4px 12px rgba(0, 0, 0, 0.1);
    opacity: 0.96;
    filter: blur(0.15px);
}
.hero-description {
    color: rgba(255, 255, 255, 0.88);
    opacity: 0.95;
    filter: blur(0.2px);
}
@media (prefers-color-scheme: dark) {
    .liquid-glass-hero {
        background: rgba(0, 0, 0, 0.28);
        border-color: rgba(255, 255, 255, 0.14);
        box-shadow:
            0 10px 40px rgba(0, 0, 0, 0.35),
            inset 0 1px 0 rgba(255, 255, 255, 0.14),
            inset 0 -1px 0 rgba(255, 255, 255, 0.08);
    }
    .liquid-glass-hero::before {
        background: radial-gradient(
            circle closest-corner at 50% 50%,
            rgba(255, 255, 255, 0.08) 0%,
            rgba(255, 255, 255, 0.04) 5%,
            transparent 15%
        );
    }
    .liquid-glass-overlay {
        background: radial-gradient(
            circle at 30% 20%,
            rgba(255, 255, 255, 0.1) 0%,
            rgba(255, 255, 255, 0.04) 40%,
            transparent 70%
        );
    }
    .liquid-glass-reflection {
        background: linear-gradient(
            180deg,
            rgba(255, 255, 255, 0.08) 0%,
            rgba(255, 255, 255, 0.04) 45%,
            transparent 100%
        );
    }
    .gradient-text {
        text-shadow:
            0 1px 2px rgba(0, 0, 0, 0.12),
            0 8px 20px rgba(255, 255, 255, 0.18);
    }
    .hero-description {
        color: rgba(255, 255, 255, 0.92);
    }
}
</style>