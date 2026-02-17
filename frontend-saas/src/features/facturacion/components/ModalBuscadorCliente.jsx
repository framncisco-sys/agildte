import { useState } from 'react'
import { Search, X, Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import { searchClientes } from '../../../api/clientes'

export function ModalBuscadorCliente({ isOpen, onClose, onSelect }) {
  const [nombre, setNombre] = useState('')
  const [documento, setDocumento] = useState('')
  const [resultados, setResultados] = useState([])
  const [buscando, setBuscando] = useState(false)

  const handleBuscar = async (e) => {
    e.preventDefault()
    setBuscando(true)
    try {
      const list = await searchClientes({ nombre, documento })
      setResultados(list)
    } catch (err) {
      setResultados([])
      toast.error(err.response?.data?.detail ?? err.message ?? 'Error al buscar clientes')
    } finally {
      setBuscando(false)
    }
  }

  const handleSelect = (cliente) => {
    onSelect(cliente)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col rounded-xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 id="modal-title" className="text-lg font-semibold text-gray-800">
            Buscar Cliente
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
            aria-label="Cerrar"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleBuscar} className="p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre
              </label>
              <input
                type="text"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Nombre o razón social"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Documento (NIT/DUI)
              </label>
              <input
                type="text"
                value={documento}
                onChange={(e) => setDocumento(e.target.value)}
                placeholder="NIT, NRC o DUI"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={buscando || (!nombre && !documento)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Search size={18} />
            {buscando ? 'Buscando...' : 'Buscar'}
          </button>
        </form>

        <div className="flex-1 overflow-auto px-6 pb-6">
          {resultados.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">
              {buscando ? (
                <span className="inline-flex items-center gap-2">
                  <span className="animate-pulse">●</span> Cargando...
                </span>
              ) : (
                'Ingresa criterios y presiona Buscar'
              )}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-gray-600">
                    <th className="py-2 pr-4">Nombre</th>
                    <th className="py-2 pr-4 hidden sm:table-cell">NIT/NRC</th>
                    <th className="py-2 pr-4 hidden md:table-cell">Correo</th>
                    <th className="py-2 w-12">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {resultados.map((c) => (
                    <tr
                      key={c.id}
                      className="border-b border-gray-100 hover:bg-gray-50"
                    >
                      <td className="py-3 pr-4 font-medium text-gray-800">
                        {c.nombre}
                      </td>
                      <td className="py-3 pr-4 hidden sm:table-cell text-gray-600">
                        {c.nrc || c.nit || c.dui || '-'}
                      </td>
                      <td className="py-3 pr-4 hidden md:table-cell text-gray-600 truncate max-w-[140px]">
                        {c.email_contacto || '-'}
                      </td>
                      <td className="py-3">
                        <button
                          type="button"
                          onClick={() => handleSelect(c)}
                          className="p-2 rounded-lg text-green-600 hover:bg-green-50 transition-colors"
                          aria-label="Seleccionar cliente"
                          title="Seleccionar"
                        >
                          <Plus size={20} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
