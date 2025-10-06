<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from '@/router'
import { useI18n } from 'vue-i18n'
import LoginView from '@/pages/LoginView.vue'
import RegisterView from '@/pages/RegisterView.vue'
import SimulateView from '@/pages/SimulateView.vue'
import Dashboard from '@/pages/Dashboard.vue'
import LandingView from '@/pages/LandingView.vue'

const { currentPath, navigate } = useRouter()
const i18n = useI18n()
const { t } = i18n
const selectedLocale = ref<'en' | 'fr'>('en')
watch(selectedLocale, (val) => {
  // mise à jour de la locale globale
  // @ts-ignore
  if (i18n && (i18n as any).locale) (i18n as any).locale.value = val
})
const View = computed(() => {
  switch (currentPath.value) {
    case '/': return LandingView
    case '/legacy': return Dashboard
    case '/login': return LoginView
    case '/register': return RegisterView
    case '/simulate': return SimulateView
    default: return LandingView
  }
})
</script>

<template>
  <nav class="container mx-auto p-4 flex items-center gap-4">
    <a href="/" @click.prevent="navigate('/')" class="text-sm hover:underline">{{ t('nav.home') }}</a>
    <a href="/simulate" @click.prevent="navigate('/simulate')" class="text-sm hover:underline">{{ t('nav.simulate') }}</a>
    <a href="/legacy" @click.prevent="navigate('/legacy')" class="text-sm hover:underline">{{ t('nav.legacy') }}</a>
    <span class="ml-auto flex items-center gap-3">
      <a href="/login" @click.prevent="navigate('/login')" class="text-sm hover:underline">{{ t('nav.login') }}</a>
      <a href="/register" @click.prevent="navigate('/register')" class="text-sm hover:underline">{{ t('nav.register') }}</a>
      <select v-model="selectedLocale" class="text-sm border rounded p-1">
        <option value="en">EN</option>
        <option value="fr">FR</option>
      </select>
    </span>
  </nav>
  <component :is="View" />
</template>

<style scoped>
.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.vue:hover {
  filter: drop-shadow(0 0 2em #42b883aa);
}
</style>
