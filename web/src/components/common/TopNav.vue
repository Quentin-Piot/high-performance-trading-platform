<script setup lang="ts">
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
import { useI18n } from 'vue-i18n'
import { ref, watch } from 'vue'
import { Home, BarChart3, LogIn, UserPlus, Globe, Menu, X } from 'lucide-vue-next'

const { navigate } = useRouter()
const { t } = useI18n()
const i18n = useI18n()
const localeRef = (i18n as unknown as { locale: { value: 'en' | 'fr' } }).locale
const selectedLocale = ref<'en' | 'fr'>(localeRef?.value ?? 'en')
const mobileMenuOpen = ref(false)

watch(selectedLocale, (val) => {
  if (localeRef) localeRef.value = val
})

function go(path: string) {
  navigate(path)
  mobileMenuOpen.value = false
}

function goHome() {
  navigate('/')
  mobileMenuOpen.value = false
}

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}
</script>

<template>
  <nav class="relative">
    <!-- Gradient background -->
    <div class="absolute inset-0 bg-gradient-to-r from-trading-blue/5 via-trading-purple/5 to-trading-cyan/5 rounded-2xl"></div>
    
    <!-- Navigation content -->
    <div class="relative flex items-center justify-between py-3 px-4 sm:py-4 sm:px-6 backdrop-blur-sm border border-white/10 rounded-2xl shadow-soft">
      <!-- Logo section avec effet hover - responsive -->
      <div 
        class="flex items-end gap-2 sm:gap-3 cursor-pointer group transition-all duration-300 hover-scale"
        @click="goHome"
      >
        <div class="relative">
          <!-- Logo avec gradient - taille adaptative -->
          <div class="text-2xl sm:text-3xl font-bold text-trading-blue group-hover:text-trading-cyan transition-all duration-500">
            HPTP
          </div>
          <!-- Effet de brillance -->
          <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 -skew-x-12"></div>
        </div>
        <div class="hidden sm:flex flex-col">
          <span class="text-sm font-medium text-foreground/90 group-hover:text-trading-blue transition-colors">
            {{ t('nav.title') }}
          </span>
          <span class="text-xs text-muted-foreground group-hover:text-muted-foreground/80 transition-colors">
            {{ t('nav.subtitle') }}
          </span>
        </div>
      </div>

      <!-- Desktop Navigation -->
      <div class="hidden lg:flex items-center gap-2">
        <!-- Home button -->
        <Button 
          variant="ghost" 
          size="sm" 
          class="h-9 px-4 hover:bg-trading-blue/10 hover:text-trading-blue transition-all duration-300 hover-scale group"
          @click="go('/')"
        >
          <Home class="size-4 mr-2 group-hover:rotate-12 transition-transform duration-300" />
          {{ t('nav.home') }}
        </Button>

        <!-- Simulation button -->
        <Button 
          variant="ghost" 
          size="sm" 
          class="h-9 px-4 hover:bg-trading-purple/10 hover:text-trading-purple transition-all duration-300 hover-scale group"
          @click="go('/simulate')"
        >
          <BarChart3 class="size-4 mr-2 group-hover:scale-110 transition-transform duration-300" />
          {{ t('nav.simulate') }}
        </Button>

        <!-- Divider -->
        <div class="w-px h-6 bg-border/50 mx-2"></div>

        <!-- Auth buttons -->
        <Button 
          variant="outline" 
          size="sm" 
          class="h-9 px-4 border-trading-blue/20 hover:border-trading-blue hover:bg-trading-blue/5 hover:text-trading-blue transition-all duration-300 hover-scale group"
          @click="go('/login')"
        >
          <LogIn class="size-4 mr-2 group-hover:-rotate-12 transition-transform duration-300" />
          {{ t('nav.login') }}
        </Button>

        <Button 
          size="sm" 
          class="h-9 px-4 bg-trading-blue text-white rounded-lg border border-trading-blue hover:bg-trading-blue/80 hover:border-trading-blue/80 transition-all duration-300 hover-scale group"
          @click="go('/register')"
        >
          <UserPlus class="size-4 mr-2 group-hover:scale-110 transition-transform duration-300" />
          {{ t('nav.register') }}
        </Button>

        <!-- Language selector -->
        <div class="relative ml-2">
          <Select v-model="selectedLocale">
            <SelectTrigger 
              size="sm" 
              class="h-9 w-36 border-trading-cyan/20 hover:border-trading-cyan hover:bg-trading-cyan/5 transition-all duration-300 hover-scale group justify-start"
            >
              <Globe class="size-4 mr-2 text-trading-cyan group-hover:rotate-180 transition-transform duration-500" />
              <SelectValue :placeholder="selectedLocale === 'fr' ? 'Français' : 'English'" />
            </SelectTrigger>
            <SelectContent class="border-white/10 bg-card/95 backdrop-blur-sm w-36">
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
              class="h-9 w-12 border-trading-cyan/20 hover:border-trading-cyan hover:bg-trading-cyan/5 transition-all duration-300 hover-scale group justify-center"
            >
              <Globe class="size-4 text-trading-cyan group-hover:rotate-180 transition-transform duration-500" />
            </SelectTrigger>
            <SelectContent class="border-white/10 bg-card/95 backdrop-blur-sm w-32">
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
          class="h-9 w-9 p-0 hover:bg-trading-blue/10 hover:text-trading-blue transition-all duration-300 hover-scale"
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
      <div class="bg-card/95 backdrop-blur-sm border border-white/10 rounded-2xl shadow-strong p-4 space-y-3">
        <!-- Navigation mobile -->
        <div class="space-y-2">
          <Button 
            variant="ghost" 
            size="sm" 
            class="w-full justify-start h-10 px-4 hover:bg-trading-blue/10 hover:text-trading-blue transition-all duration-300 group"
            @click="go('/')"
          >
            <Home class="size-4 mr-3 group-hover:rotate-12 transition-transform duration-300" />
            {{ t('nav.home') }}
          </Button>

          <Button 
            variant="ghost" 
            size="sm" 
            class="w-full justify-start h-10 px-4 hover:bg-trading-purple/10 hover:text-trading-purple transition-all duration-300 group"
            @click="go('/simulate')"
          >
            <BarChart3 class="size-4 mr-3 group-hover:scale-110 transition-transform duration-300" />
            {{ t('nav.simulate') }}
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
            <LogIn class="size-4 mr-3 group-hover:-rotate-12 transition-transform duration-300" />
            {{ t('nav.login') }}
          </Button>

          <Button 
            size="sm" 
            class="w-full justify-start h-10 px-4 bg-trading-blue text-white rounded-lg border border-trading-blue hover:bg-trading-blue/80 hover:border-trading-blue/80 transition-all duration-300 group"
            @click="go('/register')"
          >
            <UserPlus class="size-4 mr-3 group-hover:scale-110 transition-transform duration-300" />
            {{ t('nav.register') }}
          </Button>
        </div>
      </div>
    </div>

    <!-- Subtle glow effect -->
    <div class="absolute inset-0 bg-gradient-to-r from-trading-blue/10 via-trading-purple/10 to-trading-cyan/10 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 -z-10"></div>
  </nav>
</template>

<style scoped>
/* Enhanced hover effects */
.hover-scale:hover {
  transform: scale(1.02);
}

/* Gradient text animation */
@keyframes gradient-shift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
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
