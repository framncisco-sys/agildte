import { createContext, useContext, useEffect } from 'react'
import { useAuthStore } from '../stores/useAuthStore'
import { useEmpresaStore } from '../stores/useEmpresaStore'
import { getMe, login as apiLogin, refreshToken } from '../api/auth'

const AuthContext = createContext(null)

/**
 * Proveedor de autenticación: user, token, role, login, logout.
 * Auto-login: al cargar, si hay token en localStorage, valida con /auth/me/ y restaura user/empresa.
 */
export function AuthProvider({ children }) {
  const user = useAuthStore((s) => s.user)
  const token = useAuthStore((s) => s.token)
  const refresh = useAuthStore((s) => s.refresh)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const loginStore = useAuthStore((s) => s.login)
  const logoutStore = useAuthStore((s) => s.logout)

  const role = user?.role ?? null

  /**
   * Sincroniza el perfil con GET /auth/me/ cuando cambia el token (o el refresh).
   * IMPORTANTE: no incluir setUser/setToken en dependencias — con zustand persist pueden
   * cambiar de referencia tras cada actualización y provocar un bucle infinito de getMe().
   */
  useEffect(() => {
    if (!token) return

    let cancelled = false

    const restoreSession = async () => {
      const { setUser, setToken, logout: logoutFromStore } = useAuthStore.getState()
      const refreshNow = useAuthStore.getState().refresh

      try {
        const me = await getMe()
        if (cancelled) return
        setUser(me.user)
        if (me.empresa_default) useEmpresaStore.getState().setEmpresa(me.empresa_default)
        if (me.empresas?.length) useEmpresaStore.getState().setEmpresas(me.empresas)
      } catch (err) {
        if (cancelled) return
        if (err.response?.status !== 401) return
        if (refreshNow) {
          try {
            const data = await refreshToken(refreshNow)
            setToken(data.access, data.refresh)
            const me = await getMe()
            if (cancelled) return
            setUser(me.user)
            if (me.empresa_default) useEmpresaStore.getState().setEmpresa(me.empresa_default)
            if (me.empresas?.length) useEmpresaStore.getState().setEmpresas(me.empresas)
          } catch {
            logoutFromStore()
            window.location.href = '/login'
          }
        } else {
          logoutFromStore()
          window.location.href = '/login'
        }
      }
    }

    restoreSession()
    return () => {
      cancelled = true
    }
    // Solo valores que deben disparar una nueva sincronización (no funciones del store).
  }, [token, refresh])

  const login = async (credentials) => {
    const data = await apiLogin(credentials)
    loginStore({
      user: data.user,
      access: data.access,
      refresh: data.refresh,
      empresa_default: data.empresa_default,
      empresas: data.empresas,
    })
    return data
  }

  const logout = () => {
    logoutStore()
    window.location.href = '/login'
  }

  const value = {
    user,
    token,
    role,
    isAuthenticated,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
