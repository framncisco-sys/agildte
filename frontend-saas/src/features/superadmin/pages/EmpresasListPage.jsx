import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { listEmpresas, deleteEmpresa } from '../../../api/empresas'
import { EmpresasTable } from '../components/EmpresasTable'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'

export default function EmpresasListPage() {
  const [empresas, setEmpresas] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const setEmpresasStore = useEmpresaStore((s) => s.setEmpresas)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listEmpresas()
      setEmpresas(data)
      setEmpresasStore(data.map((e) => ({ id: e.id, nombre: e.nombre })))
    } catch (err) {
      toast.error(err.response?.data?.detail ?? 'Error al cargar empresas')
      setEmpresas([])
    } finally {
      setLoading(false)
    }
  }, [setEmpresasStore])

  useEffect(() => {
    cargar()
  }, [cargar])

  const filtradas = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return empresas
    return empresas.filter(
      (e) =>
        (e.nombre || '').toLowerCase().includes(q) ||
        (e.nrc || '').toLowerCase().includes(q) ||
        (e.nit || '').toLowerCase().includes(q)
    )
  }, [empresas, search])

  const handleDelete = async (empresa) => {
    if (!window.confirm(`¿Eliminar la empresa «${empresa.nombre}»? Esta acción no se puede deshacer.`)) return
    try {
      await deleteEmpresa(empresa.id)
      toast.success('Empresa eliminada')
      cargar()
    } catch (err) {
      toast.error(err.response?.data?.detail ?? 'No se pudo eliminar la empresa')
    }
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Gestión de Empresas</h2>
          <p className="text-sm text-slate-500">Alta, baja, edición y pruebas de estrés por tenant.</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={cargar}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 text-sm"
          >
            <RefreshCw className="h-4 w-4" />
            Actualizar
          </button>
          <Link
            to="/superadmin/empresas/nueva"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            Nueva empresa
          </Link>
        </div>
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre, NRC o NIT…"
          className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <EmpresasTable empresas={filtradas} loading={loading} onDelete={handleDelete} />
    </div>
  )
}
