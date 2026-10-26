import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // 1) chat 前端接口：保留 /api，不能 rewrite
      '/api/chat': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },

      // 2) 其他 Java 接口：/api 只是前端代理前缀，要剥掉
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        rewrite: p => p.replace(/^\/api/, ''),
      },

      // 3) Python 编排层
      '/py': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: p => p.replace(/^\/py/, ''),
      },
    },
  },
})