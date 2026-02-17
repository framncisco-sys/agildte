import axios from 'axios'
import apiClient from './axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

/**
 * Login con username y password vía JWT.
 * POST /api/token/ -> access + refresh; luego GET /api/auth/me/ para user, role, empresa.
 */
export async function login(credentials) {
  const username = credentials.username ?? credentials.email
  const password = credentials.password
  if (!username || !password) {
    throw new Error('Usuario y contraseña son requeridos')
  }
  const { data: tokenData } = await axios.post(`${baseURL}/token/`, {
    username: username.trim(),
    password,
  })
  const access = tokenData.access
  const refresh = tokenData.refresh
  const me = await getMe(access)
  return {
    access,
    refresh,
    user: me.user,
    empresa_default: me.empresa_default,
    empresas: me.empresas,
  }
}

/**
 * Login legacy (custom backend): POST /api/auth/login/
 * Útil si se usa email o el backend devuelve user/empresas en una sola llamada.
 */
export async function loginLegacy(credentials) {
  const { data } = await axios.post(`${baseURL}/auth/login/`, credentials)
  return data
}

/**
 * Obtiene el usuario actual y empresa (requiere token).
 */
export async function getMe(accessToken) {
  const client = accessToken
    ? axios.create({
        baseURL,
        headers: { Authorization: `Bearer ${accessToken}`, Accept: 'application/json' },
      })
    : apiClient
  const { data } = await client.get('/auth/me/')
  return data
}

/**
 * Refresca el access token. POST /api/token/refresh/
 */
export async function refreshToken(refreshTokenValue) {
  const { data } = await axios.post(`${baseURL}/token/refresh/`, {
    refresh: refreshTokenValue,
  })
  return data
}

/**
 * Cambiar contraseña del usuario autenticado.
 */
export async function changePassword({ old_password, new_password }) {
  const { data } = await apiClient.post('/auth/change-password/', {
    old_password,
    new_password,
  })
  return data
}
