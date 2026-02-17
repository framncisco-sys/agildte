import axios from 'axios'
import { useAuthStore } from '../stores/useAuthStore'
import { useEmpresaStore } from '../stores/useEmpresaStore'

// En dev usa '/api' (proxy Vite) para evitar CORS. En prod usa VITE_API_BASE_URL.
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

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

// Interceptor de response: manejar 401 y refresco
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
