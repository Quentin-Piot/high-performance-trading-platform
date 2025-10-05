<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/authStore'
import { useRouter } from '@/router'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

type Mode = 'login' | 'register'
const props = defineProps<{ mode: Mode }>()

const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const loading = ref(false)
const valid = computed(() => email.value.includes('@') && password.value.length >= 6)

const auth = useAuthStore()
const { navigate } = useRouter()

async function onSubmit() {
  error.value = null
  if (!valid.value) {
    error.value = 'Invalid email or password'
    return
  }
  loading.value = true
  try {
    if (props.mode === 'login') await auth.login({ email: email.value, password: password.value })
    else await auth.register({ email: email.value, password: password.value })
    navigate('/simulate')
  } catch (e: any) {
    error.value = e?.message || 'Authentication failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-sm w-full mx-auto p-4 rounded-md border">
    <h2 class="text-lg font-semibold mb-3">{{ props.mode === 'login' ? 'Login' : 'Register' }}</h2>
    <div class="space-y-3">
      <div>
        <Label class="mb-1">Email</Label>
        <Input v-model="email" type="email" placeholder="you@example.com" />
      </div>
      <div>
        <Label class="mb-1">Password</Label>
        <Input v-model="password" type="password" />
        <p class="text-xs text-muted-foreground mt-1">Minimum 6 characters.</p>
      </div>
      <Button :disabled="loading || !valid" @click="onSubmit" class="w-full h-10">
        {{ loading ? '...' : (props.mode === 'login' ? 'Login' : 'Register') }}
      </Button>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
    </div>
  </div>
  <div class="text-center mt-3">
    <a v-if="props.mode==='login'" href="/register" class="text-sm text-muted-foreground hover:underline">Create an account</a>
    <a v-else href="/login" class="text-sm text-muted-foreground hover:underline">Already have an account?</a>
  </div>
  </template>