import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
type SupportedLocale = 'en' | 'fr'
const LOCALE_STORAGE_KEY = 'hptp-locale'
export function useLocale() {
  const i18n = useI18n()
  const localeRef = (i18n as unknown as { locale: { value: SupportedLocale } }).locale
  const getStoredLocale = (): SupportedLocale => {
    try {
      const stored = localStorage.getItem(LOCALE_STORAGE_KEY) as SupportedLocale
      return stored && ['en', 'fr'].includes(stored) ? stored : 'en'
    } catch {
      return 'en'
    }
  }
  const saveLocale = (newLocale: SupportedLocale) => {
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, newLocale)
    } catch (error) {
      console.warn('Failed to save locale to localStorage:', error)
    }
  }
  const selectedLocale = ref<SupportedLocale>(getStoredLocale())
  if (localeRef && localeRef.value !== selectedLocale.value) {
    localeRef.value = selectedLocale.value
  }
  watch(selectedLocale, (newLocale) => {
    if (localeRef) localeRef.value = newLocale
    saveLocale(newLocale)
  }, { immediate: false })
  const setLocale = (newLocale: SupportedLocale) => {
    selectedLocale.value = newLocale
  }
  return {
    selectedLocale,
    setLocale,
    supportedLocales: ['en', 'fr'] as const
  }
}