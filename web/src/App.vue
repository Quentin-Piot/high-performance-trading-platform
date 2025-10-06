<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from '@/router'
import { useI18n } from 'vue-i18n'
import LoginView from '@/pages/LoginView.vue'
import RegisterView from '@/pages/RegisterView.vue'
import SimulateView from '@/pages/SimulateView.vue'
import Dashboard from '@/pages/Dashboard.vue'
import LandingView from '@/pages/LandingView.vue'
const { currentPath } = useRouter()
const i18n = useI18n()
const localeRef = (i18n as unknown as { locale: { value: 'en' | 'fr' } }).locale
const selectedLocale = ref<'en' | 'fr'>('en')
watch(selectedLocale, (val) => {
  if (localeRef) localeRef.value = val
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
