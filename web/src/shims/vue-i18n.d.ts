declare module 'vue-i18n' {
  export interface I18nOptions {
    legacy?: boolean
    globalInjection?: boolean
    locale?: string
    fallbackLocale?: string
    messages?: Record<string, unknown>
  }

  export function createI18n(options?: I18nOptions): unknown
  export function useI18n(): { t: (key: string, ...args: unknown[]) => string }
  const _default: unknown
  export default _default
}