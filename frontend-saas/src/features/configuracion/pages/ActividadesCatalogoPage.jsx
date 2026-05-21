import { FileSpreadsheet } from 'lucide-react'
import { ActividadesCatalogoCard } from '../components/ActividadesCatalogoCard'

/** Página dedicada: importar CSV/Excel del MH (visible en el menú lateral). */
export default function ActividadesCatalogoPage() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-emerald-50">
          <FileSpreadsheet className="h-6 w-6 text-emerald-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Catálogo de actividades (MH)</h1>
          <p className="text-sm text-slate-500">
            Suba el archivo CSV o Excel que publica el Ministerio de Hacienda. No requiere seleccionar empresa.
          </p>
        </div>
      </div>
      <ActividadesCatalogoCard />
    </div>
  )
}
