import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('element-plus')) {
            if (id.includes('@element-plus/icons-vue')) {
            return 'icons'
          }
          if (id.includes('element-plus/es/components/')) {
            return 'components'
          }
          return 'element-plus'
          }
          if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) {
          return 'vue-vendor'
          }
          if (id.includes('axios')) {
          return 'axios'
          }
          if (id.includes('echarts') || id.includes('zrender')) {
          return 'echarts-vendor'
          }
          if (id.includes('dayjs')) {
          return 'dayjs'
          }
          if (id.includes('lodash')) {
          return 'lodash'
          }
          if (id.includes('vue-i18n')) {
          return 'vue-i18n'
          }
        }
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    testTimeout: 10000,
    hookTimeout: 10000,
    exclude: [
      'e2e/**',
      'node_modules/**',
      'dist/**',
      'src/components/common/__tests__/**',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{ts,vue}'],
      exclude: ['src/**/*.d.ts', 'src/main.ts', 'src/auto-imports.d.ts', 'src/components.d.ts'],
      thresholds: {
        lines: 60,
        functions: 60,
        branches: 50,
        statements: 60,
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
