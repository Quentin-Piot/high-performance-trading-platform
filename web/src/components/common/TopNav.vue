<script setup lang="ts">
import { useRouter } from "@/router";
import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectGroup,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { useI18n } from "vue-i18n";
import { ref, watch } from "vue";
import {
    Home,
    BarChart3,
    LogIn,
    UserPlus,
    Globe,
    Menu,
    X,
} from "lucide-vue-next";

const { navigate } = useRouter();
const { t } = useI18n();
const i18n = useI18n();
const localeRef = (i18n as unknown as { locale: { value: "en" | "fr" } })
    .locale;
const selectedLocale = ref<"en" | "fr">(localeRef?.value ?? "en");
const mobileMenuOpen = ref(false);

watch(selectedLocale, (val) => {
    if (localeRef) localeRef.value = val;
});

function go(path: string) {
    navigate(path);
    mobileMenuOpen.value = false;
}

function goHome() {
    navigate("/");
    mobileMenuOpen.value = false;
}

function toggleMobileMenu() {
    mobileMenuOpen.value = !mobileMenuOpen.value;
}
</script>

<template>
    <nav class="relative">
        <!-- Liquid glass hero background - same as LandingView -->
        <div class="liquid-glass-hero">
            <div class="liquid-glass-bg"></div>
            <div class="liquid-glass-overlay"></div>
            <div class="liquid-glass-reflection"></div>
            <div class="liquid-glass-shimmer"></div>
            <div class="liquid-glass-noise"></div>
        </div>

        <!-- Navigation content -->
        <div
            class="relative flex items-center justify-between py-3 px-4 sm:py-4 sm:px-6 z-10"
        >
            <!-- Logo section avec effet hover - responsive -->
            <div
                class="flex items-end gap-2 sm:gap-3 cursor-pointer group transition-all duration-300 hover-scale"
                @click="goHome"
            >
                <div class="relative">
                    <!-- Logo avec gradient - même style que le hero title -->
                    <div
                        class="text-2xl sm:text-3xl font-bold gradient-text group-hover:scale-105 transition-all duration-500"
                    >
                        HPTP
                    </div>
                    <!-- Effet de brillance -->
                    <div
                        class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 -skew-x-12"
                    ></div>
                </div>
                <div class="hidden sm:flex flex-col">
                    <span
                        class="text-sm font-medium text-white/90 group-hover:text-trading-blue transition-colors"
                    >
                        {{ t("nav.title") }}
                    </span>
                    <span
                        class="text-xs text-white/70 group-hover:text-white/80 transition-colors"
                    >
                        {{ t("nav.subtitle") }}
                    </span>
                </div>
            </div>

            <!-- Desktop Navigation -->
            <div class="hidden lg:flex items-center gap-2">
                <!-- Home button -->
                <Button
                    variant="ghost"
                    size="sm"
                    class="h-9 px-4 text-white/90 hover:bg-trading-blue/20 hover:text-trading-blue transition-all duration-300 hover-scale group"
                    @click="go('/')"
                >
                    <Home
                        class="size-4 mr-2 group-hover:rotate-12 transition-transform duration-300"
                    />
                    {{ t("nav.home") }}
                </Button>

                <!-- Simulation button -->
                <Button
                    variant="ghost"
                    size="sm"
                    class="h-9 px-4 text-white/90 hover:bg-trading-purple/20 hover:text-trading-purple transition-all duration-300 hover-scale group"
                    @click="go('/simulate')"
                >
                    <BarChart3
                        class="size-4 mr-2 group-hover:scale-110 transition-transform duration-300"
                    />
                    {{ t("nav.simulate") }}
                </Button>

                <!-- Divider -->
                <div class="w-px h-6 bg-white/20 mx-2"></div>

                <!-- Language selector -->
                <div class="relative ml-2">
                    <Select v-model="selectedLocale">
                        <SelectTrigger
                            size="sm"
                            class="h-9 md:w-36 w-20 border-white/20 text-white/90 hover:border-trading-cyan hover:bg-trading-cyan/20 transition-all duration-300 hover-scale group justify-start"
                        >
                            <Globe
                                class="size-4 mr-2 text-trading-cyan group-hover:rotate-180 transition-transform duration-500"
                            />
                            <SelectValue
                                :placeholder="
                                    selectedLocale === 'fr'
                                        ? 'Français'
                                        : 'English'
                                "
                            />
                        </SelectTrigger>
                        <SelectContent
                            class="border-white/10 bg-card/95 backdrop-blur-sm w-36"
                        >
                            <SelectGroup>
                                <SelectItem
                                    value="en"
                                    class="hover:bg-trading-blue/10 hover:text-trading-blue transition-colors cursor-pointer"
                                >
                                    English
                                </SelectItem>
                                <SelectItem
                                    value="fr"
                                    class="hover:bg-trading-purple/10 hover:text-trading-purple transition-colors cursor-pointer"
                                >
                                    Français
                                </SelectItem>
                            </SelectGroup>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <!-- Mobile/Tablet Navigation -->
            <div class="flex lg:hidden items-center gap-2">
                <!-- Language selector compact pour mobile -->
                <div class="relative">
                    <Select v-model="selectedLocale">
                        <SelectTrigger
                            size="sm"
                            class="h-9 w-24 border-white/20 text-white/90 hover:border-trading-cyan hover:bg-trading-cyan/20 transition-all duration-300 hover-scale group justify-center"
                        >
                            <Globe
                                class="size-4 mr-1 text-trading-cyan group-hover:rotate-180 transition-transform duration-500"
                            />
                            <span class="text-xs font-medium">
                                {{ selectedLocale === "fr" ? "FR" : "EN" }}
                            </span>
                        </SelectTrigger>
                        <SelectContent
                            class="border-white/10 bg-card/95 backdrop-blur-sm w-32"
                        >
                            <SelectGroup>
                                <SelectItem
                                    value="en"
                                    class="hover:bg-trading-blue/10 hover:text-trading-blue transition-colors cursor-pointer"
                                >
                                    English
                                </SelectItem>
                                <SelectItem
                                    value="fr"
                                    class="hover:bg-trading-purple/10 hover:text-trading-purple transition-colors cursor-pointer"
                                >
                                    Français
                                </SelectItem>
                            </SelectGroup>
                        </SelectContent>
                    </Select>
                </div>

                <!-- Menu hamburger -->
                <Button
                    variant="ghost"
                    size="sm"
                    class="h-9 w-9 p-0 text-white/90 hover:bg-trading-blue/20 hover:text-trading-blue transition-all duration-300 hover-scale"
                    @click="toggleMobileMenu"
                >
                    <Menu v-if="!mobileMenuOpen" class="size-5" />
                    <X v-else class="size-5" />
                </Button>
            </div>
        </div>

        <!-- Menu mobile overlay -->
        <div
            v-if="mobileMenuOpen"
            class="lg:hidden absolute top-full left-0 right-0 mt-2 z-50 animate-slide-down"
        >
            <div
                class="bg-card/95 backdrop-blur-sm border border-white/10 rounded-2xl shadow-strong p-4 space-y-3"
            >
                <!-- Navigation mobile -->
                <div class="space-y-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        class="w-full justify-start h-10 px-4 hover:bg-trading-blue/10 hover:text-trading-blue transition-all duration-300 group"
                        @click="go('/')"
                    >
                        <Home
                            class="size-4 mr-3 group-hover:rotate-12 transition-transform duration-300"
                        />
                        {{ t("nav.home") }}
                    </Button>

                    <Button
                        variant="ghost"
                        size="sm"
                        class="w-full justify-start h-10 px-4 hover:bg-trading-purple/10 hover:text-trading-purple transition-all duration-300 group"
                        @click="go('/simulate')"
                    >
                        <BarChart3
                            class="size-4 mr-3 group-hover:scale-110 transition-transform duration-300"
                        />
                        {{ t("nav.simulate") }}
                    </Button>
                </div>

                <!-- Divider -->
                <div class="h-px bg-border/50 my-3"></div>

                <!-- Auth buttons mobile -->
                <div class="space-y-2">
                    <Button
                        variant="outline"
                        size="sm"
                        class="w-full justify-start h-10 px-4 border-trading-blue/20 hover:border-trading-blue hover:bg-trading-blue/5 hover:text-trading-blue transition-all duration-300 group"
                        @click="go('/login')"
                    >
                        <LogIn
                            class="size-4 mr-3 group-hover:-rotate-12 transition-transform duration-300"
                        />
                        {{ t("nav.login") }}
                    </Button>

                    <Button
                        size="sm"
                        class="w-full justify-start h-10 px-4 bg-trading-blue text-white rounded-lg border border-trading-blue hover:bg-trading-blue/80 hover:border-trading-blue/80 transition-all duration-300 group"
                        @click="go('/register')"
                    >
                        <UserPlus
                            class="size-4 mr-3 group-hover:scale-110 transition-transform duration-300"
                        />
                        {{ t("nav.register") }}
                    </Button>
                </div>
            </div>
        </div>
    </nav>
