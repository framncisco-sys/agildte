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

/** Endpoint SSO PosAgil (POST); el JWT no va en la URL. */
export function getPosAgilAuthEndpointUrl() {
  const base = getPosAgilEntryUrl().replace(/\/+$/, '')
  const path = `${base}/auth/agildte`
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  if (typeof window !== 'undefined') {
    return new URL(path, window.location.origin).toString()
  }
  return path
}

/**
 * Abre PosAgil con sesión AgilDTE vía POST (token en cuerpo, no en query ni en HTML).
 */
export function openPosAgilSso(accessToken) {
  if (!accessToken || typeof accessToken !== 'string') return
  const form = document.createElement('form')
  form.method = 'POST'
  form.action = getPosAgilAuthEndpointUrl()
  form.style.display = 'none'
  const input = document.createElement('input')
  input.type = 'hidden'
  input.name = 'access_token'
  input.value = accessToken
  form.appendChild(input)
  document.body.appendChild(form)
  form.submit()
}

/**
 * @deprecated Use openPosAgilSso(accessToken). Ya no incluye el JWT en la URL.
 */
export function getPosAgilSsoUrl(accessToken) {
  void accessToken
  return getPosAgilAuthEndpointUrl()
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
