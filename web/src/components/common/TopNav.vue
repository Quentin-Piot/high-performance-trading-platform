<script setup lang="ts">
import { useRouter } from "@/router";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectGroup,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { useI18n } from "vue-i18n";
import { ref, watch, computed } from "vue";
import {
    Home,
    BarChart3,
    LogIn,
    UserPlus,
    Globe,
    Menu,
    X,
    LogOut,
    Settings,
    History,
} from "lucide-vue-next";
const { navigate } = useRouter();
const { t } = useI18n();
const i18n = useI18n();
const auth = useAuthStore();
const localeRef = (i18n as unknown as { locale: { value: "en" | "fr" } })
    .locale;
const selectedLocale = ref<"en" | "fr">(localeRef?.value ?? "en");
const mobileMenuOpen = ref(false);
const isAuthenticated = computed(() => auth.isAuthenticated);
const userName = computed(() => auth.userName || auth.userEmail || "User");
const userProvider = computed(() => auth.user?.provider || "cognito");
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
async function handleLogout() {
    await auth.logout();
    navigate("/");
    mobileMenuOpen.value = false;
}
</script>
<template>
    <nav class="relative">
        <div class="liquid-glass-hero">
            <div class="liquid-glass-bg"></div>
            <div class="liquid-glass-overlay"></div>
            <div class="liquid-glass-reflection"></div>
            <div class="liquid-glass-shimmer"></div>
            <div class="liquid-glass-noise"></div>
        </div>
        <div class="relative z-10 mx-auto max-w-7xl">
            <div
                class="flex items-center justify-between py-4 px-4 sm:px-6 lg:px-8"
            >
                <div
                    class="flex items-end gap-2 sm:gap-3 cursor-pointer group transition-all duration-300 hover-scale"
                    @click="goHome"
                >
                    <div class="relative">
                        <div
                            class="text-2xl sm:text-3xl font-bold gradient-text group-hover:scale-105 transition-all duration-500"
                        >
                            HPTP
                        </div>
                        <div
                            class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 -skew-x-12"
                        ></div>
                    </div>
                    <div class="hidden sm:flex flex-col">
                        <span
                            class="text-sm font-medium text-white/90 group-hover:text-blue-400 transition-colors"
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
                <div class="hidden lg:flex items-center gap-3">
                    <div class="flex items-center gap-2 mr-4">
                        <Button
                            variant="ghost"
                            size="sm"
                            class="h-9 px-4 text-white/90 hover:bg-white/10 hover:text-white transition-all duration-300"
                            @click="go('/')"
                        >
                            <Home class="size-4 mr-2" />
                            <span class="font-medium">{{ t("nav.home") }}</span>
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            class="h-9 px-4 text-white/90 hover:bg-white/10 hover:text-white transition-all duration-300"
                            @click="go('/simulate')"
                        >
                            <BarChart3 class="size-4 mr-2" />
                            <span class="font-medium">{{
                                t("nav.simulate")
                            }}</span>
                        </Button>
                        <Button
                            v-if="isAuthenticated"
                            variant="ghost"
                            size="sm"
                            class="h-9 px-4 text-white/90 hover:bg-white/10 hover:text-white transition-all duration-300"
                            @click="go('/history')"
                        >
                            <History class="size-4 mr-2" />
                            <span class="font-medium">{{
                                t("nav.history")
                            }}</span>
                        </Button>
                    </div>
                    <div class="flex items-center gap-2">
                        <Select v-model="selectedLocale">
                            <SelectTrigger
                                size="sm"
                                class="h-9 w-32 border-white/20 bg-white/5 text-white/90 hover:bg-white/10 hover:border-white/30 transition-all duration-300"
                            >
                                <Globe class="size-4 mr-2 text-blue-400" />
                                <SelectValue
                                    :placeholder="
                                        selectedLocale === 'fr'
                                            ? 'Français'
                                            : 'English'
                                    "
                                />
                            </SelectTrigger>
                            <SelectContent
                                class="border-white/10 bg-[#1a1f2e]/98 backdrop-blur-xl"
                            >
                                <SelectGroup>
                                    <SelectItem
                                        value="en"
                                        class="text-white/90 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
                                    >
                                        English
                                    </SelectItem>
                                    <SelectItem
                                        value="fr"
                                        class="text-white/90 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
                                    >
                                        Français
                                    </SelectItem>
                                </SelectGroup>
                            </SelectContent>
                        </Select>
                        <div class="w-px h-6 bg-white/20 mx-1"></div>
                        <div v-if="isAuthenticated" class="flex items-center">
                            <Popover>
                                <PopoverTrigger as-child>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        class="h-9 px-3 text-white/90 hover:bg-white/10 hover:text-white transition-all duration-300 gap-2"
                                    >
                                        <div class="flex items-center gap-2">
                                            <div
                                                class="w-7 h-7 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-xs font-semibold"
                                            >
                                                {{
                                                    userName
                                                        .charAt(0)
                                                        .toUpperCase()
                                                }}
                                            </div>
                                            <span
                                                class="max-w-24 truncate font-medium"
                                                >{{ userName }}</span
                                            >
                                        </div>
                                    </Button>
                                </PopoverTrigger>
                                <PopoverContent
                                    class="w-64 border-white/10 bg-[#1a1f2e]/98 backdrop-blur-xl p-0"
                                >
                                    <div class="p-4 border-b border-white/10">
                                        <div class="flex items-center gap-3">
                                            <div
                                                class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white font-semibold"
                                            >
                                                {{
                                                    userName
                                                        .charAt(0)
                                                        .toUpperCase()
                                                }}
                                            </div>
                                            <div class="flex-1 min-w-0">
                                                <div
                                                    class="text-white/90 font-medium truncate"
                                                >
                                                    {{ userName }}
                                                </div>
                                                <div
                                                    class="text-xs text-white/60 flex items-center gap-1"
                                                >
                                                    <div
                                                        class="size-1.5 rounded-full"
                                                        :class="{
                                                            'bg-blue-400':
                                                                userProvider ===
                                                                'google',
                                                            'bg-orange-400':
                                                                userProvider ===
                                                                'cognito',
                                                        }"
                                                    ></div>
                                                    {{
                                                        userProvider ===
                                                        "google"
                                                            ? "Google"
                                                            : "Cognito"
                                                    }}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="p-2">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            class="w-full justify-start h-9 px-3 text-white/90 hover:bg-white/10 hover:text-white"
                                        >
                                            <Settings class="size-4 mr-3" />
                                            Settings
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            class="w-full justify-start h-9 px-3 text-white/90 hover:bg-red-500/10 hover:text-red-400"
                                            @click="handleLogout"
                                        >
                                            <LogOut class="size-4 mr-3" />
                                            Logout
                                        </Button>
                                    </div>
                                </PopoverContent>
                            </Popover>
                        </div>
                        <div v-else class="flex items-center gap-2">
                            <Button
                                variant="ghost"
                                size="sm"
                                class="h-9 px-4 text-white/90 hover:bg-white/10 hover:text-white transition-all duration-300"
                                @click="go('/login')"
                            >
                                <LogIn class="size-4 mr-2" />
                                <span class="font-medium">{{
                                    t("nav.login")
                                }}</span>
                            </Button>
                            <Button
                                size="sm"
                                class="h-9 px-4 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white font-medium shadow-lg shadow-blue-500/25 transition-all duration-300"
                                @click="go('/register')"
                            >
                                <UserPlus class="size-4 mr-2" />
                                {{ t("nav.register") }}
                            </Button>
                        </div>
                    </div>
                </div>
                <div class="flex lg:hidden items-center gap-3">
                    <Select v-model="selectedLocale">
                        <SelectTrigger
                            size="sm"
                            class="h-9 w-20 border-white/20 bg-white/5 text-white/90 hover:bg-white/10"
                        >
                            <Globe class="size-4 text-blue-400" />
                            <span class="text-xs font-medium ml-1">
                                {{ selectedLocale.toUpperCase() }}
                            </span>
                        </SelectTrigger>
                        <SelectContent
                            class="border-white/10 bg-[#1a1f2e]/98 backdrop-blur-xl"
                        >
                            <SelectGroup>
                                <SelectItem
                                    value="en"
                                    class="text-white/90 hover:bg-white/10 hover:text-white cursor-pointer"
                                >
                                    English
                                </SelectItem>
                                <SelectItem
                                    value="fr"
                                    class="text-white/90 hover:bg-white/10 hover:text-white cursor-pointer"
                                >
                                    Français
                                </SelectItem>
                            </SelectGroup>
                        </SelectContent>
                    </Select>
                    <Button
                        variant="ghost"
                        size="sm"
                        class="h-9 w-9 p-0 text-white/90 hover:bg-white/10 hover:text-white transition-all duration-300"
                        @click="toggleMobileMenu"
                    >
                        <Menu v-if="!mobileMenuOpen" class="size-5" />
                        <X v-else class="size-5" />
                    </Button>
                </div>
            </div>
        </div>
        <Transition name="mobile-menu">
            <div
                v-if="mobileMenuOpen"
                class="lg:hidden absolute top-full left-0 right-0 mt-2 px-4 z-50"
            >
                <div
                    class="bg-[#1a1f2e]/98 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
                >
                    <div class="p-3 space-y-1">
                        <Button
                            variant="ghost"
                            size="sm"
                            class="w-full justify-start h-11 px-4 text-white/90 hover:bg-white/10 hover:text-white transition-all"
                            @click="go('/')"
                        >
                            <Home class="size-5 mr-3" />
                            <span class="font-medium">{{ t("nav.home") }}</span>
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            class="w-full justify-start h-11 px-4 text-white/90 hover:bg-white/10 hover:text-white transition-all"
                            @click="go('/simulate')"
                        >
                            <BarChart3 class="size-5 mr-3" />
                            <span class="font-medium">{{
                                t("nav.simulate")
                            }}</span>
                        </Button>
                        <Button
                            v-if="isAuthenticated"
                            variant="ghost"
                            size="sm"
                            class="w-full justify-start h-11 px-4 text-white/90 hover:bg-white/10 hover:text-white transition-all"
                            @click="go('/history')"
                        >
                            <History class="size-5 mr-3" />
                            <span class="font-medium">{{
                                t("nav.history")
                            }}</span>
                        </Button>
                    </div>
                    <div class="h-px bg-white/10"></div>
                    <div v-if="isAuthenticated" class="p-3 space-y-2">
                        <div
                            class="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10"
                        >
                            <div
                                class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white font-semibold flex-shrink-0"
                            >
                                {{ userName.charAt(0).toUpperCase() }}
                            </div>
                            <div class="flex-1 min-w-0">
                                <div
                                    class="text-sm font-medium text-white/90 truncate"
                                >
                                    {{ userName }}
                                </div>
                                <div
                                    class="text-xs text-white/60 flex items-center gap-1.5"
                                >
                                    <div
                                        class="size-1.5 rounded-full"
                                        :class="{
                                            'bg-blue-400':
                                                userProvider === 'google',
                                            'bg-orange-400':
                                                userProvider === 'cognito',
                                        }"
                                    ></div>
                                    {{
                                        userProvider === "google"
                                            ? "Google Account"
                                            : "Cognito Account"
                                    }}
                                </div>
                            </div>
                        </div>
                        <Button
                            variant="ghost"
                            size="sm"
                            class="w-full justify-start h-11 px-4 text-white/90 hover:bg-white/10 hover:text-white transition-all"
                        >
                            <Settings class="size-5 mr-3" />
                            <span class="font-medium">Settings</span>
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            class="w-full justify-start h-11 px-4 text-white/90 hover:bg-red-500/10 hover:text-red-400 transition-all"
                            @click="handleLogout"
                        >
                            <LogOut class="size-5 mr-3" />
                            <span class="font-medium">Logout</span>
                        </Button>
                    </div>
                    <div v-else class="p-3 space-y-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            class="w-full justify-start h-11 px-4 text-white/90 hover:bg-white/10 hover:text-white transition-all"
                            @click="go('/login')"
                        >
                            <LogIn class="size-5 mr-3" />
                            <span class="font-medium">{{
                                t("nav.login")
                            }}</span>
                        </Button>
                        <Button
                            size="sm"
                            class="w-full justify-start h-11 px-4 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white font-medium"
                            @click="go('/register')"
                        >
                            <UserPlus class="size-5 mr-3" />
                            <span class="font-medium">{{
                                t("nav.register")
                            }}</span>
                        </Button>
                    </div>
                </div>
            </div>
        </Transition>
    </nav>
</template>
<style scoped>
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
.hover-scale:hover {
    transform: scale(1.02);
}
.mobile-menu-enter-active,
.mobile-menu-leave-active {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.mobile-menu-enter-from {
    opacity: 0;
    transform: translateY(-8px);
}
.mobile-menu-leave-to {
    opacity: 0;
    transform: translateY(-8px);
}
</style>