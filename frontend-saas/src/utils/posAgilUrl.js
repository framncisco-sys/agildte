/**
 * URL de entrada al PosAgil (Flask). Login, RequireAuth, botón navbar.
 *
 * - VITE_POSAGIL_PUBLIC_URL: gateway o URL directa (prioridad).
 * - Sin variable en desarrollo: mismo host, puerto VITE_POSAGIL_DEV_PORT o 5001 (Flask en host suele ser 5000: defínalo).
 * - Producción sin variable: /pos/ (Nginx debe enrutar al contenedor POS).
 */
export function getPosAgilEntryUrl() {
  const explicit = (import.meta.env.VITE_POSAGIL_PUBLIC_URL || '').trim()
  if (explicit) {
    return explicit.endsWith('/') ? explicit : `${explicit}/`
  }
  if (import.meta.env.DEV) {
    if (typeof window === 'undefined') return '/pos/'
    const { protocol, hostname } = window.location
    const port = String(import.meta.env.VITE_POSAGIL_DEV_PORT || '5001').trim() || '5001'
    return `${protocol}//${hostname}:${port}/`
  }
  return '/pos/'
}

/**
 * Entrada al PosAgil con sesión AgilDTE: el backend Flask valida el JWT en /auth/agildte.
 */
export function getPosAgilSsoUrl(accessToken) {
  const base = getPosAgilEntryUrl().replace(/\/+$/, '')
  const path = `${base}/auth/agildte`
  // Producción sin VITE_POSAGIL_PUBLIC_URL: base es ruta relativa (/pos). new URL('/x') falla sin base.
  const u =
    path.startsWith('http://') || path.startsWith('https://')
      ? new URL(path)
      : new URL(path, typeof window !== 'undefined' ? window.location.origin : 'http://localhost')
  if (accessToken && typeof accessToken === 'string') {
    u.searchParams.set('access_token', accessToken)
  }
  return u.toString()
}

/**
 * Cuando esta SPA muestra la ruta /pos/* (no debería en prod con Nginx).
 * No devolver /pos/ como destino para no recargar la misma app en bucle.
 */
export function getPosAgilRedirectLeavingSpa() {
  const explicit = (import.meta.env.VITE_POSAGIL_PUBLIC_URL || '').trim()
  if (explicit) {
    return explicit.endsWith('/') ? explicit : `${explicit}/`
  }
  if (import.meta.env.DEV && typeof window !== 'undefined') {
    const { protocol, hostname } = window.location
    const port = String(import.meta.env.VITE_POSAGIL_DEV_PORT || '5001').trim() || '5001'
    return `${protocol}//${hostname}:${port}/`
  }
  return null
}
