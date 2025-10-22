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
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Authentication failed'
  } finally {
    loading.value = false
  }
}

async function onGoogleLogin() {
  error.value = null
  try {
    await auth.loginWithGoogle('/simulate')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Google authentication failed'
  }
}
</script>

<template>
  <div class="max-w-sm w-full mx-auto p-4 rounded-md border">
    <h2 class="text-lg font-semibold mb-3">{{ props.mode === 'login' ? 'Login' : 'Register' }}</h2>
    
    <!-- Google OAuth Button -->
    <div class="mb-4">
      <Button 
        variant="outline" 
        class="w-full h-10 flex items-center justify-center gap-2" 
        @click="onGoogleLogin"
        :disabled="loading"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        Continue with Google
      </Button>
    </div>

    <!-- Divider -->
    <div class="relative mb-4">
      <div class="absolute inset-0 flex items-center">
        <span class="w-full border-t" />
      </div>
      <div class="relative flex justify-center text-xs uppercase">
        <span class="bg-background px-2 text-muted-foreground">Or continue with email</span>
      </div>
    </div>

    <!-- Email/Password Form -->
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
      <Button :disabled="loading || !valid" class="w-full h-10" @click="onSubmit">
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