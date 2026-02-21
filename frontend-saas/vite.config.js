import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En Docker: VITE_API_URL=http://backend:8000
// En local sin Docker: http://localhost:8000
const backendUrl = process.env.VITE_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',   // necesario para que Docker exponga el puerto
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
      },
      '/media': {
        target: backendUrl,
        changeOrigin: true,
      },
    },
  },
})
