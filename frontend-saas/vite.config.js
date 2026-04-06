import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En Docker: VITE_API_URL=http://backend:8000
// En local sin Docker: http://localhost:8000
const backendUrl = process.env.VITE_API_URL || 'http://localhost:8000'

const apiProxy = {
  '/api': {
    target: backendUrl,
    changeOrigin: true,
  },
  '/media': {
    target: backendUrl,
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [react()],
  appType: 'spa',  // Necesario para que /login, /dashboard etc. sirvan index.html al refrescar
  server: {
    port: 3000,
    host: '0.0.0.0',   // necesario para que Docker exponga el puerto
    proxy: apiProxy,
  },
  // npm run preview no usa server.proxy por defecto; sin esto /api devuelve 404 en el puerto del preview.
  preview: {
    port: 3000,
    host: '0.0.0.0',
    proxy: apiProxy,
  },
})
