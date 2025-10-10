import { defineStore } from 'pinia'

export type ErrorEvent = {
  id: string
  time: number
  code: string // i18n key-like code: e.g., 'error.invalid_csv'
  message?: string // optional raw message for debugging
  context?: Record<string, unknown>
}

export const useErrorStore = defineStore('errors', {
  state: () => ({
    events: [] as ErrorEvent[],
  }),
  getters: {
    last: (s) => s.events[0] || null,
    count: (s) => s.events.length,
  },
  actions: {
    log(code: string, message?: string, context?: Record<string, unknown>) {
      const evt: ErrorEvent = {
        id: crypto.randomUUID(),
        time: Date.now(),
        code,
        message,
        context,
      }
      this.events.unshift(evt)
      // Optional: send to analytics endpoint later
      // console.debug('[error]', evt)
    },
    clear() {
      this.events = []
    },
  },
})