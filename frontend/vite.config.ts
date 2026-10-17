import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// W dockerze backend jest pod http://backend:8000, lokalnie pod localhost.
const backend = process.env.BACKEND_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/api': backend,
      '/media': backend,
    },
  },
  test: {
    environment: 'node',
  },
})