</template>

<style scoped>
/* Liquid glass hero styling - same as LandingView */
.liquid-glass-hero {
    position: absolute;
    inset: 0;
    background: rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(24px) saturate(1.15);
    -webkit-backdrop-filter: blur(24px) saturate(1.15);
    border: 1px solid rgba(255, 255, 255, 0.18);
    box-shadow:
        0 12px 40px rgba(0, 0, 0, 0.18),
        inset 0 1px 0 rgba(255, 255, 255, 0.18),
        inset 0 -1px 0 rgba(255, 255, 255, 0.12);
    border-radius: 1rem;
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

/* Gradient text styling - same as hero title */
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

/* Enhanced hover effects */
.hover-scale:hover {
    transform: scale(1.02);
}

/* Gradient text animation */
@keyframes gradient-shift {
    0%,
    100% {
        background-position: 0% 50%;
    }
    50% {
        background-position: 100% 50%;
    }
}

.group:hover .bg-gradient-to-r {
    background-size: 200% 200%;
    animation: gradient-shift 2s ease infinite;
}

/* Animation pour le menu mobile */
@keyframes slide-down {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-slide-down {
    animation: slide-down 0.2s ease-out;
}

/* Dark mode adjustments */
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
}

/* Optimisations tactiles */
@media (hover: none) and (pointer: coarse) {
    .hover-scale:hover {
        transform: none;
    }

    .hover-scale:active {
        transform: scale(0.98);
    }
}
</style>
