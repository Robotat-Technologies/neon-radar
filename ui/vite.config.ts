import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// The API (contract C3) runs on 127.0.0.1:8000 (`neonradar api serve`); the dev and preview
// servers forward /api to it, so the browser only ever talks to its own origin.
const apiProxy = {
  '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
  // Cytoscape and fcose make one chunk of about 560 kB, loaded only by the graph pages.
  build: { chunkSizeWarningLimit: 600 },
})
