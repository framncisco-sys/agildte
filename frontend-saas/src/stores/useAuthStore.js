import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { useEmpresaStore } from './useEmpresaStore'

/**
 * Store de autenticación para SaaS.
 * login(data) recibe la respuesta del backend: { user, access, empresa_default }
 * Si hay empresa_default, la asigna automáticamente en useEmpresaStore.
 */
export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refresh: null,
      isAuthenticated: false,

      login: (data) => {
        const { user, access, refresh, empresa_default, empresas } = data
        set({
          user: user || data.user,
          token: access || data.access,
          refresh: refresh || data.refresh,
          isAuthenticated: true,
        })
        if (empresas?.length) {
          useEmpresaStore.getState().setEmpresas(empresas)
        }
        if (empresa_default) {
          useEmpresaStore.getState().setEmpresa(empresa_default)
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          refresh: null,
          isAuthenticated: false,
        })
        useEmpresaStore.getState().clearEmpresa()
      },

      setUser: (user) =>
        set((state) => ({
          ...state,
          user: { ...state.user, ...user },
        })),

      setToken: (access, refresh) =>
        set((state) => ({
          ...state,
          token: access ?? state.token,
          refresh: refresh ?? state.refresh,
        })),
    }),
    { name: 'auth-storage' }
  )
)
