import { useState } from 'react'
import { Upload, FileSpreadsheet, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { importarCatalogoActividades } from '../../../api/actividades'

/**
 * Carga el CSV/Excel oficial del MH al catálogo global (toda la plataforma).
 */
export function ActividadesCatalogoCard() {
  const [archivo, setArchivo] = useState(null)
  const [subiendo, setSubiendo] = useState(false)
  const [ultimo, setUltimo] = useState(null)

  const handleFile = (e) => {
    const f = e.target.files?.[0]
    setArchivo(f || null)
    setUltimo(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!archivo) {
      toast.error('Seleccione el archivo CSV o Excel del Ministerio de Hacienda.')
      return
    }
    const nombre = (archivo.name || '').toLowerCase()
    if (!nombre.endsWith('.csv') && !nombre.endsWith('.xlsx') && !nombre.endsWith('.xls')) {
      toast.error('Use .csv (delimitador ;) o .xlsx')
      return
    }
    setSubiendo(true)
    try {
      const data = await importarCatalogoActividades(archivo)
      setUltimo(data)
      toast.success(data.mensaje || 'Catálogo actualizado.')
      setArchivo(null)
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Error al importar.'
      toast.error(typeof msg === 'string' ? msg : 'Error al importar el catálogo.')
    } finally {
      setSubiendo(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-6">
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center gap-2">
        <FileSpreadsheet className="h-5 w-5 text-emerald-600" />
        <h2 className="font-semibold text-slate-800">Catálogo de actividades económicas (MH)</h2>
      </div>
      <form onSubmit={handleSubmit} className="p-5 space-y-4">
        <p className="text-sm text-slate-600">
          Suba el archivo que publica el Ministerio de Hacienda (CSV con punto y coma{' '}
          <code className="text-xs bg-slate-100 px-1 rounded">CÓDIGO;ACTIVIDADES ECONÓMICAS</code>
          {' '}o Excel). Se actualizará el catálogo usado en facturación y en PosAgil.
        </p>
        <label className="flex flex-col sm:flex-row sm:items-center gap-3 cursor-pointer">
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 bg-slate-50 text-sm font-medium text-slate-700 hover:bg-slate-100">
            <Upload className="h-4 w-4" />
            Elegir archivo
          </span>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={handleFile}
          />
          <span className="text-sm text-slate-500 truncate">{archivo ? archivo.name : 'Ningún archivo seleccionado'}</span>
        </label>
        <button
          type="submit"
          disabled={subiendo || !archivo}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
        >
          {subiendo ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          {subiendo ? 'Importando…' : 'Importar catálogo'}
        </button>
        {ultimo?.total_en_bd != null && (
          <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
            {ultimo.mensaje}
          </p>
        )}
      </form>
    </div>
  )
}
