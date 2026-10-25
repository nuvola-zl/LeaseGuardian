import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8080', changeOrigin: true, rewrite: p => p.replace(/^\/api/, '') },
      '/py': { target: 'http://127.0.0.1:8000', changeOrigin: true, rewrite: p => p.replace(/^\/py/, '') },
    },
  },
})
