import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    // Optimisation pour CloudFront/S3
    rollupOptions: {
      output: {
        // Chunking strategy optimisée
        manualChunks: {
          // Vendor chunk pour les dépendances externes
          vendor: [
            'vue',
            'pinia',
            'vue-i18n'
          ],
          // UI components chunk
          ui: [
            'lucide-vue-next',
            'reka-ui',
            'embla-carousel-vue'
          ],
          // Charts chunk (plus lourd)
          charts: [
            'lightweight-charts',
            'echarts',
            'vue-echarts'
          ],
          // Utils chunk
          utils: [
            'axios',
            'decimal.js',
            'clsx',
            'tailwind-merge',
            'class-variance-authority'
          ]
        },
        // Nommage des chunks pour cache busting
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (!assetInfo.name) return 'assets/[name]-[hash][extname]'
          const info = assetInfo.name.split('.')
          const ext = info[info.length - 1]
          if (/\.(css)$/.test(assetInfo.name)) {
            return `assets/css/[name]-[hash].${ext}`
          }
          if (/\.(png|jpe?g|svg|gif|tiff|bmp|ico)$/i.test(assetInfo.name)) {
            return `assets/images/[name]-[hash].${ext}`
          }
          if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name)) {
            return `assets/fonts/[name]-[hash].${ext}`
          }
          return `assets/[name]-[hash].${ext}`
        }
      }
    },
    // Optimisations générales
    target: 'es2015',
    minify: 'terser',
    // Taille des chunks
    chunkSizeWarningLimit: 1000,
    // Source maps pour debugging en prod
    sourcemap: false
  },
  // Configuration pour CloudFront
  base: '/',
  // Optimisation des assets
  assetsInclude: ['**/*.svg', '**/*.png', '**/*.jpg', '**/*.jpeg', '**/*.gif']
})