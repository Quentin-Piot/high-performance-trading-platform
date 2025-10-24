<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/authStore'
import { useRouter } from '@/router'
import { useI18n } from 'vue-i18n'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { CheckCircle, XCircle, Eye, EyeOff } from 'lucide-vue-next'
import { PasswordValidationService } from '@/services/passwordValidationService'

type Mode = 'login' | 'register'

const props = defineProps<{ mode: Mode }>()

const { t } = useI18n()
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref<string | null>(null)
const loading = ref(false)

// Validation du mot de passe en temps réel
const passwordValidation = ref(PasswordValidationService.validatePassword(''))

// Computed properties pour faciliter l'accès aux propriétés de validation
const passwordRequirements = computed(() => {
  const rules = passwordValidation.value.rules
  return {
    minLength: rules.find(r => r.id === 'minLength')?.isValid || false,
    hasUppercase: rules.find(r => r.id === 'hasUppercase')?.isValid || false,
    hasLowercase: rules.find(r => r.id === 'hasLowercase')?.isValid || false,
    hasNumber: rules.find(r => r.id === 'hasNumber')?.isValid || false,
    hasSymbol: rules.find(r => r.id === 'hasSymbol')?.isValid || false
  }
})

const passwordStrength = computed(() => {
  const score = passwordValidation.value.score
  return {
    level: PasswordValidationService.getPasswordStrength(score),
    color: PasswordValidationService.getPasswordStrengthColor(score),
    bgColor: PasswordValidationService.getPasswordStrengthBgColor(score),
    score
  }
})

// Validation de l'email
const isEmailValid = computed(() => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email.value)
})

// Validation globale
const valid = computed(() => {
  if (props.mode === 'login') {
    return isEmailValid.value && password.value.length >= 6
  } else {
    return isEmailValid.value && passwordValidation.value.isValid
  }
})

const auth = useAuthStore()
const { navigate } = useRouter()

// Watcher pour la validation du mot de passe en temps réel
watch(password, (newPassword) => {
  if (props.mode === 'register') {
    passwordValidation.value = PasswordValidationService.validatePassword(newPassword)
  }
}, { immediate: true })

async function onSubmit() {
  error.value = null
  if (!valid.value) {
    error.value = props.mode === 'login' 
      ? t('auth.errors.invalidCredentials', 'Invalid email or password')
      : t('auth.errors.invalidPassword', 'Please meet all password requirements')
    return
  }
  
  loading.value = true
  try {
    if (props.mode === 'login') {
      await auth.login({ email: email.value, password: password.value })
    } else {
      await auth.register({ email: email.value, password: password.value })
    }
    navigate('/simulate')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : t('auth.errors.authFailed', 'Authentication failed')
  } finally {
    loading.value = false
  }
}

async function onGoogleLogin() {
  error.value = null
  try {
    await auth.loginWithGoogle('/simulate')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : t('auth.errors.googleAuthFailed', 'Google authentication failed')
  }
}

