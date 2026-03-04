import { useState, useEffect } from 'react'
import { X, Search, Loader2 } from 'lucide-react'
import { getActividades } from '../../../api/actividades'

/**
 * Modal para buscar y seleccionar actividad económica desde el backend.
 * Solo usa datos del backend (tabla ActividadEconomica) - sin fallback al frontend.
 * Si Hacienda agrega actividades, actualizar la tabla con cargar_actividades.
 */
export function ModalBuscadorActividad({ isOpen, onClose, onSelect }) {
  const [actividades, setActividades] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!isOpen) {
      setActividades([])
      return
    }
    setLoading(true)
    getActividades({ search: search.trim() || undefined, limit: 50 })
      .then((data) => {
        const list = data.results || data || []
        setActividades(Array.isArray(list) ? list : [])
      })
      .catch(() => setActividades([]))
      .finally(() => setLoading(false))
  }, [isOpen, search])

  const handleSelect = (act) => {
    const codigo = act.codigo ?? ''
    const descripcion = act.descripcion ?? ''
    onSelect({ codigo, descripcion })
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50" aria-modal="true">
      <div className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-2xl max-h-[90vh] sm:max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 shrink-0">
          <h2 className="text-lg font-semibold text-gray-800">Buscar actividad económica</h2>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-full text-gray-500 hover:bg-gray-100 touch-manipulation"
            aria-label="Cerrar"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-3 border-b border-gray-100 shrink-0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por código o descripción..."
              className="w-full pl-10 pr-4 py-2.5 sm:py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-base sm:text-sm"
              autoFocus
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto min-h-0 p-3 sm:p-4">
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
          ) : actividades.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              {search.trim() ? 'No se encontraron actividades. Use otro término o actualice la tabla con cargar_actividades.' : 'Escriba para buscar actividades económicas.'}
            </p>
          ) : (
            <>
              <div className="sm:hidden space-y-2">
                {actividades.map((act) => (
                  <button
                    key={act.codigo}
                    type="button"
                    onClick={() => handleSelect(act)}
                    className="w-full text-left flex flex-col gap-1 p-4 rounded-xl border border-gray-200 bg-gray-50/50 hover:bg-blue-50/50 hover:border-blue-200 transition-colors touch-manipulation"
                  >
                    <span className="font-medium text-gray-800">{act.codigo}</span>
                    <span className="text-sm text-gray-600">{act.descripcion}</span>
                  </button>
                ))}
              </div>
              <div className="hidden sm:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="px-3 py-2 text-left font-semibold text-gray-700 w-24">Código</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-700">Descripción</th>
                      <th className="px-3 py-2 w-20"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {actividades.map((act) => (
                      <tr
                        key={act.codigo}
                        className="border-b border-gray-100 hover:bg-blue-50/30"
                      >
                        <td className="px-3 py-2 font-medium text-gray-800">{act.codigo}</td>
                        <td className="px-3 py-2 text-gray-700">{act.descripcion}</td>
                        <td className="px-3 py-2">
                          <button
                            type="button"
                            onClick={() => handleSelect(act)}
                            className="px-3 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700"
                          >
                            Seleccionar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
