declare module 'vue-i18n' {
  import type { App } from 'vue'

  export interface I18nOptions {
    legacy?: boolean
    globalInjection?: boolean
    locale?: string
    fallbackLocale?: string
    messages?: Record<string, any>
  }

  export function createI18n(options?: I18nOptions): any
  export function useI18n(): { t: (key: string, ...args: any[]) => string }
  export default {} as any
}