function togglePasswordVisibility() {
  showPassword.value = !showPassword.value
}
</script>
<template>
  <div class="max-w-sm w-full mx-auto p-4 rounded-md border">
    <h2 class="text-lg font-semibold mb-3">{{ props.mode === 'login' ? t('auth.titles.login', 'Login') : t('auth.titles.register', 'Register') }}</h2>
    <div class="mb-4">
      <Button 
        variant="outline" 
        class="w-full h-10 flex items-center justify-center gap-2" 
        :disabled="loading"
        @click="onGoogleLogin"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        {{ t('auth.buttons.googleLogin', 'Continue with Google') }}
      </Button>
    </div>
    <div class="relative mb-4">
      <div class="absolute inset-0 flex items-center">
        <span class="w-full border-t" />
      </div>
      <div class="relative flex justify-center text-xs uppercase">
        <span class="bg-background px-2 text-muted-foreground">{{ t('auth.labels.orContinueWithEmail', 'Or continue with email') }}</span>
      </div>
    </div>
    <div class="space-y-3">
      <div>
        <Label class="mb-1">{{ t('auth.labels.email', 'Email') }}</Label>
        <Input v-model="email" type="email" :placeholder="t('auth.placeholders.email', 'you@example.com')" />
      </div>
      <div>
        <Label class="mb-1">{{ t('auth.labels.password', 'Password') }}</Label>
        <div class="relative">
          <Input v-model="password" :type="showPassword ? 'text' : 'password'" :placeholder="t('auth.placeholders.password', 'Enter your password')" />
          <button
            type="button"
            @click="togglePasswordVisibility"
            class="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
          >
            <Eye v-if="!showPassword" class="h-4 w-4" />
            <EyeOff v-else class="h-4 w-4" />
          </button>
        </div>
        
        <!-- Validation du mot de passe pour l'inscription -->
        <div v-if="props.mode === 'register' && password.length > 0" class="mt-2 space-y-1">
          <div class="text-xs text-gray-600 mb-2">{{ t('auth.password.requirements', 'Password requirements:') }}</div>
          
          <div class="space-y-1">
             <div class="flex items-center text-xs">
               <CheckCircle v-if="passwordRequirements.minLength" class="h-3 w-3 text-green-500 mr-2" />
               <XCircle v-else class="h-3 w-3 text-red-500 mr-2" />
               <span :class="passwordRequirements.minLength ? 'text-green-600' : 'text-red-600'">
                 {{ t('auth.password.minLength', 'At least 8 characters') }}
               </span>
             </div>
             
             <div class="flex items-center text-xs">
               <CheckCircle v-if="passwordRequirements.hasUppercase" class="h-3 w-3 text-green-500 mr-2" />
               <XCircle v-else class="h-3 w-3 text-red-500 mr-2" />
               <span :class="passwordRequirements.hasUppercase ? 'text-green-600' : 'text-red-600'">
                 {{ t('auth.password.hasUppercase', 'One uppercase letter') }}
               </span>
             </div>
             
             <div class="flex items-center text-xs">
               <CheckCircle v-if="passwordRequirements.hasLowercase" class="h-3 w-3 text-green-500 mr-2" />
               <XCircle v-else class="h-3 w-3 text-red-500 mr-2" />
               <span :class="passwordRequirements.hasLowercase ? 'text-green-600' : 'text-red-600'">
                 {{ t('auth.password.hasLowercase', 'One lowercase letter') }}
               </span>
             </div>
             
             <div class="flex items-center text-xs">
               <CheckCircle v-if="passwordRequirements.hasNumber" class="h-3 w-3 text-green-500 mr-2" />
               <XCircle v-else class="h-3 w-3 text-red-500 mr-2" />
               <span :class="passwordRequirements.hasNumber ? 'text-green-600' : 'text-red-600'">
                 {{ t('auth.password.hasNumber', 'One number') }}
               </span>
             </div>
             
             <div class="flex items-center text-xs">
               <CheckCircle v-if="passwordRequirements.hasSymbol" class="h-3 w-3 text-green-500 mr-2" />
               <XCircle v-else class="h-3 w-3 text-red-500 mr-2" />
               <span :class="passwordRequirements.hasSymbol ? 'text-green-600' : 'text-red-600'">
                 {{ t('auth.password.hasSymbol', 'One symbol') }}
               </span>
             </div>
           </div>
           
           <!-- Indicateur de force du mot de passe -->
           <div v-if="password.length > 0" class="mt-2">
             <div class="text-xs text-gray-600 mb-1">{{ t('auth.password.strength', 'Password strength:') }}</div>
             <div class="flex items-center space-x-2">
               <div class="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                 <div 
                   class="h-full transition-all duration-300"
                   :class="passwordStrength.bgColor"
                   :style="{ width: `${(passwordStrength.score / 100) * 100}%` }"
                 ></div>
               </div>
               <span class="text-xs" :class="passwordStrength.color">
                 {{ t(`auth.password.strength.${passwordStrength.level}`, passwordStrength.level) }}
               </span>
             </div>
           </div>
        </div>
        
        <p v-else class="text-xs text-muted-foreground mt-1">{{ t('auth.password.minCharacters', 'Minimum 6 characters.') }}</p>
      </div>
      <Button :disabled="loading || !valid" class="w-full h-10" @click="onSubmit">
        {{ loading ? t('auth.buttons.loading', '...') : (props.mode === 'login' ? t('auth.buttons.login', 'Login') : t('auth.buttons.register', 'Register')) }}
      </Button>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
    </div>
  </div>
  <div class="text-center mt-3">
    <a v-if="props.mode==='login'" href="/register" class="text-sm text-muted-foreground hover:underline">{{ t('auth.links.createAccount', 'Create an account') }}</a>
    <a v-else href="/login" class="text-sm text-muted-foreground hover:underline">{{ t('auth.links.alreadyHaveAccount', 'Already have an account?') }}</a>
  </div>
</template>