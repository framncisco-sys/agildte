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
  const setToken = useAuthStore((s) => s.setToken)
  const setUser = useAuthStore((s) => s.setUser)

  const role = user?.role ?? null

  useEffect(() => {
    if (!token) return
    if (user?.id) return

    const restoreSession = async () => {
      try {
        const me = await getMe()
        setUser(me.user)
        if (me.empresa_default) useEmpresaStore.getState().setEmpresa(me.empresa_default)
        if (me.empresas?.length) useEmpresaStore.getState().setEmpresas(me.empresas)
      } catch (err) {
        if (err.response?.status !== 401) return
        if (refresh) {
          try {
            const data = await refreshToken(refresh)
            setToken(data.access, data.refresh)
            const me = await getMe()
            setUser(me.user)
            if (me.empresa_default) useEmpresaStore.getState().setEmpresa(me.empresa_default)
            if (me.empresas?.length) useEmpresaStore.getState().setEmpresas(me.empresas)
          } catch {
            logoutStore()
            window.location.href = '/login'
          }
        } else {
          logoutStore()
          window.location.href = '/login'
        }
      }
    }

    restoreSession()
  }, [token, refresh, user?.id, setUser, logoutStore])

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
