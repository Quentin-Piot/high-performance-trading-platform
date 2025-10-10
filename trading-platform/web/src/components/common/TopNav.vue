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
import { Home, BarChart3, LogIn, UserPlus, Globe } from 'lucide-vue-next'

const { navigate } = useRouter()
const { t } = useI18n()
const i18n = useI18n()
const localeRef = (i18n as unknown as { locale: { value: 'en' | 'fr' } }).locale
const selectedLocale = ref<'en' | 'fr'>(localeRef?.value ?? 'en')

watch(selectedLocale, (val) => {
  if (localeRef) localeRef.value = val
})

function go(path: string) {
  navigate(path)
}

function goHome() {
  navigate('/')
}
</script>

<template>
  <nav class="relative">
    <!-- Gradient background -->
    <div class="absolute inset-0 bg-gradient-to-r from-trading-blue/5 via-trading-purple/5 to-trading-cyan/5 rounded-2xl"></div>
    
    <!-- Navigation content -->
    <div class="relative flex items-center justify-between py-4 px-6 backdrop-blur-sm border border-white/10 rounded-2xl shadow-soft">
      <!-- Logo section avec effet hover -->
      <div 
        class="flex items-end gap-3 cursor-pointer group transition-all duration-300 hover-scale"
        @click="goHome"
      >
        <div class="relative">
          <!-- Logo avec gradient -->
          <div class="text-3xl font-bold text-trading-blue group-hover:text-trading-cyan transition-all duration-500">
            HPTP
          </div>
          <!-- Effet de brillance -->
          <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 -skew-x-12"></div>
        </div>
        <div class="flex flex-col">
          <span class="text-sm font-medium text-foreground/90 group-hover:text-trading-blue transition-colors">
            {{ t('nav.title') }}
          </span>
          <span class="text-xs text-muted-foreground group-hover:text-muted-foreground/80 transition-colors">
            {{ t('nav.subtitle') }}
          </span>
        </div>
      </div>

      <!-- Navigation links -->
      <div class="flex items-center gap-2">
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
</style>
