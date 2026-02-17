import { useState, useEffect, useMemo } from 'react'
import { Plus, Pencil, Trash2, Search } from 'lucide-react'
import toast from 'react-hot-toast'
import { getClientes, deleteCliente } from '../../../api/clientes'
import { ClienteFormModal } from '../components/ClienteFormModal'

export default function Clientes() {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [clienteEdit, setClienteEdit] = useState(null)

  const fetchList = async () => {
    setLoading(true)
    try {
      const data = await getClientes({ search: search.trim() || undefined })
      setList(data)
    } catch (err) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Error al cargar clientes')
      setList([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchList()
  }, [])

  const filteredList = useMemo(() => {
    if (!search.trim()) return list
    const q = search.trim().toLowerCase()
    return list.filter(
      (c) =>
        (c.nombre || '').toLowerCase().includes(q) ||
        (c.documento_identidad || c.nit || c.dui || '').toLowerCase().includes(q) ||
        (c.nrc || '').toLowerCase().includes(q)
    )
  }, [list, search])

  const handleNew = () => {
    setClienteEdit(null)
    setModalOpen(true)
  }

  const handleEdit = (cliente) => {
    setClienteEdit(cliente)
    setModalOpen(true)
  }

  const handleDelete = async (cliente) => {
    const name = cliente.nombre || 'este cliente'
    if (!window.confirm(`¿Está seguro de eliminar a ${name}? Esta acción no se puede deshacer.`)) return
    try {
      await deleteCliente(cliente.id)
      toast.success('Cliente eliminado.')
      fetchList()
    } catch (err) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Error al eliminar')
    }
  }

  const handleSaved = () => {
    fetchList()
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Cartera de Clientes</h1>
        <button
          type="button"
          onClick={handleNew}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
        >
          <Plus size={20} />
          Nuevo Cliente
        </button>
      </div>

      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre o NIT..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            aria-label="Buscar clientes"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500">Cargando clientes...</div>
        ) : filteredList.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            No hay clientes. Use &quot;Nuevo Cliente&quot; para agregar uno.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-gray-700">Nombre</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-700">Documento (NIT/DUI)</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-700 hidden md:table-cell">NRC</th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-700 hidden lg:table-cell">Correo</th>
                  <th className="px-4 py-3 text-right font-semibold text-gray-700 w-28">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filteredList.map((row, idx) => (
                  <tr
                    key={row.id}
                    className={`border-b border-gray-100 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} hover:bg-blue-50/30 transition-colors`}
                  >
                    <td className="px-4 py-3 font-medium text-gray-800">{row.nombre || '—'}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {row.documento_identidad || row.nit || row.dui || '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-600 hidden md:table-cell">{row.nrc || '—'}</td>
                    <td className="px-4 py-3 text-gray-600 hidden lg:table-cell truncate max-w-[200px]" title={row.correo || row.email_contacto || ''}>
                      {row.correo || row.email_contacto || '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleEdit(row)}
                          className="p-2 rounded-lg text-blue-600 hover:bg-blue-50 transition-colors"
                          aria-label="Editar"
                          title="Editar"
                        >
                          <Pencil size={18} />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(row)}
                          className="p-2 rounded-lg text-red-600 hover:bg-red-50 transition-colors"
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
        )}
      </div>

      <ClienteFormModal
        isOpen={modalOpen}
        onClose={() => { setModalOpen(false); setClienteEdit(null) }}
        onSaved={handleSaved}
        clienteEdit={clienteEdit}
      />
    </div>
  )
}
