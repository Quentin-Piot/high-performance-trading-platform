<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
    Dialog,
    DialogTrigger,
    DialogScrollContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from "@/components/ui/dialog";
import type { Component } from "vue";
interface Section {
    icon: Component;
    titleKey?: string;
    title?: string;
    points: string[];
}
interface Props {
    cardId: string;
    icon: Component;
    gradient: string;
    glowColor: string;
    sections: Section[];
}
const props = defineProps<Props>();
const { t } = useI18n();
const getCtaColor = () => {
    if (props.gradient.includes("green"))
        return "text-trading-green";
    if (props.gradient.includes("purple"))
        return "text-trading-purple";
    if (props.gradient.includes("orange"))
        return "text-trading-orange";
    return "text-trading-blue";
};
</script>
<template>
    <Dialog>
        <DialogTrigger as-child>
            <button
                type="button"
                :aria-label="t(`landing.project.${cardId}.title`) + ' - ' + t(`landing.project.${cardId}.click_to_${cardId === 'frontend' ? 'architecture' : cardId === 'backend' ? 'system_design' : 'iac_cloud'}`)"
                class="group cursor-pointer h-full transition-transform duration-500 ease-out hover:-translate-y-2 w-full border-0 bg-transparent p-0"
            >
                <div
                    class="arch-card relative h-full rounded-3xl overflow-hidden bg-card/90 backdrop-blur-xl border border-border shadow-xl transition-all duration-500"
                >
                    <div
                        class="arch-glow absolute -inset-0.5 rounded-3xl opacity-0 group-hover:opacity-60 transition-opacity duration-500 blur-xl -z-10"
                        :style="{
                            background: `linear-gradient(135deg, ${glowColor}, transparent)`,
                        }"
                    ></div>
                    <div
                        class="absolute inset-0 bg-gradient-to-br from-primary/5 to-primary/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                    ></div>
                    <div
                        class="relative p-8 flex flex-col items-center text-center h-full"
                    >
                        <div
                            :class="`w-16 h-16 rounded-2xl bg-gradient-to-br ${gradient} flex items-center justify-center mb-6 shadow-lg transition-transform duration-500 group-hover:scale-110 group-hover:rotate-6`"
                        >
                            <component :is="icon" class="h-8 w-8 text-white" />
                        </div>
                        <h3
                            class="text-2xl font-bold text-foreground mb-4 leading-tight"
                        >
                            {{ t(`landing.project.${cardId}.title`) }}
                        </h3>
                        <p
                            class="text-base text-muted-foreground leading-relaxed flex-1 mb-6"
                        >
                            {{ t(`landing.project.${cardId}.description`) }}
                        </p>
                        <div
                            :class="`flex items-center justify-center font-semibold ${getCtaColor()} transition-transform duration-300 group-hover:translate-x-1`"
                        >
                            <span class="text-sm">
                                {{
                                    t(
                                        `landing.project.${cardId}.click_to_${cardId === "frontend" ? "architecture" : cardId === "backend" ? "system_design" : "iac_cloud"}`,
                                    )
                                }}
                            </span>
                            <svg
                                class="w-4 h-4 ml-1.5 transition-transform duration-300 group-hover:translate-x-1"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2.5"
                                    d="M9 5l7 7-7 7"
                                />
                            </svg>
                        </div>
                    </div>
                </div>
            </button>
        </DialogTrigger>
        <DialogScrollContent
            class="modal-glass sm:max-w-4xl p-0 border-0 overflow-hidden bg-card"
        >
            <DialogHeader
                class="p-10 pb-6 flex flex-col items-center text-center border-b border-border relative"
            >
                <div
                    :class="`w-14 h-14 rounded-2xl bg-gradient-to-br ${gradient} flex items-center justify-center mb-5 shadow-xl`"
                >
                    <component :is="icon" class="h-7 w-7 text-white" />
                </div>
                <DialogTitle
                    class="text-3xl font-bold text-foreground mb-3 tracking-tight"
                >
                    {{
                        t(
                            `landing.architecture.${cardId === "infrastructure" ? "infra_dialog" : cardId}.title`,
                        )
                    }}
                </DialogTitle>
                <DialogDescription
                    class="text-lg text-muted-foreground leading-relaxed max-w-2xl"
                >
                    {{
                        t(
                            `landing.architecture.${cardId === "infrastructure" ? "infra_dialog" : cardId}.description`,
                        )
                    }}
                </DialogDescription>
            </DialogHeader>
            <div class="p-10 pt-8 space-y-8 overflow-y-auto max-h-[60vh]">
                <div
                    v-for="(section, idx) in sections"
                    :key="idx"
                    class="modal-section relative rounded-2xl p-7 backdrop-blur-md bg-gradient-to-r from-secondary/80 to-secondary/50 border border-border shadow-lg hover:shadow-xl hover:bg-secondary/90 transition-all duration-300"
                >
                    <div class="flex items-center gap-3 mb-5">
                        <div
                            :class="`w-8 h-8 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-md`"
                        >
                            <component
                                :is="section.icon"
                                class="h-4 w-4 text-white"
                            />
                        </div>
                        <h4
                            class="text-xl font-bold text-foreground tracking-tight"
                        >
                            {{
                                section.titleKey
                                    ? t(section.titleKey)
                                    : section.title
                            }}
                        </h4>
                    </div>
                    <div class="space-y-4">
                        <div
                            v-for="(point, pointIdx) in section.points"
                            :key="pointIdx"
                            class="flex items-start gap-4 p-3.5 rounded-xl backdrop-blur-sm bg-muted/50 border border-border hover:bg-muted/70 hover:translate-x-1 transition-all duration-300"
                        >
                            <div
                                class="w-1.5 h-1.5 rounded-full bg-gradient-to-br from-primary to-primary/80 mt-2 flex-shrink-0 shadow-sm"
                            ></div>
                            <p
                                class="text-[15px] text-foreground leading-relaxed"
                            >
                                {{ t(point) }}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </DialogScrollContent>
    </Dialog>
</template>
<style scoped>
.modal-glass {
    background: linear-gradient(
        135deg,
        rgba(22, 28, 43, 0.45) 0%,
        rgba(28, 22, 46, 0.45) 55%,
        rgba(35, 24, 58, 0.45) 100%
    ) !important;
    backdrop-filter: blur(40px) saturate(1.4) !important;
    -webkit-backdrop-filter: blur(40px) saturate(1.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    box-shadow:
        0 20px 60px rgba(0, 0, 0, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.3),
        inset 0 -1px 0 rgba(255, 255, 255, 0.15) !important;
    border-radius: 28px !important;
}
@media (prefers-color-scheme: dark) {
    .modal-glass {
        background: linear-gradient(
            135deg,
            rgba(22, 28, 43, 0.65) 0%,
            rgba(28, 22, 46, 0.65) 55%,
            rgba(35, 24, 58, 0.65) 100%
        ) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        box-shadow:
            0 20px 60px rgba(0, 0, 0, 0.6),
            inset 0 1px 0 rgba(255, 255, 255, 0.12),
            inset 0 -1px 0 rgba(255, 255, 255, 0.06) !important;
    }
}
@media (max-width: 640px) {
    .modal-glass {
        max-width: calc(100vw - 2rem) !important;
        max-height: calc(100vh - 2rem) !important;
        margin: 1rem;
    }
}
</style>