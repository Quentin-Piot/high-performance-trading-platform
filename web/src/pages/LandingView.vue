<script setup lang="ts">
import { useRouter } from '@/router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useI18n } from 'vue-i18n'
import { LineChart, ShieldCheck, BarChart3 } from 'lucide-vue-next'
import TopNav from '@/components/common/TopNav.vue'
import { ref, watch } from 'vue'


const i18n = useI18n()

const { navigate } = useRouter()
const { t } = useI18n()
const localeRef = (i18n as unknown as { locale: { value: 'en' | 'fr' } }).locale
const selectedLocale = ref<'en' | 'fr'>('en')
watch(selectedLocale, (val) => {
  if (localeRef) localeRef.value = val
})
function go(path: string) {
  navigate(path)
}
</script>

<template>
  <main class="container mx-auto px-4 sm:px-6 py-6 sm:py-10 space-y-6 sm:space-y-10 animate-fade-in">
    <!-- Top nav -->
    <TopNav />

    <!-- Hero Section avec dégradé et animations - optimisé mobile -->
    <section class="relative overflow-hidden rounded-xl sm:rounded-2xl border gradient-hero px-4 sm:px-8 py-8 sm:py-16 text-center shadow-strong hover-lift transition-smooth">
      <!-- Éléments décoratifs flottants - adaptés mobile -->
      <div class="absolute top-4 sm:top-8 left-4 sm:left-8 w-12 sm:w-20 h-12 sm:h-20 bg-trading-blue/20 rounded-full animate-float"></div>
      <div class="absolute top-8 sm:top-16 right-6 sm:right-12 w-8 sm:w-12 h-8 sm:h-12 bg-trading-purple/30 rounded-full animate-float" style="animation-delay: -2s;"></div>
      <div class="absolute bottom-6 sm:bottom-12 left-8 sm:left-16 w-10 sm:w-16 h-10 sm:h-16 bg-trading-cyan/25 rounded-full animate-float" style="animation-delay: -4s;"></div>
      
      <!-- Contenu principal - responsive -->
      <div class="relative z-10 animate-slide-up space-y-4 sm:space-y-6">
        <h1 class="text-2xl sm:text-4xl md:text-5xl font-bold tracking-tight gradient-text leading-tight px-2">
          {{ t('landing.title') }}
        </h1>
        <p class="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed px-2">{{ t('landing.subtitle') }}</p>
        <div class="flex justify-center gap-4 pt-2 sm:pt-4">
          <Button 
            size="lg" 
            @click="go('/simulate')" 
            class="gradient-primary text-white font-semibold px-6 sm:px-8 py-3 sm:py-4 rounded-xl shadow-medium hover-glow hover-scale transition-bounce text-sm sm:text-base"
          >
            <BarChart3 class="mr-2 h-4 w-4 sm:h-5 sm:w-5" />
            {{ t('landing.cta.startBacktest') }}
          </Button>
        </div>
      </div>
      
      <!-- Effets SF lumineux latéraux - optimisés mobile -->
      <div 
        class="sf-light sf-light-left"
        style="animation-delay: -0.8s; width: 120px; filter: blur(16px); opacity: 0.15; mix-blend-mode: screen; z-index: 5; left: 0; box-shadow: 0 0 40px rgba(99,102,241,.25), 0 0 60px rgba(168,85,247,.15); animation-duration: 6s;"
      ></div>
      <div 
        class="sf-light sf-light-right"
        style="animation-delay: 0.4s; width: 120px; filter: blur(16px); opacity: 0.15; mix-blend-mode: screen; z-index: 5; right: 0; box-shadow: 0 0 40px rgba(6,182,212,.25), 0 0 60px rgba(34,197,94,.15); animation-duration: 6s;"
      ></div>
    </section>

    <!-- Features grid avec animations échelonnées - responsive -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-8">
      <Card class="group relative overflow-hidden border-0 shadow-soft hover-lift hover-glow transition-smooth animate-scale-in bg-gradient-to-br from-card via-card to-secondary/30">
        <div class="absolute inset-0 bg-gradient-to-br from-trading-blue/5 to-trading-purple/5 opacity-0 group-hover:opacity-100 transition-smooth"></div>
        <CardHeader class="relative z-10 p-4 sm:p-6">
          <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
            <div class="rounded-xl sm:rounded-2xl bg-trading-blue/10 p-3 sm:p-4 text-trading-blue group-hover:bg-trading-blue/20 transition-smooth shadow-soft">
              <LineChart class="size-5 sm:size-6" />
            </div>
            <div class="flex-1">
              <CardTitle class="text-lg sm:text-xl font-semibold">{{ t('landing.sections.simulation.title') }}</CardTitle>
              <CardDescription class="text-muted-foreground mt-1 text-sm">Backtests rapides, paramètres clairs, résultats fiables.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent class="relative z-10 p-4 sm:p-6 pt-0">
          <p class="text-sm text-muted-foreground leading-relaxed">{{ t('landing.sections.simulation.text') }}</p>
        </CardContent>
      </Card>

      <Card class="group relative overflow-hidden border-0 shadow-soft hover-lift hover-glow transition-smooth animate-scale-in bg-gradient-to-br from-card via-card to-secondary/30" style="animation-delay: 0.1s;">
        <div class="absolute inset-0 bg-gradient-to-br from-trading-green/5 to-trading-cyan/5 opacity-0 group-hover:opacity-100 transition-smooth"></div>
        <CardHeader class="relative z-10 p-4 sm:p-6">
          <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
            <div class="rounded-xl sm:rounded-2xl bg-trading-green/10 p-3 sm:p-4 text-trading-green group-hover:bg-trading-green/20 transition-smooth shadow-soft">
              <ShieldCheck class="size-5 sm:size-6" />
            </div>
            <div class="flex-1">
              <CardTitle class="text-lg sm:text-xl font-semibold">{{ t('landing.sections.auth.title') }}</CardTitle>
              <CardDescription class="text-muted-foreground mt-1 text-sm">Flux d'authentification simplifié et sécurisé.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent class="relative z-10 p-4 sm:p-6 pt-0">
          <p class="text-sm text-muted-foreground leading-relaxed">{{ t('landing.sections.auth.text') }}</p>
        </CardContent>
      </Card>

      <Card class="group relative overflow-hidden border-0 shadow-soft hover-lift hover-glow transition-smooth animate-scale-in bg-gradient-to-br from-card via-card to-secondary/30" style="animation-delay: 0.2s;">
        <div class="absolute inset-0 bg-gradient-to-br from-trading-orange/5 to-trading-red/5 opacity-0 group-hover:opacity-100 transition-smooth"></div>
        <CardHeader class="relative z-10 p-4 sm:p-6">
          <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
            <div class="rounded-xl sm:rounded-2xl bg-trading-orange/10 p-3 sm:p-4 text-trading-orange group-hover:bg-trading-orange/20 transition-smooth shadow-soft">
              <BarChart3 class="size-5 sm:size-6" />
            </div>
            <div class="flex-1">
              <CardTitle class="text-lg sm:text-xl font-semibold">{{ t('landing.sections.visualization.title') }}</CardTitle>
              <CardDescription class="text-muted-foreground mt-1 text-sm">Visualisations nettes, thèmes lisibles, détails pertinents.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent class="relative z-10 p-4 sm:p-6 pt-0">
          <p class="text-sm text-muted-foreground leading-relaxed">{{ t('landing.sections.visualization.text') }}</p>
        </CardContent>
      </Card>
    </section>
  </main>
