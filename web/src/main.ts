import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'

const pinia = createPinia()
const app = createApp(App)

app.use(pinia)
// Rehydrate auth token on app start
import { useAuthStore } from '@/stores/authStore'
const auth = useAuthStore()
auth.rehydrate()
app.mount('#app')