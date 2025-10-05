<script setup lang="ts">
import { useRouter } from '@/router'
import { Button } from '@/components/ui/button'

const { navigate } = useRouter()

function go(path: string) {
  navigate(path)
}
</script>

<template>
  <main class="container mx-auto px-6 py-10">
    <section class="text-center space-y-4">
      <h1 class="text-3xl font-bold">High-Performance Trading Platform</h1>
      <p class="text-muted-foreground max-w-2xl mx-auto">
        A modern Vue + TypeScript frontend integrated with a FastAPI backend. Run backtests with CSV upload,
        configure Simple Moving Averages (SMA), and visualize your equity curve, PnL, and drawdown with Lightweight Charts.
      </p>
      <div class="flex justify-center gap-3 mt-4">
        <Button size="lg" @click="go('/simulate')">Start Backtest</Button>
        <Button size="lg" variant="outline" @click="go('/login')">Login</Button>
        <Button size="lg" variant="outline" @click="go('/register')">Register</Button>
      </div>
    </section>

    <section class="grid md:grid-cols-3 gap-6 mt-12">
      <div class="p-4 border rounded">
        <h2 class="font-semibold mb-2">Backtest Simulation</h2>
        <p class="text-sm text-muted-foreground">
          Upload your CSV price data, set SMA parameters, and run a server-powered backtest. Results show equity curve, PnL,
          and max drawdown with robust error handling and responsive UI.
        </p>
      </div>
      <div class="p-4 border rounded">
        <h2 class="font-semibold mb-2">Authentication</h2>
        <p class="text-sm text-muted-foreground">
          Register and login to store tokens in Pinia. Requests use an authenticated API client. For testing,
          the simulate page can be accessed without login.
        </p>
      </div>
      <div class="p-4 border rounded">
        <h2 class="font-semibold mb-2">Visualization</h2>
        <p class="text-sm text-muted-foreground">
          Equity curve rendered with Lightweight Charts. Metrics for PnL and drawdown with clear, minimal design.
        </p>
      </div>
    </section>

    <section class="mt-10 text-center">
      <p class="text-sm text-muted-foreground">
        Prefer the previous dashboard? Visit the legacy homepage.
      </p>
      <Button class="mt-3" variant="outline" @click="go('/legacy')">Open Legacy Dashboard</Button>
    </section>
  </main>
</template>

<style scoped>
.text-muted-foreground { color: #6b7280; }
</style>