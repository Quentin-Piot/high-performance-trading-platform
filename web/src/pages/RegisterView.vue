<script setup lang="ts">
import { onMounted } from 'vue'
import AuthForm from '@/components/auth/AuthForm.vue'
import { useAuthStore } from '@/stores/authStore'
import { useRouter } from '@/router'

const auth = useAuthStore()
const { navigate } = useRouter()

onMounted(async () => {
  // Check for Google OAuth callback
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.has('auth') || urlParams.has('error')) {
    const success = await auth.handleGoogleCallback()
    if (success) {
      navigate('/simulate')
      return
    }
  }
  
  // Rehydrate auth state
  auth.rehydrate()
  if (auth.isAuthenticated) navigate('/simulate')
})
</script>

<template>
  <main class="container mx-auto p-6">
    <AuthForm mode="register" />
  </main>
</template>