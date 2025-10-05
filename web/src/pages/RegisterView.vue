<script setup lang="ts">
import AuthForm from '@/components/auth/AuthForm.vue'
import { useAuthStore } from '@/stores/authStore'
import { useRouter } from '@/router'

const auth = useAuthStore()
auth.rehydrate()
const { navigate } = useRouter()
if (auth.isAuthenticated) navigate('/simulate')
</script>

<template>
  <main class="container mx-auto p-6">
    <AuthForm mode="register" />
  </main>
</template>