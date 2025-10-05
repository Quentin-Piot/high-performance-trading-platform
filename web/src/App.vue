<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from '@/router'
import LoginView from '@/pages/LoginView.vue'
import RegisterView from '@/pages/RegisterView.vue'
import SimulateView from '@/pages/SimulateView.vue'
import Dashboard from '@/pages/Dashboard.vue'
import LandingView from '@/pages/LandingView.vue'

const { currentPath, navigate } = useRouter()
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
    <a href="/" @click.prevent="navigate('/')" class="text-sm hover:underline">Home</a>
    <a href="/simulate" @click.prevent="navigate('/simulate')" class="text-sm hover:underline">Simulate</a>
    <a href="/legacy" @click.prevent="navigate('/legacy')" class="text-sm hover:underline">Legacy</a>
    <span class="ml-auto flex items-center gap-3">
      <a href="/login" @click.prevent="navigate('/login')" class="text-sm hover:underline">Login</a>
      <a href="/register" @click.prevent="navigate('/register')" class="text-sm hover:underline">Register</a>
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
