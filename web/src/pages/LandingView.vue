<script setup lang="ts">
import { useRouter } from "@/router";
import { Button } from "@/components/ui/button";
import { useI18n } from "vue-i18n";
import { BarChart3 } from "lucide-vue-next";
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
        class="min-h-screen flex flex-col justify-center items-center px-4 sm:px-6 animate-fade-in"
    >
        <div class="absolute top-6 left-0 right-0">
            <TopNav />
        </div>

        <section
            class="liquid-glass-hero gradient-hero relative overflow-hidden rounded-xl sm:rounded-2xl px-6 sm:px-12 py-12 sm:py-20 text-center max-w-4xl mx-auto"
        >
            <!-- Liquid Glass Background Layers -->
            <div class="liquid-glass-bg"></div>
            <div class="liquid-glass-overlay"></div>
            <div class="liquid-glass-reflection"></div>
            <div class="liquid-glass-shimmer"></div>
            <div class="liquid-glass-noise"></div>

            <div class="relative z-10 animate-slide-up space-y-6 sm:space-y-8">
                <h1
                    class="text-3xl sm:text-3xl md:text-5xl font-bold tracking-tight gradient-text hero-title leading-tight"
                >
                    {{ t("landing.title") }}
                </h1>
                <p
                    class="text-md sm:text-lg hero-description max-w-3xl mx-auto leading-relaxed"
                >
                    {{ t("landing.subtitle") }}
                </p>
                <div class="flex justify-center gap-4 pt-4 sm:pt-6">
                    <Button
                        size="lg"
                        class="gradient-primary text-white font-semibold px-8 sm:px-12 py-4 sm:py-5 rounded-xl shadow-medium hover-glow hover-scale transition-bounce text-base sm:text-lg"
                        @click="go('/simulate')"
                    >
                        <BarChart3 class="mr-3 h-5 w-5 sm:h-6 sm:w-6" />
                        {{ t("landing.cta.startBacktest") }}
                    </Button>
                </div>
            </div>
        </section>
    </main>
</template>

<style scoped>
/* Liquid Glass + Glassmorphism — Apple-inspired */
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
    transition:
        transform 400ms cubic-bezier(0.4, 0, 0.2, 1),
        background 400ms ease,
        box-shadow 400ms ease;
}

.liquid-glass-hero:hover {
    background: rgba(255, 255, 255, 0.08);
    box-shadow:
        0 18px 56px rgba(0, 0, 0, 0.22),
        inset 0 1px 0 rgba(255, 255, 255, 0.22),
        inset 0 -1px 0 rgba(255, 255, 255, 0.16);
    transform: translateY(-2px);
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
    animation: liquid-gradient 18s ease-in-out infinite;
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
        45deg,
        transparent 30%,
        rgba(255, 255, 255, 0.12) 50%,
        transparent 70%
    );
    background-size: 180% 180%;
    animation: shimmer 5s ease-in-out infinite;
    border-radius: inherit;
    opacity: 0;
    transition: opacity 300ms ease;
}

.liquid-glass-hero:hover .liquid-glass-shimmer {
    opacity: 1;
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
    background-size:
        180% 180%,
        100% 100%,
        100% 100%;
    background-position:
        0% 0%,
        0% 0%,
        0% 0%;
    animation: specular-sweep 7s ease-in-out infinite;
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

@keyframes specular-sweep {
    0% {
        background-position:
            -100% 0%,
            0% 0%,
            0% 0%;
    }
    50% {
        background-position:
            30% 0%,
            0% 0%,
            0% 0%;
    }
    100% {
        background-position:
            140% 0%,
            0% 0%,
            0% 0%;
    }
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
        background: rgba(0, 0, 0, 0.28);
        border-color: rgba(255, 255, 255, 0.14);
        box-shadow:
            0 10px 40px rgba(0, 0, 0, 0.35),
            inset 0 1px 0 rgba(255, 255, 255, 0.14),
            inset 0 -1px 0 rgba(255, 255, 255, 0.08);
    }

    .liquid-glass-hero:hover {
        background: rgba(0, 0, 0, 0.34);
        box-shadow:
            0 16px 52px rgba(0, 0, 0, 0.45),
            inset 0 1px 0 rgba(255, 255, 255, 0.18),
            inset 0 -1px 0 rgba(255, 255, 255, 0.1);
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
