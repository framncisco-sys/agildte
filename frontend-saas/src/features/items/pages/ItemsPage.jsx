import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, Search, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { getItems, deleteItem } from '../../../api/items'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'
import { ItemFormModal } from '../components/ItemFormModal'

const TIPO_IMPUESTO_LABEL = { '20': 'Gravado 13%', exento: 'Exento' }
const TIPO_ITEM_LABEL = { 1: 'Bien', 2: 'Servicio' }

export default function ItemsPage() {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [itemEdit, setItemEdit] = useState(null)

  const fetchList = async () => {
    if (!empresaId) {
      setList([])
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const data = await getItems({ empresa_id: empresaId, q: search.trim() || undefined })
      setList(Array.isArray(data) ? data : [])
    } catch (err) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Error al cargar ítems')
      setList([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchList()
  }, [empresaId])

  useEffect(() => {
    if (!empresaId) return
    const t = setTimeout(() => {
      getItems({ empresa_id: empresaId, q: search.trim() || undefined })
        .then((data) => setList(Array.isArray(data) ? data : []))
        .catch(() => setList([]))
    }, 300)
    return () => clearTimeout(t)
  }, [search, empresaId])

  const handleNew = () => {
    setItemEdit(null)
    setModalOpen(true)
  }

  const handleEdit = (item) => {
    setItemEdit(item)
    setModalOpen(true)
  }

  const handleDelete = async (item) => {
    const name = item.descripcion || 'este ítem'
    if (!window.confirm(`¿Eliminar "${name}"? El ítem se desactivará y ya no aparecerá en el listado.`)) return
    try {
      await deleteItem(item.id)
      toast.success('Ítem eliminado.')
      fetchList()
    } catch (err) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Error al eliminar')
    }
  }

  const handleSaved = () => {
    fetchList()
  }

  const formatPrecio = (v) => {
    const n = Number(v)
    return isNaN(n) ? '$0.00' : `$${n.toFixed(2)}`
  }

  if (!empresaId) {
    return (
      <div className="p-4 sm:p-6 max-w-6xl mx-auto">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800 mb-4">Administración de Ítems</h1>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-800">
          Seleccione una empresa en la barra superior para gestionar su catálogo de ítems.
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4 sm:mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Administración de Ítems</h1>
        <button
          type="button"
          onClick={handleNew}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
        >
          <Plus size={20} />
          Nuevo Ítem
        </button>
      </div>

      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por descripción o código..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            aria-label="Buscar ítems"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden min-w-0">
        {loading ? (
          <div className="p-12 flex justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : list.length === 0 ? (
          <div className="p-8 sm:p-12 text-center text-gray-500">
            No hay ítems. Use &quot;Nuevo Ítem&quot; para agregar productos o servicios al catálogo.
          </div>
        ) : (
          <>
            {/* Móvil: cards */}
            <div className="md:hidden divide-y divide-gray-100">
              {list.map((row) => (
                <div key={row.id} className="p-4 space-y-2">
                  <p className="font-medium text-gray-800">{row.descripcion}</p>
                  {(row.codigo || row.codigo === 0) && (
                    <p className="text-sm text-gray-500">Código: {row.codigo}</p>
                  )}
                  <p className="text-sm font-semibold text-gray-900">{formatPrecio(row.precio_unitario)}</p>
                  <p className="text-xs text-gray-500">
                    {TIPO_IMPUESTO_LABEL[row.tipo_impuesto] ?? row.tipo_impuesto} · {TIPO_ITEM_LABEL[row.tipo_item] ?? 'Ítem'}
                  </p>
                  <div className="flex gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => handleEdit(row)}
                      className="p-2 rounded-lg text-blue-600 hover:bg-blue-50"
                      aria-label="Editar"
                    >
                      <Pencil size={18} />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(row)}
                      className="p-2 rounded-lg text-red-600 hover:bg-red-50"
                      aria-label="Eliminar"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            {/* Escritorio: tabla */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm min-w-[500px]">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Descripción</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Código</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-700">Precio unit.</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Impuesto</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-700 w-28">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((row, idx) => (
                    <tr
                      key={row.id}
                      className={`border-b border-gray-100 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} hover:bg-blue-50/30 transition-colors`}
                    >
                      <td className="px-4 py-3 font-medium text-gray-800">{row.descripcion || '—'}</td>
                      <td className="px-4 py-3 text-gray-600">{row.codigo || '—'}</td>
                      <td className="px-4 py-3 text-right font-medium text-gray-800">{formatPrecio(row.precio_unitario)}</td>
                      <td className="px-4 py-3 text-gray-600">{TIPO_IMPUESTO_LABEL[row.tipo_impuesto] ?? row.tipo_impuesto}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => handleEdit(row)}
                            className="p-2 rounded-lg text-blue-600 hover:bg-blue-50"
                            aria-label="Editar"
                            title="Editar"
                          >
                            <Pencil size={18} />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(row)}
                            className="p-2 rounded-lg text-red-600 hover:bg-red-50"
                            aria-label="Eliminar"
                            title="Eliminar"
                          >
                            <Trash2 size={18} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      <ItemFormModal
        isOpen={modalOpen}
        onClose={() => { setModalOpen(false); setItemEdit(null) }}
        onSaved={handleSaved}
        itemEdit={itemEdit}
        empresaId={empresaId}
      />
    </div>
  )
}
