import { useState, useEffect } from 'react'
import { X, Search, Plus, Loader2 } from 'lucide-react'
import { getItems } from '../../../api/items'

/**
 * Modal que muestra el catálogo de ítems de la empresa.
 * Buscador interno; al hacer clic en '+' de una fila, se llama onSelect(item) y se cierra.
 * Responsivo: tabla en escritorio, cards en móvil.
 */
export function ModalCatalogoItems({ isOpen, onClose, onSelect, empresaId }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!isOpen || !empresaId) {
      setItems([])
      return
    }
    setLoading(true)
    getItems({ empresa_id: empresaId, q: search.trim() || undefined })
      .then((data) => setItems(Array.isArray(data) ? data : []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [isOpen, empresaId, search])

  const handleSelect = (item) => {
    onSelect({
      descripcion: item.descripcion ?? '',
      precio_unitario: Number(item.precio_unitario) ?? 0,
    })
    onClose()
  }

  const formatPrecio = (v) => {
    const n = Number(v)
    return isNaN(n) ? '$0.00' : `$${n.toFixed(2)}`
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50" aria-modal="true">
      <div className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-2xl max-h-[90vh] sm:max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 shrink-0">
          <h2 className="text-lg font-semibold text-gray-800">Catálogo de ítems</h2>
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
              placeholder="Buscar por nombre o código..."
              className="w-full pl-10 pr-4 py-2.5 sm:py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-base sm:text-sm"
              autoFocus
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto min-h-0 p-3 sm:p-4">
          {!empresaId ? (
            <p className="text-gray-500 text-center py-8">Seleccione una empresa.</p>
          ) : loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
          ) : items.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No hay ítems. Agregue productos en Administración de Ítems.
            </p>
          ) : (
            <>
              {/* Móvil: cards grandes y botón + fácil de tocar */}
              <div className="sm:hidden space-y-2">
                {items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 bg-gray-50/50"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 truncate">{item.descripcion}</p>
                      <p className="text-sm text-gray-500">
                        {item.codigo ? `Cód: ${item.codigo}` : 'Sin código'} · {formatPrecio(item.precio_unitario)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleSelect(item)}
                      className="shrink-0 p-3 rounded-xl bg-green-600 text-white hover:bg-green-700 touch-manipulation active:scale-95 transition-transform"
                      aria-label="Agregar a la fila"
                      title="Agregar"
                    >
                      <Plus size={24} />
                    </button>
                  </div>
                ))}
              </div>
              {/* Escritorio: tabla */}
              <div className="hidden sm:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="px-3 py-2 text-left font-semibold text-gray-700">Código</th>
                      <th className="px-3 py-2 text-left font-semibold text-gray-700">Nombre</th>
                      <th className="px-3 py-2 text-right font-semibold text-gray-700">Precio Unitario</th>
                      <th className="px-3 py-2 w-14"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <tr
                        key={item.id}
                        className="border-b border-gray-100 hover:bg-blue-50/30"
                      >
                        <td className="px-3 py-2 text-gray-600">{item.codigo || '—'}</td>
                        <td className="px-3 py-2 font-medium text-gray-800">{item.descripcion}</td>
                        <td className="px-3 py-2 text-right font-medium text-gray-800">{formatPrecio(item.precio_unitario)}</td>
                        <td className="px-3 py-2">
                          <button
                            type="button"
                            onClick={() => handleSelect(item)}
                            className="p-2 rounded-lg bg-green-600 text-white hover:bg-green-700"
                            aria-label="Agregar"
                            title="Agregar a la fila"
                          >
                            <Plus size={18} />
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
