<script setup lang="ts">
import { useRouter } from '@/router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useI18n } from 'vue-i18n'
import { LineChart, ShieldCheck, Zap, BarChart3 } from 'lucide-vue-next'
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
  <main class="container mx-auto px-6 py-10 space-y-10">
    <!-- Top nav -->
    <TopNav />

    <!-- Hero -->
    <section class="relative overflow-hidden rounded-xl border bg-secondary/50 p-10 text-center shadow-sm">
      <div class="absolute inset-0 -z-10 opacity-30 " aria-hidden="true"></div>
      <h1 class="text-4xl font-bold tracking-tight">{{ t('landing.title') }}</h1>
      <p class="text-muted-foreground max-w-2xl mx-auto mt-3">{{ t('landing.subtitle') }}</p>
      <div class="flex justify-center gap-3 mt-6">
        <Button size="lg" @click="go('/simulate')" class="  transition-transform hover:scale-[1.02]">
          {{ t('landing.cta.startBacktest') }}
        </Button>
      </div>
    </section>

    <!-- Features grid -->
    <section class="grid md:grid-cols-3 gap-6">
      <Card class="transition-all hover:shadow-lg group">
        <CardHeader>
          <div class="flex items-center gap-3">
            <div class="rounded-full bg-primary/10 p-2 text-primary">
              <LineChart class="size-5" />
            </div>
            <div>
              <CardTitle>{{ t('landing.sections.simulation.title') }}</CardTitle>
              <CardDescription>Backtests rapides, paramètres clairs, résultats fiables.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p class="text-sm text-muted-foreground">{{ t('landing.sections.simulation.text') }}</p>
        </CardContent>
      </Card>
      <Card class="transition-all hover:shadow-lg group">
        <CardHeader>
          <div class="flex items-center gap-3">
            <div class="rounded-full bg-primary/10 p-2 text-primary">
              <ShieldCheck class="size-5" />
            </div>
            <div>
              <CardTitle>{{ t('landing.sections.auth.title') }}</CardTitle>
              <CardDescription>Flux d’authentification simplifié et sécurisé.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p class="text-sm text-muted-foreground">{{ t('landing.sections.auth.text') }}</p>
        </CardContent>
      </Card>
      <Card class="transition-all hover:shadow-lg group">
        <CardHeader>
          <div class="flex items-center gap-3">
            <div class="rounded-full bg-primary/10 p-2 text-primary">
              <BarChart3 class="size-5" />
            </div>
            <div>
              <CardTitle>{{ t('landing.sections.visualization.title') }}</CardTitle>
              <CardDescription>Visualisations nettes, thèmes lisibles, détails pertinents.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p class="text-sm text-muted-foreground">{{ t('landing.sections.visualization.text') }}</p>
        </CardContent>
      </Card>
    </section>

    <!-- How it works / steps -->
    <section class="grid md:grid-cols-3 gap-6">
      <Card class="transition-all hover:shadow-lg">
        <CardHeader>
          <CardTitle>1. Importez vos données</CardTitle>
          <CardDescription>CSV propre, champs standards, lecture fiable.</CardDescription>
        </CardHeader>
        <CardContent>
          <p class="text-sm text-muted-foreground">Chargez un fichier CSV depuis l’interface de simulation puis
            définissez vos paramètres SMA.</p>
        </CardContent>
      </Card>
      <Card class="transition-all hover:shadow-lg">
        <CardHeader>
          <CardTitle>2. Lancez le backtest</CardTitle>
          <CardDescription>Calcul rapide, carte lisible, métriques clés.</CardDescription>
        </CardHeader>
        <CardContent>
          <p class="text-sm text-muted-foreground">Suivez l’équity curve et les KPI principaux avec un rendu inspiré de
            TradingView.</p>
        </CardContent>
      </Card>
      <Card class="transition-all hover:shadow-lg">
        <CardHeader>
          <CardTitle>3. Analysez et itérez</CardTitle>
          <CardDescription>Paramétrage fluide, comparaisons simples.</CardDescription>
        </CardHeader>
        <CardContent>
          <p class="text-sm text-muted-foreground">Ajustez vos paramètres et améliorez les performances de vos
            stratégies.</p>
        </CardContent>
      </Card>
    </section>

    <!-- Final CTA -->
    <section class="text-center">
      <div class="inline-flex items-center gap-2 rounded-xl border bg-secondary/40 px-6 py-4">
        <Zap class="size-5 text-primary" />
        <span class="text-sm text-muted-foreground">Prêt à démarrer ?</span>
        <Button size="sm" class="ml-2" @click="go('/simulate')">Lancer une simulation</Button>
      </div>
    </section>
  </main>
</template>

<style scoped>
/* Accent discret derrière le hero (placeholder sans image) */
section.relative::before {
  content: "";
  position: absolute;
  inset: -40% -10% auto -10%;
  height: 140%;
  border-radius: 50%;
  background: radial-gradient(1200px 400px at 50% 30%, rgba(16, 185, 129, 0.15), transparent 60%);
  pointer-events: none;
}
</style>