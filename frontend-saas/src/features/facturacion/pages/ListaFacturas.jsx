import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Search, FileText, Braces, Eye, Loader2, CircleX, FileDown, FolderDown, Send } from 'lucide-react'
import toast from 'react-hot-toast'
import { getVentas, downloadPDF, downloadJSON, downloadFacturasFiltradasZip, reenviarVenta } from '../../../api/facturas'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'
import { DetalleRechazoModal } from '../components/DetalleRechazoModal'
import { InvalidacionModal } from '../components/InvalidacionModal'

const ESTADO_BADGES = {
  PROCESADO: { label: 'PROCESADO', color: 'bg-emerald-100 text-emerald-800', icon: '🟢' },
  RECHAZADO: { label: 'RECHAZADO', color: 'bg-red-100 text-red-800', icon: '🔴' },
  ANULADO: { label: 'ANULADO', color: 'bg-gray-200 text-gray-700', icon: '⚫' },
  PENDIENTE: { label: 'PENDIENTE', color: 'bg-amber-100 text-amber-800', icon: '🟡' },
}

function formatFecha(value) {
  if (!value) return '—'
  // Prioridad: fecha_hora_emision (ISO) > fecha_emision (date)
  const str = typeof value === 'object' && value !== null
    ? (value.fecha_hora_emision || value.fecha_emision || '')
    : String(value || '')
  if (!str) return '—'
  const d = new Date(str)
  if (isNaN(d.getTime())) return String(str)
  const pad = (n) => String(n).padStart(2, '0')
  const h = d.getHours()
  const ampm = h >= 12 ? 'PM' : 'AM'
  const h12 = h % 12 || 12
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(h12)}:${pad(d.getMinutes())} ${ampm}`
}

function formatMoneda(val) {
  if (val == null || val === '') return '$0.00'
  const n = Number(val)
  return isNaN(n) ? '$0.00' : `$${n.toFixed(2)}`
}

const PAGE_SIZE = 20

function Paginacion({ page, totalPages, totalCount, pageSize, onPageChange, cargando }) {
  if (totalPages <= 1 && totalCount === 0) return null

  const inicio = totalCount === 0 ? 0 : (page - 1) * pageSize + 1
  const fin = Math.min(page * pageSize, totalCount)

  // Generar rango de páginas visible (máx 5 botones)
  const rango = []
  const delta = 2
  const left = Math.max(1, page - delta)
  const right = Math.min(totalPages, page + delta)
  for (let i = left; i <= right; i++) rango.push(i)

  const btnBase = 'inline-flex items-center justify-center h-8 min-w-[2rem] px-2 rounded-lg text-sm font-medium transition-colors'
  const btnActivo = 'bg-emerald-600 text-white shadow-sm'
  const btnNormal = 'text-gray-600 hover:bg-gray-100 border border-gray-200'
  const btnDisabled = 'text-gray-300 border border-gray-100 cursor-not-allowed'

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 border-t border-gray-100 bg-white rounded-b-xl">
      <p className="text-sm text-gray-500 shrink-0">
        {totalCount === 0
          ? 'Sin resultados'
          : `Mostrando ${inicio}–${fin} de ${totalCount} factura${totalCount !== 1 ? 's' : ''}`}
      </p>
      {totalPages > 1 && (
        <div className="flex items-center gap-1">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1 || cargando}
            className={`${btnBase} ${page <= 1 || cargando ? btnDisabled : btnNormal}`}
            title="Página anterior"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          {left > 1 && (
            <>
              <button onClick={() => onPageChange(1)} className={`${btnBase} ${btnNormal}`}>1</button>
              {left > 2 && <span className="px-1 text-gray-400 text-sm">…</span>}
            </>
          )}

          {rango.map((p) => (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              disabled={cargando}
              className={`${btnBase} ${p === page ? btnActivo : btnNormal}`}
            >
              {p}
            </button>
          ))}

          {right < totalPages && (
            <>
              {right < totalPages - 1 && <span className="px-1 text-gray-400 text-sm">…</span>}
              <button onClick={() => onPageChange(totalPages)} className={`${btnBase} ${btnNormal}`}>{totalPages}</button>
            </>
          )}

          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || cargando}
            className={`${btnBase} ${page >= totalPages || cargando ? btnDisabled : btnNormal}`}
            title="Página siguiente"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
}

export function ListaFacturas() {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [filtrosAbiertos, setFiltrosAbiertos] = useState(false)
  const [ventas, setVentas] = useState([])
  const [paginacion, setPaginacion] = useState({ count: 0, total_pages: 1, page: 1, has_next: false, has_previous: false })
  const [paginaActual, setPaginaActual] = useState(1)
  const [cargando, setCargando] = useState(false)
  const [modalRechazo, setModalRechazo] = useState(null)
  const [modalInvalidacion, setModalInvalidacion] = useState(null)
  const [descargandoLote, setDescargandoLote] = useState(null)
  const [reenviandoId, setReenviandoId] = useState(null)

  const [filtros, setFiltros] = useState({
    fecha_inicio: '',
    fecha_fin: '',
    tipo_dte: '',
    search: '',
  })

  // Ref para disparar búsqueda: { page, trigger }
  const [buscarTrigger, setBuscarTrigger] = useState({ page: 1, ts: Date.now() })

  const dispararBusqueda = (page = 1) => {
    setPaginaActual(page)
    setBuscarTrigger({ page, ts: Date.now() })
  }

  const handleBuscar = () => dispararBusqueda(1)

  const handleCambiarPagina = (nuevaPagina) => {
    dispararBusqueda(nuevaPagina)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const limpiarFiltros = () => {
    setFiltros({ fecha_inicio: '', fecha_fin: '', tipo_dte: '', search: '' })
    setVentas([])
    setPaginacion({ count: 0, total_pages: 1, page: 1, has_next: false, has_previous: false })
    setPaginaActual(1)
  }

  // Ejecutar búsqueda cuando cambia el trigger o la empresa
  const filtrosRef = useRef(filtros)
  filtrosRef.current = filtros

  useEffect(() => {
    const fetchData = async () => {
      setCargando(true)
      try {
        const params = { ...filtrosRef.current, page: buscarTrigger.page, page_size: PAGE_SIZE }
        if (empresaId) params.empresa_id = empresaId
        const data = await getVentas(params)
        setVentas(Array.isArray(data.results) ? data.results : [])
        setPaginacion({
          count: data.count ?? 0,
          total_pages: data.total_pages ?? 1,
          page: data.page ?? buscarTrigger.page,
          has_next: data.has_next ?? false,
          has_previous: data.has_previous ?? false,
        })
        setPaginaActual(data.page ?? buscarTrigger.page)
      } catch (err) {
        toast.error(err.response?.data?.detail || err.message || 'Error al cargar ventas')
        setVentas([])
      } finally {
        setCargando(false)
      }
    }
    fetchData()
  }, [buscarTrigger, empresaId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Reiniciar a página 1 cuando cambia la empresa
  const prevEmpresaId = useRef(empresaId)
  useEffect(() => {
    if (prevEmpresaId.current !== empresaId) {
      prevEmpresaId.current = empresaId
      dispararBusqueda(1)
    }
  }, [empresaId])

  const handleDownloadPDF = async (v) => {
    try {
      await downloadPDF(v.id, `factura_${v.numero_control || v.id}.pdf`)
      toast.success('PDF descargado')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al descargar PDF')
    }
  }

  const handleDownloadJSON = async (v) => {
    try {
      await downloadJSON(v.id, `dte_${v.numero_control || v.id}.json`)
      toast.success('JSON descargado')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al descargar JSON')
    }
  }

  const estadoInfo = (estado) => ESTADO_BADGES[estado] || ESTADO_BADGES.PENDIENTE

  const handleInvalidacionExito = (ventaActualizada) => {
    setVentas((prev) =>
      prev.map((v) => (v.id === ventaActualizada.id ? { ...v, estado_dte: 'Anulado', estado: 'ANULADO' } : v))
    )
  }

  const handleReenviar = async (v) => {
    setReenviandoId(v.id)
    try {
      const data = await reenviarVenta(v.id)
      setVentas((prev) =>
        prev.map((item) => (item.id === v.id ? { ...item, ...data, estado: data.estado || 'PROCESADO' } : item))
      )
      toast.success(data.mensaje || 'Factura enviada correctamente')
    } catch (err) {
      const resp = err.response
      const msg = resp?.data?.mensaje || resp?.data?.error || err.message || 'Error al reenviar'
      const sugerencia = resp?.data?.sugerencia
      toast.error(sugerencia ? `${msg}\n${sugerencia}` : msg, { duration: 6000 })
      // Si MH rechazó, el backend devuelve 400 con la venta actualizada
      if (resp?.status === 400 && resp?.data?.id === v.id && resp?.data?.estado) {
        setVentas((prev) =>
          prev.map((item) => (item.id === v.id ? { ...item, ...resp.data } : item))
        )
      }
    } finally {
      setReenviandoId(null)
    }
  }

  /** Descarga ZIP de PDFs o JSONs según filtros (misma query que la tabla). */
  const handleDescargaZipFiltrado = async (format) => {
    setDescargandoLote(format)
    try {
      await downloadFacturasFiltradasZip({ ...filtros, empresa_id: empresaId }, format)
      toast.success(`ZIP de ${format.toUpperCase()} descargado`)
    } catch (err) {
      const d = err.response?.data
      const msg =
        (typeof d === 'object' && d && (d.error || d.detail)) ||
        err.message ||
        'Error al descargar'
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setDescargandoLote(null)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-2 sm:px-0">
      <h1 className="text-lg sm:text-xl font-semibold text-gray-800 mb-4 sm:mb-6">Historial de Documentos</h1>

      {/* Filtros Acordeón */}
      <div className="mb-6 border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
        <button
          type="button"
          onClick={() => setFiltrosAbiertos((x) => !x)}
          className="w-full flex items-center justify-between px-5 py-3 text-left font-medium text-gray-700 hover:bg-gray-50"
        >
          <span className="flex items-center gap-2">
            <Search className="w-4 h-4" />
            Filtros Avanzados
          </span>
          {filtrosAbiertos ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
        {filtrosAbiertos && (
          <div className="px-5 pb-5 pt-0 border-t border-gray-100 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Fecha Inicio</label>
                <input
                  type="date"
                  value={filtros.fecha_inicio}
                  onChange={(e) => setFiltros((f) => ({ ...f, fecha_inicio: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Fecha Fin</label>
                <input
                  type="date"
                  value={filtros.fecha_fin}
                  onChange={(e) => setFiltros((f) => ({ ...f, fecha_fin: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Tipo Documento</label>
                <select
                  value={filtros.tipo_dte}
                  onChange={(e) => setFiltros((f) => ({ ...f, tipo_dte: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Todos</option>
                  <option value="01">Factura (CF)</option>
                  <option value="03">Crédito Fiscal (CCF)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Buscar</label>
                <input
                  type="text"
                  placeholder="Correlativo o cliente..."
                  value={filtros.search}
                  onChange={(e) => setFiltros((f) => ({ ...f, search: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleBuscar}
                disabled={cargando}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {cargando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                Buscar
              </button>
              <button
                type="button"
                onClick={limpiarFiltros}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Limpiar
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Descarga masiva según filtros (PDF o JSON DTE en ZIP) */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => handleDescargaZipFiltrado('pdf')}
          disabled={!!descargandoLote}
          className="px-3 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 flex items-center gap-2 text-sm"
          title="Genera un ZIP con el PDF de cada factura que coincida con los filtros (máx. 100 por lote)"
        >
          {descargandoLote === 'pdf' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
          Descargar PDFs filtrados (ZIP)
        </button>
        <button
          type="button"
          onClick={() => handleDescargaZipFiltrado('json')}
          disabled={!!descargandoLote}
          className="px-3 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 flex items-center gap-2 text-sm"
          title="Genera un ZIP con el JSON DTE de cada factura que coincida con los filtros (máx. 100 por lote)"
        >
          {descargandoLote === 'json' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FolderDown className="w-4 h-4" />}
          Descargar JSONs filtrados (ZIP)
        </button>
      </div>

      {/* Tabla / Cards */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden min-w-0">
        {cargando ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : ventas.length === 0 ? (
          <div className="py-16 text-center text-gray-500 px-4">No hay documentos que coincidan con los filtros.</div>
        ) : (
          <>
            {/* Móvil: cards */}
            <div className="md:hidden divide-y divide-gray-100">
              {ventas.map((v) => {
                const total = Number(v.venta_gravada || 0) + Number(v.venta_exenta || 0) + Number(v.venta_no_sujeta || 0) + Number(v.debito_fiscal || 0)
                const cliente = v.nombre_receptor || 'Consumidor Final'
                const correlativo = v.numero_control || `Venta #${v.id}`
                const estado = v.estado || 'PENDIENTE'
                const badge = estadoInfo(estado)
                const esProcesado = estado === 'PROCESADO'
                const esRechazado = estado === 'RECHAZADO'
                const esPendiente = estado === 'PENDIENTE'
                const reenviando = reenviandoId === v.id
                return (
                  <div key={v.id} className="p-4 space-y-2">
                    <p className="font-medium text-gray-800">{correlativo}</p>
                    <p className="text-sm text-gray-600">{formatFecha(v)}</p>
                    <p className="text-sm text-gray-700 truncate" title={cliente}>{cliente}</p>
                    <p className="text-sm text-gray-500">Total a pagar: <span className="font-semibold text-gray-900">{formatMoneda(total)}</span></p>
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
                      {badge.icon} {badge.label}
                    </span>
                    {esPendiente && (
                      <button
                        onClick={() => handleReenviar(v)}
                        disabled={reenviando}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-amber-800 bg-amber-100 rounded-lg hover:bg-amber-200 disabled:opacity-60"
                        title="Reenviar a Hacienda (espera respuesta para ver errores)"
                      >
                        {reenviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        Reenviar
                      </button>
                    )}
                    <div className="flex gap-2 pt-2">
                      {esProcesado && (
                        <>
                          <button onClick={() => handleDownloadPDF(v)} className="p-2 rounded-lg text-gray-600 hover:bg-gray-100" title="PDF"><FileText className="w-4 h-4" /></button>
                          <button onClick={() => handleDownloadJSON(v)} className="p-2 rounded-lg text-gray-600 hover:bg-gray-100" title="JSON"><Braces className="w-4 h-4" /></button>
                          <button onClick={() => setModalInvalidacion(v)} className="p-2 rounded-lg text-red-600 hover:bg-red-50" title="Anular"><CircleX className="w-4 h-4" /></button>
                        </>
                      )}
                      {esRechazado && (
                        <button onClick={() => setModalRechazo(v)} className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-700 bg-red-50 rounded-lg"><Eye className="w-4 h-4" /> Ver Error</button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
            {/* Escritorio: tabla con scroll */}
            <div className="overflow-x-auto hidden md:block">
            <table className="w-full min-w-[600px]">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Fecha</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Correlativo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Cliente</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-600 uppercase">Total a pagar</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase">Estado</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-600 uppercase">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {ventas.map((v, i) => {
                  const total = Number(v.venta_gravada || 0) + Number(v.venta_exenta || 0) + Number(v.venta_no_sujeta || 0) + Number(v.debito_fiscal || 0)
                  const cliente = v.nombre_receptor || 'Consumidor Final'
                  const correlativo = v.numero_control || `Venta #${v.id}`
                  const estado = v.estado || 'PENDIENTE'
                  const badge = estadoInfo(estado)
                  const esProcesado = estado === 'PROCESADO'
                  const esRechazado = estado === 'RECHAZADO'
                  const esPendiente = estado === 'PENDIENTE'
                  const reenviando = reenviandoId === v.id
                  return (
                    <tr
                      key={v.id}
                      className={`border-b border-gray-100 ${i % 2 === 1 ? 'bg-gray-50/50' : ''} hover:bg-gray-50`}
                    >
                      <td className="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">
                        {formatFecha(v)}
                      </td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-700">{correlativo}</td>
                      <td className="px-4 py-3 text-sm text-gray-700 max-w-[200px] truncate" title={cliente}>
                        {cliente}
                      </td>
                      <td className="px-4 py-3 text-sm text-right font-medium text-gray-800">
                        {formatMoneda(total)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
                          {badge.icon} {badge.label}
                        </span>
                        {esPendiente && (
                          <button
                            onClick={() => handleReenviar(v)}
                            disabled={reenviando}
                            className="ml-2 inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-amber-800 bg-amber-100 rounded-lg hover:bg-amber-200 disabled:opacity-60"
                            title="Reenviar a Hacienda (espera respuesta para ver errores)"
                          >
                            {reenviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                            Reenviar
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-2">
                          {esProcesado && (
                            <>
                              <button
                                onClick={() => handleDownloadPDF(v)}
                                className="p-2 rounded-lg text-gray-600 hover:bg-gray-200 hover:text-blue-600 transition-colors"
                                title="Descargar PDF"
                              >
                                <FileText className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleDownloadJSON(v)}
                                className="p-2 rounded-lg text-gray-600 hover:bg-gray-200 hover:text-blue-600 transition-colors"
                                title="Descargar JSON"
                              >
                                <Braces className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setModalInvalidacion(v)}
                                className="p-2 rounded-lg text-red-600 hover:bg-red-50 hover:text-red-700 transition-colors"
                                title="Invalidar (Anular) documento"
                              >
                                <CircleX className="w-4 h-4" />
                              </button>
                            </>
                          )}
                          {esRechazado && (
                            <button
                              onClick={() => setModalRechazo(v)}
                              className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                              title="Ver Error"
                            >
                              <Eye className="w-4 h-4" />
                              Ver Error
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            </div>
          </>
        )}
        <Paginacion
          page={paginaActual}
          totalPages={paginacion.total_pages}
          totalCount={paginacion.count}
          pageSize={PAGE_SIZE}
          onPageChange={handleCambiarPagina}
          cargando={cargando}
        />
      </div>

      <DetalleRechazoModal
        open={!!modalRechazo}
        onClose={() => setModalRechazo(null)}
        venta={modalRechazo || {}}
      />

      <InvalidacionModal
        open={!!modalInvalidacion}
        onClose={() => setModalInvalidacion(null)}
        venta={modalInvalidacion || {}}
        onExito={handleInvalidacionExito}
      />
    </div>
  )
}
