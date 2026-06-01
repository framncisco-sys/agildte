import { useEffect, useState } from 'react'
import { FileSpreadsheet, Loader2, RefreshCw } from 'lucide-react'
import { ActividadesCatalogoCard } from '../../configuracion/components/ActividadesCatalogoCard'
import { getActividades } from '../../../api/actividades'

const CATALOGOS_INFO = [
  { titulo: 'Actividades económicas', desc: 'Códigos oficiales de actividad económica (CIIU MH).' },
  { titulo: 'Departamentos / municipios', desc: 'Catálogo geográfico para receptores DTE (próximamente importación centralizada).' },
  { titulo: 'Tipos de DTE', desc: 'FE (01), CCF (03), NC (05), ND (06), FSE (14), F05 contingencia.' },
  { titulo: 'Unidades de medida', desc: 'Catálogo MH de unidades (integrado en generador DTE).' },
]

export default function CatalogosMHPage() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  const cargarStats = () => {
    setLoading(true)
    getActividades({ limit: 1, offset: 0 })
      .then((data) => setStats({ total: data.count ?? data.results?.length ?? 0 }))
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    cargarStats()
  }, [])

  return (
    <div>
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-800">Catálogos del Ministerio de Hacienda</h2>
        <p className="text-sm text-slate-500">
          Visualización y sincronización de catálogos oficiales usados en facturación electrónica.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 gap-4 mb-6">
        {CATALOGOS_INFO.map((cat) => (
          <div key={cat.titulo} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-start gap-3">
              <FileSpreadsheet className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-slate-800">{cat.titulo}</h3>
                <p className="text-sm text-slate-500 mt-0.5">{cat.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-slate-600">
          Actividades en base de datos:{' '}
          {loading ? (
            <Loader2 className="inline h-4 w-4 animate-spin" />
          ) : (
            <strong>{stats?.total ?? '—'}</strong>
          )}
        </p>
        <button
          type="button"
          onClick={cargarStats}
          className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Actualizar conteo
        </button>
      </div>

      <ActividadesCatalogoCard />
    </div>
  )
}
