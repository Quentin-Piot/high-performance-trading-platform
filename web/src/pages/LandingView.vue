<script setup lang="ts">
import { useRouter } from '@/router'
import { Button } from '@/components/ui/button'
import { useI18n } from 'vue-i18n'

const { navigate } = useRouter()
const { t } = useI18n()

function go(path: string) {
  navigate(path)
}
</script>

<template>
  <main class="container mx-auto px-6 py-10">
    <section class="text-center space-y-4">
      <h1 class="text-3xl font-bold">{{ t('landing.title') }}</h1>
      <p class="text-muted-foreground max-w-2xl mx-auto">
        {{ t('landing.subtitle') }}
      </p>
      <div class="flex justify-center gap-3 mt-4">
        <Button size="lg" @click="go('/simulate')">{{ t('landing.cta.startBacktest') }}</Button>
        <Button size="lg" variant="outline" @click="go('/login')">{{ t('landing.cta.login') }}</Button>
        <Button size="lg" variant="outline" @click="go('/register')">{{ t('landing.cta.register') }}</Button>
      </div>
    </section>

    <section class="grid md:grid-cols-3 gap-6 mt-12">
      <div class="p-4 border rounded">
        <h2 class="font-semibold mb-2">{{ t('landing.sections.simulation.title') }}</h2>
        <p class="text-sm text-muted-foreground">{{ t('landing.sections.simulation.text') }}</p>
      </div>
      <div class="p-4 border rounded">
        <h2 class="font-semibold mb-2">{{ t('landing.sections.auth.title') }}</h2>
        <p class="text-sm text-muted-foreground">{{ t('landing.sections.auth.text') }}</p>
      </div>
      <div class="p-4 border rounded">
        <h2 class="font-semibold mb-2">{{ t('landing.sections.visualization.title') }}</h2>
        <p class="text-sm text-muted-foreground">{{ t('landing.sections.visualization.text') }}</p>
      </div>
    </section>

    <section class="mt-10 text-center">
      <p class="text-sm text-muted-foreground">{{ t('landing.legacy.text') }}</p>
      <Button class="mt-3" variant="outline" @click="go('/legacy')">{{ t('landing.legacy.open') }}</Button>
    </section>
  </main>
</template>

<style scoped>
.text-muted-foreground { color: #6b7280; }
</style>