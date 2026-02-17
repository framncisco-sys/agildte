import { useState, useEffect, useRef } from 'react'
import { Search, X, FileText, Loader2 } from 'lucide-react'
import { getVentas } from '../../../api/facturas'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'

/**
 * Buscador asíncrono de facturas procesadas para Nota de Crédito/Débito.
 * Solo muestra facturas con sello de MH (PROCESADAS).
 */
export function BuscadorDocumentoRelacionado({ valor, onChange, error, disabled }) {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [busqueda, setBusqueda] = useState('')
  const [resultados, setResultados] = useState([])
  const [cargando, setCargando] = useState(false)
  const [abierto, setAbierto] = useState(false)
  const [debounceId, setDebounceId] = useState(null)
  const contenedorRef = useRef(null)

  useEffect(() => {
    if (!abierto) return
    const handler = (e) => {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target)) setAbierto(false)
    }
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [abierto])

  useEffect(() => {
    if (!busqueda.trim() || busqueda.length < 2) {
      setResultados([])
      return
    }
    if (debounceId) clearTimeout(debounceId)
    const id = setTimeout(async () => {
      setCargando(true)
      try {
        const data = await getVentas({
          empresa_id: empresaId,
          search: busqueda.trim(),
          solo_procesadas: true,
        })
        const list = Array.isArray(data) ? data : (data?.results ?? data?.ventas ?? [])
        setResultados(list.filter((v) => ['CF', 'CCF'].includes(v.tipo_venta)))
      } catch {
        setResultados([])
      } finally {
        setCargando(false)
      }
    }, 350)
    setDebounceId(id)
    return () => clearTimeout(id)
  }, [busqueda, empresaId])

  const facturaSeleccionada = valor

  const handleSelect = (venta) => {
    onChange?.({
      id: venta.id,
      codigoGeneracion: venta.codigo_generacion || venta.codigoGeneracion,
      fechaEmision: venta.fecha_emision || venta.fechaEmision || venta.fecha_hora_emision?.slice(0, 10),
      tipoDte: venta.tipo_venta === 'CF' ? '01' : '03',
      numeroControl: venta.numero_control || venta.numeroControl,
      nombreReceptor: venta.nombre_receptor || venta.nombreReceptor || venta.cliente?.nombre,
    })
    setBusqueda('')
    setResultados([])
    setAbierto(false)
  }

  const handleClear = () => {
    onChange?.(null)
    setBusqueda('')
    setResultados([])
  }

  return (
    <div ref={contenedorRef} className="relative">
      {facturaSeleccionada ? (
        <div className="flex items-center justify-between gap-3 p-4 rounded-xl border-2 border-amber-300 bg-amber-50">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-lg bg-amber-100">
              <FileText size={20} className="text-amber-700" />
            </div>
            <div className="min-w-0">
              <p className="font-medium text-gray-800 truncate">
                {facturaSeleccionada.numeroControl || facturaSeleccionada.codigoGeneracion?.slice(0, 8) + '...'}
              </p>
              <p className="text-sm text-gray-600">
                {facturaSeleccionada.fechaEmision} · DTE-{facturaSeleccionada.tipoDte}
                {facturaSeleccionada.nombreReceptor && ` · ${facturaSeleccionada.nombreReceptor}`}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClear}
            disabled={disabled}
            className="p-2 rounded-lg text-amber-700 hover:bg-amber-200 transition-colors shrink-0"
            aria-label="Quitar documento"
          >
            <X size={18} />
          </button>
        </div>
      ) : (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            value={busqueda}
            onChange={(e) => {
              setBusqueda(e.target.value)
              setAbierto(true)
            }}
            onFocus={() => setAbierto(true)}
            placeholder="Buscar por correlativo, cliente o UUID..."
            disabled={disabled}
            className={`w-full pl-10 pr-4 py-3 rounded-xl border-2 bg-white focus:ring-2 focus:ring-amber-400 focus:border-amber-400 outline-none transition-colors ${
              error ? 'border-red-400' : 'border-amber-200'
            }`}
          />
          {cargando && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-amber-600" size={18} />
          )}
        </div>
      )}

      {abierto && !facturaSeleccionada && (busqueda.trim().length >= 2 || resultados.length > 0) && (
        <div className="absolute z-50 mt-2 w-full rounded-xl border border-gray-200 bg-white shadow-lg max-h-64 overflow-y-auto">
          {cargando && resultados.length === 0 ? (
            <div className="p-4 text-center text-gray-500">Buscando...</div>
          ) : resultados.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              {busqueda.trim().length >= 2 ? 'No hay facturas procesadas que coincidan' : 'Escribe al menos 2 caracteres'}
            </div>
          ) : (
            <ul className="py-1">
              {resultados.map((v) => (
                <li key={v.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(v)}
                    className="w-full px-4 py-3 text-left hover:bg-amber-50 flex flex-col gap-0.5 border-b border-gray-100 last:border-0"
                  >
                    <span className="font-medium text-gray-800">
                      {v.numero_control || v.numeroControl || v.codigo_generacion?.slice(0, 8) + '...'}
                    </span>
                    <span className="text-sm text-gray-500">
                      {v.fecha_emision || v.fechaEmision} · DTE-{v.tipo_venta === 'CF' ? '01' : '03'} ·{' '}
                      {v.nombre_receptor || v.nombreReceptor || v.cliente?.nombre || '—'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error && <p className="mt-1.5 text-sm text-red-600">{error}</p>}
    </div>
  )
}
