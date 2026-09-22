import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Backend vers lequel relayer /api en développement (même origine => cookie de session simple)
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://localhost:8001'

  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      watch: {
        usePolling: true
      },
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: false,
          xfwd: true
        }
      }
    },
    build: {
      sourcemap: false,
      rollupOptions: {
        output: {
          // Bibliothèques volumineuses dans des fichiers séparés (mis en cache entre deux versions)
          manualChunks: {
            timeline: ['vis-timeline/standalone'],
            charts: ['recharts'],
            vendor: ['react', 'react-dom', 'react-router-dom', '@tanstack/react-query', '@headlessui/react', 'axios', 'date-fns']
          }
        }
      },
      chunkSizeWarningLimit: 900
    }
  }
})
