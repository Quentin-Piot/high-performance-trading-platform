<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AuthForm from '@/components/auth/AuthForm.vue'
import { useAuthStore } from '@/stores/authStore'
import { useRouter } from '@/router'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Globe, Home } from 'lucide-vue-next'

const auth = useAuthStore()
const { navigate } = useRouter()
const { t } = useI18n()
const i18n = useI18n()

const localeRef = (i18n as unknown as { locale: { value: "en" | "fr" } }).locale
const selectedLocale = ref<"en" | "fr">(localeRef?.value ?? "en")

watch(selectedLocale, (val) => {
  if (localeRef) localeRef.value = val
})

function goHome() {
  navigate('/')
}

onMounted(async () => {
  // Rehydrate auth state first
  auth.rehydrate()
  
  // Check for Google OAuth callback
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.has('auth') || urlParams.has('error')) {
    const success = await auth.handleGoogleCallback()
    if (success) {
      navigate('/simulate')
      return
    }
  }
  
  // Check if already authenticated after rehydration
  if (auth.isAuthenticated) navigate('/simulate')
})
</script>

<template>
  <div class="min-h-screen flex">
    <!-- Left side - Auth Form -->
    <div class="w-full lg:w-1/2 flex flex-col items-center justify-center p-8 bg-background relative">
      <!-- Top controls -->
      <div class="absolute top-6 left-6 right-6 flex items-center justify-between">
        <!-- Home button -->
        <Button
          variant="ghost"
          size="sm"
          class="h-9 px-4 text-muted-foreground hover:bg-trading-blue/10 hover:text-trading-blue transition-all duration-300 hover-scale group"
          @click="goHome"
        >
          <Home class="size-4 mr-2 group-hover:rotate-12 transition-transform duration-300" />
          {{ t('auth.login.backToHome') }}
        </Button>

        <!-- Language selector -->
        <div class="relative">
          <Select v-model="selectedLocale">
            <SelectTrigger
              size="sm"
              class="h-9 w-36 border-border/20 text-muted-foreground hover:border-trading-cyan hover:bg-trading-cyan/10 transition-all duration-300 hover-scale group justify-start"
            >
              <Globe class="size-4 mr-2 text-trading-cyan group-hover:rotate-180 transition-transform duration-500" />
              <SelectValue :placeholder="selectedLocale === 'fr' ? 'Français' : 'English'" />
            </SelectTrigger>
            <SelectContent class="border-border/10 bg-card/95 backdrop-blur-sm w-36">
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

      <div class="w-full max-w-md">
        <AuthForm mode="login" />
      </div>
    </div>

    <!-- Right side - Gradient Background -->
    <div class="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-[#161c2b] via-[#1c162e] to-[#23183a]">
      <!-- Animated gradient overlay -->
      <div class="absolute inset-0 bg-gradient-to-tr from-blue-500/15 via-purple-500/10 to-cyan-500/15"></div>
      
      <!-- Decorative elements -->
      <div class="absolute top-20 right-20 w-72 h-72 bg-blue-400/20 rounded-full blur-3xl animate-pulse"></div>
      <div class="absolute bottom-20 left-20 w-96 h-96 bg-purple-500/15 rounded-full blur-3xl animate-pulse delay-1000"></div>
      <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-cyan-400/10 rounded-full blur-3xl animate-pulse delay-500"></div>
      
      <!-- Content -->
      <div class="relative z-10 flex flex-col items-start justify-center p-16 text-white">
        <div class="space-y-6">
          <h1 class="text-5xl font-bold tracking-tight">
            {{ t('auth.login.welcome') }}
          </h1>
          <p class="text-xl text-white/80 max-w-md leading-relaxed">
            {{ t('auth.login.description') }}
          </p>
          
          <!-- Feature highlights -->
          <div class="mt-12 space-y-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
              </div>
              <span class="text-blue-50">{{ t('auth.login.features.secure') }}</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                </svg>
              </div>
              <span class="text-blue-50">{{ t('auth.login.features.fast') }}</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                </svg>
              </div>
              <span class="text-blue-50">{{ t('auth.login.features.advanced') }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Bottom decorative line -->
      <div class="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
    </div>
  </div>
</template>

<style scoped>
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.animate-pulse {
  animation: pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.delay-500 {
  animation-delay: 0.5s;
}

.delay-1000 {
  animation-delay: 1s;
}

.hover-scale:hover {
  transform: scale(1.02);
}
</style>