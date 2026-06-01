import { useEffect, useMemo, useState } from 'react'
import { Search, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { getClientes } from '../../../api/clientes'
import { listEmpresas } from '../../../api/empresas'

export default function ClientesGlobalPage() {
  const [clientes, setClientes] = useState([])
  const [empresas, setEmpresas] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filtroEmpresa, setFiltroEmpresa] = useState('')

  useEffect(() => {
    Promise.all([getClientes(), listEmpresas()])
      .then(([c, e]) => {
        setClientes(c)
        setEmpresas(e)
      })
      .catch((err) => {
        toast.error(err.response?.data?.detail ?? 'Error al cargar clientes')
      })
      .finally(() => setLoading(false))
  }, [])

  const empresaMap = useMemo(() => {
    const m = {}
    empresas.forEach((e) => { m[e.id] = e.nombre })
    return m
  }, [empresas])

  const filtrados = useMemo(() => {
    let list = clientes
    if (filtroEmpresa) {
      list = list.filter((c) => String(c.empresa) === filtroEmpresa || String(c.empresa_id) === filtroEmpresa)
    }
    const q = search.trim().toLowerCase()
    if (!q) return list
    return list.filter(
      (c) =>
        (c.nombre || '').toLowerCase().includes(q) ||
        (c.documento_identidad || c.nit || '').toLowerCase().includes(q) ||
        (c.nrc || '').toLowerCase().includes(q)
    )
  }, [clientes, search, filtroEmpresa])

  return (
    <div>
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-800">Gestión global de Clientes</h2>
        <p className="text-sm text-slate-500">
          Monitoreo de clientes finales asociados a todas las empresas del SaaS.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre, NIT o NRC…"
            className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg text-sm"
          />
        </div>
        <select
          value={filtroEmpresa}
          onChange={(e) => setFiltroEmpresa(e.target.value)}
          className="px-3 py-2.5 border border-slate-300 rounded-lg text-sm min-w-[200px]"
        >
          <option value="">Todas las empresas</option>
          {empresas.map((e) => (
            <option key={e.id} value={String(e.id)}>{e.nombre}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      ) : (
        <div className="overflow-x-auto bg-white rounded-xl border border-slate-200 shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left p-3 font-medium text-slate-600">Cliente</th>
                <th className="text-left p-3 font-medium text-slate-600">Documento</th>
                <th className="text-left p-3 font-medium text-slate-600">NRC</th>
                <th className="text-left p-3 font-medium text-slate-600">Empresa</th>
                <th className="text-left p-3 font-medium text-slate-600">Correo</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500">Sin clientes</td>
                </tr>
              ) : (
                filtrados.map((c) => (
                  <tr key={c.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/80">
                    <td className="p-3 font-medium text-slate-800">{c.nombre}</td>
                    <td className="p-3 font-mono text-xs text-slate-600">
                      {c.documento_identidad || c.nit || c.dui || '—'}
                    </td>
                    <td className="p-3 font-mono text-xs text-slate-600">{c.nrc || '—'}</td>
                    <td className="p-3 text-slate-600">
                      {empresaMap[c.empresa] || empresaMap[c.empresa_id] || '—'}
                    </td>
                    <td className="p-3 text-slate-600">{c.correo || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          <p className="px-4 py-2 text-xs text-slate-500 border-t border-slate-100">
            {filtrados.length} cliente(s) mostrados
          </p>
        </div>
      )}
    </div>
  )
}
