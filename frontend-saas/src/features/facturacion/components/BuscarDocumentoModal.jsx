import { useState } from 'react'
import { X, Search, Loader2, Check } from 'lucide-react'
import { getVentas } from '../../../api/facturas'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'
import toast from 'react-hot-toast'

/**
 * Modal para buscar documentos fiscales (Factura/CCF) procesados por MH.
 * Filtros: rango de fechas, búsqueda por cliente o correlativo.
 * Tabla: Fecha, Correlativo, Tipo DTE, Cliente, Total. Botón "Seleccionar" por fila.
 */
export function BuscarDocumentoModal({ isOpen, onClose, onSelect }) {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [fechaInicio, setFechaInicio] = useState('')
  const [fechaFin, setFechaFin] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [resultados, setResultados] = useState([])
  const [cargando, setCargando] = useState(false)

  const handleBuscar = async (e) => {
    e?.preventDefault()
    if (!empresaId) {
      toast.error('Selecciona una empresa')
      return
    }
    setCargando(true)
    try {
      const filters = {
        empresa_id: empresaId,
        solo_procesadas: true,
      }
      if (fechaInicio) filters.fecha_inicio = fechaInicio
      if (fechaFin) filters.fecha_fin = fechaFin
      if (busqueda.trim()) filters.search = busqueda.trim()

      const data = await getVentas(filters)
      const list = Array.isArray(data) ? data : (data?.results ?? data?.ventas ?? [])
      const soloFacturas = list.filter((v) => v.estado === 'PROCESADO' && ['CF', 'CCF'].includes(v.tipo_venta))
      setResultados(soloFacturas)
      if (soloFacturas.length === 0) toast('No hay documentos procesados con esos filtros')
    } catch (err) {
      toast.error(err.response?.data?.detail ?? err.message ?? 'Error al buscar')
      setResultados([])
    } finally {
      setCargando(false)
    }
  }

  const handleSeleccionar = (venta) => {
    onSelect?.(venta)
    onClose?.()
  }

  const formatTotal = (v) => {
    const grav = Number(v.venta_gravada ?? v.venta_gravada ?? 0)
    const iva = v.tipo_venta === 'CCF' ? grav * 0.13 : 0
    return (grav + iva).toFixed(2)
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-buscar-doc-title"
    >
      <div
        className="w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl bg-white shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-amber-50">
          <h2 id="modal-buscar-doc-title" className="text-lg font-semibold text-amber-900">
            Buscar documento origen (Factura / CCF)
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-amber-700 hover:bg-amber-200 transition-colors"
            aria-label="Cerrar"
          >
            <X size={22} />
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            e.stopPropagation()
            handleBuscar(e)
          }}
          className="p-6 border-b border-gray-100 space-y-4"
        >
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fecha inicio</label>
              <input
                type="date"
                value={fechaInicio}
                onChange={(e) => setFechaInicio(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-400 focus:border-amber-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fecha fin</label>
              <input
                type="date"
                value={fechaFin}
                onChange={(e) => setFechaFin(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-400 focus:border-amber-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cliente o correlativo</label>
              <input
                type="text"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="Nombre, NRC o número de control..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-400 focus:border-amber-400"
              />
            </div>
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              handleBuscar(e)
            }}
            disabled={cargando}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-500 text-white font-medium rounded-lg hover:bg-amber-600 disabled:opacity-70 transition-colors"
          >
            {cargando ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
            Buscar
          </button>
        </form>

        <div className="flex-1 overflow-auto p-6">
          {cargando && resultados.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-gray-500">
              <Loader2 size={32} className="animate-spin text-amber-500" />
            </div>
          ) : resultados.length === 0 ? (
            <p className="text-center text-gray-500 py-8">
              Usa los filtros y pulsa &quot;Buscar&quot; para listar facturas/CCF procesados.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-gray-200">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-100 text-left text-gray-600 font-medium">
                    <th className="py-3 px-4 w-28">Fecha</th>
                    <th className="py-3 px-4">Correlativo</th>
                    <th className="py-3 px-4 w-24">Tipo DTE</th>
                    <th className="py-3 px-4">Cliente</th>
                    <th className="py-3 px-4 w-28 text-right">Total</th>
                    <th className="py-3 px-4 w-28 text-center">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {resultados.map((v) => (
                    <tr
                      key={v.id}
                      className="border-b border-gray-100 hover:bg-amber-50/50 transition-colors"
                    >
                      <td className="py-3 px-4 text-gray-700">
                        {v.fecha_emision || v.fechaEmision || '—'}
                      </td>
                      <td className="py-3 px-4 font-mono text-gray-800">
                        {v.numero_control || v.numeroControl || '—'}
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-gray-200 text-gray-700">
                          DTE-{v.tipo_venta === 'CF' ? '01' : '03'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-700 max-w-[200px] truncate" title={v.nombre_receptor || v.cliente?.nombre}>
                        {v.nombre_receptor || v.nombreReceptor || v.cliente?.nombre || '—'}
                      </td>
                      <td className="py-3 px-4 text-right font-medium text-gray-800">
                        ${formatTotal(v)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => handleSeleccionar(v)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 transition-colors"
                        >
                          <Check size={16} />
                          Seleccionar
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
