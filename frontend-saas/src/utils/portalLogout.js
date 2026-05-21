/**
 * Cierre de sesión AgilDTE al volver desde PosAgil (/logout?logout=1).
 * Debe ejecutarse antes de que React rehidrate el JWT desde localStorage.
 */
export function applyPortalLogoutFromUrl() {
  if (typeof window === 'undefined') return false
  const params = new URLSearchParams(window.location.search)
  if (params.get('logout') !== '1') return false

  try {
    localStorage.removeItem('auth-storage')
    localStorage.removeItem('empresa-storage')
  } catch {
    /* ignore */
  }

  if (window.location.pathname !== '/login') {
    window.location.replace('/login')
    return true
  }

  params.delete('logout')
  const qs = params.toString()
  window.history.replaceState(null, '', qs ? `/login?${qs}` : '/login')
  return true
}
