<script setup lang="ts">
import { useRouter } from '@/router'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useI18n } from 'vue-i18n'
import { ref, watch } from 'vue'

const { navigate } = useRouter()
const i18n = useI18n()
const localeRef = (i18n as unknown as { locale: { value: 'en' | 'fr' } }).locale
const selectedLocale = ref<'en' | 'fr'>(localeRef?.value ?? 'en')
watch(selectedLocale, (val) => {
  if (localeRef) localeRef.value = val
})

function go(path: string) {
  navigate(path)
}
</script>

<template>
  <nav class="flex items-center justify-between py-3">
    <div class="flex items-center gap-2">
      <span class="text-xl font-semibold">HPTP</span>
      <span class="text-xs text-muted-foreground">High Performance Trading Platform</span>
    </div>
    <div class="flex items-center gap-2">
      <Button variant="ghost" size="sm" @click="go('/simulate')">Simuler</Button>
      <Button variant="ghost" size="sm" @click="go('/dashboard')">Dashboard</Button>
      <Button variant="outline" size="sm" @click="go('/login')">Login</Button>
      <Button size="sm" @click="go('/register')">Register</Button>
      <Select v-model="selectedLocale">
        <SelectTrigger size="sm">
          <SelectValue :placeholder="selectedLocale" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectItem value="en">English</SelectItem>
            <SelectItem value="fr">Français</SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  </nav>
</template>