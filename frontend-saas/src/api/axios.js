import axios from 'axios'
import { useAuthStore } from '../stores/useAuthStore'
import { useEmpresaStore } from '../stores/useEmpresaStore'

/**
 * Si VITE_API_BASE_URL es http://backend:8000 sin /api, las peticiones iban a /ventas/...
 * y Django solo tiene rutas bajo /api/ → 404 {"detail":"No encontrado."}.
 */
export function getApiBaseUrl() {
  const v = import.meta.env.VITE_API_BASE_URL
  if (v == null || v === '' || v === '/api') return '/api'
  const base = String(v).trim().replace(/\/+$/, '')
  if (base.endsWith('/api')) return base
  return `${base}/api`
}

const baseURL = getApiBaseUrl()

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
  timeout: 30000,
})

// Interceptor de request: inyectar Token y CompanyID
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    const empresaId = useEmpresaStore.getState().empresaId

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    if (empresaId) {
      config.headers['X-Company-ID'] = empresaId
    }

    return config
  },
  (error) => Promise.reject(error)
)

// Interceptor de response: 401 → login (excepto descargas blob/ZIP: no cerrar sesión entera por un fallo puntual)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const cfg = error.config
      const url = typeof cfg?.url === 'string' ? cfg.url : ''
      const esDescargaBlob =
        cfg?.responseType === 'blob' ||
        cfg?.responseType === 'arraybuffer' ||
        url.includes('descarga-zip') ||
        url.includes('generar-pdf') ||
        url.includes('generar-dte') ||
        url.includes('informe-cf-diario')
      if (!esDescargaBlob) {
        useAuthStore.getState().logout()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
