import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * Store para selección multi-empresa.
 * Se usa en el header X-Company-ID de las peticiones API.
 */
export const useEmpresaStore = create(
  persist(
    (set) => ({
      empresaId: null,
      empresaNombre: null,
      empresas: [],

      setEmpresaId: (empresaId) =>
        set({ empresaId }),

      setEmpresa: (empresa) =>
        set((state) => {
          const list = state.empresas
          const nuevasEmpresas =
            empresa && !list.some((e) => e.id === empresa.id)
              ? [...list, { id: empresa.id, nombre: empresa.nombre }]
              : list
          return {
            empresaId: empresa?.id ?? null,
            empresaNombre: empresa?.nombre ?? null,
            empresas: nuevasEmpresas,
          }
        }),

      setEmpresas: (empresas) =>
        set({ empresas }),

      selectEmpresa: (empresaId) => {
        const empresas = useEmpresaStore.getState().empresas
        const e = empresas.find((x) => x.id == empresaId)
        set({
          empresaId: empresaId ?? null,
          empresaNombre: e?.nombre ?? null,
        })
      },

      clearEmpresa: () =>
        set({ empresaId: null, empresaNombre: null }),
    }),
    { name: 'empresa-storage' }
  )
)
