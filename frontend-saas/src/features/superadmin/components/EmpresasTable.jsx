import { Link } from 'react-router-dom'
import { Pencil, Trash2, Loader2 } from 'lucide-react'

/**
 * Tabla de empresas integradas al SaaS.
 */
export function EmpresasTable({ empresas = [], loading = false, onDelete }) {
  if (loading) {
    return (
      <div className="flex justify-center py-16 text-slate-500">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (!empresas.length) {
    return (
      <div className="text-center py-16 text-slate-500 bg-white rounded-xl border border-slate-200">
        No hay empresas registradas. Cree la primera con el botón «Nueva empresa».
      </div>
    )
  }

  return (
    <div className="overflow-x-auto bg-white rounded-xl border border-slate-200 shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="text-left p-3 font-medium text-slate-600">Empresa</th>
            <th className="text-left p-3 font-medium text-slate-600">NRC</th>
            <th className="text-left p-3 font-medium text-slate-600">NIT</th>
            <th className="text-left p-3 font-medium text-slate-600">Ambiente</th>
            <th className="text-left p-3 font-medium text-slate-600">Contingencia</th>
            <th className="text-right p-3 font-medium text-slate-600">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {empresas.map((e) => (
            <tr key={e.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/80">
              <td className="p-3 font-medium text-slate-800">{e.nombre}</td>
              <td className="p-3 text-slate-600 font-mono text-xs">{e.nrc}</td>
              <td className="p-3 text-slate-600 font-mono text-xs">{e.nit || '—'}</td>
              <td className="p-3">
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                  e.ambiente === '00' ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
                }`}>
                  {e.ambiente === '00' ? 'Producción' : 'Pruebas'}
                </span>
              </td>
              <td className="p-3">
                {e.contingencia_activa ? (
                  <span className="text-amber-700 text-xs font-medium">Activa</span>
                ) : (
                  <span className="text-slate-400 text-xs">—</span>
                )}
              </td>
              <td className="p-3">
                <div className="flex justify-end gap-1">
                  <Link
                    to={`/superadmin/empresas/${e.id}`}
                    className="p-2 rounded-lg text-indigo-600 hover:bg-indigo-50"
                    title="Ver / editar"
                  >
                    <Pencil className="h-4 w-4" />
                  </Link>
                  <button
                    type="button"
                    onClick={() => onDelete?.(e)}
                    className="p-2 rounded-lg text-red-600 hover:bg-red-50"
                    title="Eliminar"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
