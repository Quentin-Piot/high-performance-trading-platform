import { createApp } from "vue";
import { createPinia } from "pinia";
import "./style.css";
import App from "./App.vue";
import { createI18n } from "vue-i18n";
import type { Plugin } from "vue";
import en from "./locales/en.json";
import fr from "./locales/fr.json";

const pinia = createPinia();
const app = createApp(App);

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: "en",
  fallbackLocale: "en",
  messages: { en, fr },
});

app.use(pinia);
app.use(i18n as unknown as Plugin);

import { useAuthStore } from "@/stores/authStore";
const auth = useAuthStore();
auth.rehydrate();
app.mount("#app");