</template>

<style scoped>
/* Effets visuels avancés pour la landing page */
.hero-glow {
  position: relative;
}

.hero-glow::before {
  content: "";
  position: absolute;
  inset: -2px;
  border-radius: inherit;
  padding: 2px;
  background: linear-gradient(135deg, 
    var(--trading-blue), 
    var(--trading-purple), 
    var(--trading-cyan), 
    var(--trading-green)
  );
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: xor;
  -webkit-mask-composite: xor;
  opacity: 0.6;
}

/* Animation de particules flottantes - optimisée mobile */
@keyframes particle-float {
  0%, 100% { 
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
    0%, 100% { 
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

/* Effet de brillance sur les cartes */
.card-shine {
  position: relative;
  overflow: hidden;
}

.card-shine::after {
  content: '';
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

/* Gradient animé pour le texte du titre */
@keyframes gradient-shift {
  0%, 100% {
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

/* Effet de pulsation pour les éléments interactifs */
.pulse-ring {
  position: relative;
}

.pulse-ring::before {
  content: '';
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

/* Lumières SF latérales dans le hero - optimisées mobile */
.sf-light {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 120px;
  pointer-events: none;
  filter: blur(16px);
  opacity: 0;
  animation: sf-light 4s ease-in-out infinite;
}

@media (min-width: 640px) {
  .sf-light {
    width: 140px;
    filter: blur(18px);
  }
}

.sf-light-left {
  left: -20px;
  background: radial-gradient(closest-side,
    rgba(99, 102, 241, 0.25), /* indigo */
    rgba(168, 85, 247, 0.15),  /* purple */
    transparent 70%
  );
}

@media (min-width: 640px) {
  .sf-light-left {
    left: -30px;
    background: radial-gradient(closest-side,
      rgba(99, 102, 241, 0.35), /* indigo */
      rgba(168, 85, 247, 0.25),  /* purple */
      transparent 70%
    );
  }
}

.sf-light-right {
  right: -20px;
  background: radial-gradient(closest-side,
    rgba(6, 182, 212, 0.25),   /* cyan */
    rgba(34, 197, 94, 0.15),   /* green */
    transparent 70%
  );
}

@media (min-width: 640px) {
  .sf-light-right {
    right: -30px;
    background: radial-gradient(closest-side,
      rgba(6, 182, 212, 0.35),   /* cyan */
      rgba(34, 197, 94, 0.25),   /* green */
      transparent 70%
    );
  }
}

@keyframes sf-light {
  0%, 100% { opacity: 0; transform: translateY(0); }
  50% { opacity: 0.6; transform: translateY(-6px); }
}

@media (min-width: 640px) {
  @keyframes sf-light {
    0%, 100% { opacity: 0; transform: translateY(0); }
    50% { opacity: 0.8; transform: translateY(-8px); }
  }
}

/* Optimisations tactiles pour mobile */
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
  
  /* Réduire les animations sur mobile pour les performances */
  .animate-float {
    animation-duration: 12s;
  }
  
  .gradient-text {
    animation-duration: 6s;
  }
}

/* Amélioration des performances sur mobile */
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
  
  /* Réduire le blur pour les performances */
  .backdrop-blur-sm {
    backdrop-filter: blur(4px);
  }
}
</style>
