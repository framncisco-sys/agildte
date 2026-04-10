import { useState, useCallback } from 'react'
import { Upload, Download, FileSpreadsheet, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { subirArchivoCargaMasiva, descargarPlantillaEjemplo } from '../../../api/cargaMasiva'
import apiClient from '../../../api/axios'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'
import { fechaHoyElSalvadorISO } from '../../../utils/format'

/**
 * Convierte una fila de carga masiva al payload esperado por POST /ventas/crear-con-detalles/
 * Soporta múltiples ítems por factura (fila.items).
 */
function filaToPayload(fila, empresaId) {
  const tipo = fila.tipo_dte
  const esCF = tipo === '01'
  const items = fila.items && fila.items.length ? fila.items : [
    { producto: fila.producto, cantidad: fila.cantidad || 1, precio_unitario: fila.precio_unitario || 0, producto_id: fila.producto_id },
  ]

  const detalles = []
  let ventaGravadaTotal = 0
  let debitoFiscalTotal = 0

  items.forEach((it, idx) => {
    const cant = Number(it.cantidad) || 1
    const prec = Number(it.precio_unitario) || 0
    const totalLinea = cant * prec

    let gravadaItem, ivaItem, precioUnit
    if (esCF) {
      gravadaItem = Math.round((totalLinea / 1.13) * 100) / 100
      ivaItem = Math.round((totalLinea - gravadaItem) * 100) / 100
      precioUnit = cant > 0 ? Math.round((gravadaItem / cant) * 100) / 100 : 0
    } else {
      gravadaItem = totalLinea
      ivaItem = Math.round(gravadaItem * 0.13 * 100) / 100
      precioUnit = prec
    }

    ventaGravadaTotal += gravadaItem
    debitoFiscalTotal += ivaItem

    const det = {
      cantidad: cant,
      descripcion_libre: it.producto || null,
      codigo_libre: null,
      precio_unitario: precioUnit,
      monto_descuento: 0,
      venta_no_sujeta: 0,
      venta_exenta: 0,
      venta_gravada: gravadaItem,
      iva_item: ivaItem,
      numero_item: idx + 1,
    }
    if (it.producto_id) det.producto_id = it.producto_id
    detalles.push(det)
  })

  const hoy = fechaHoyElSalvadorISO()
  const periodo = (fila.fecha || hoy).slice(0, 7)
  const tipoVenta = tipo === '01' ? 'CF' : 'CCF'
  const nombreReceptor = esCF
    ? (fila.nombre_receptor || 'Consumidor Final')
    : (fila.nombre_receptor || fila.cliente || '')
  const documentoReceptor = esCF ? (fila.documento_receptor ?? '') : null

  const body = {
    empresa: empresaId,
    tipo_dte: tipo,
    cliente_id: fila.cliente_id || null,
    cliente: esCF ? null : (fila.cliente || null),
    nombre_receptor: nombreReceptor,
    nombre_comercial_receptor: fila.nombre_comercial || null,
    nit_receptor: esCF ? null : (fila.nit || null),
    documento_receptor: documentoReceptor,
    tipo_doc_receptor: 'NIT',
    receptor_direccion: fila.direccion || null,
    receptor_correo: fila.correo || null,
    receptor_departamento: fila.departamento || null,
    receptor_municipio: fila.municipio || null,
    receptor_telefono: fila.telefono || null,
    cod_actividad_receptor: fila.cod_actividad || null,
    desc_actividad_receptor: fila.desc_actividad || null,
    fecha_emision: fila.fecha || hoy,
    periodo_aplicado: periodo,
    tipo_venta: tipoVenta,
    nrc_receptor: esCF ? null : (fila.cliente || null),
    venta_gravada: ventaGravadaTotal,
    venta_exenta: 0,
    venta_no_sujeta: 0,
    debito_fiscal: debitoFiscalTotal,
    estado_dte: 'Generado',
    clase_documento: '4',
    clasificacion_venta: '1',
    tipo_ingreso: '3',
    condicion_operacion: 1,
    plazo_pago: null,
    periodo_pago: null,
    detalles,
  }
  return body
}

export function CargaMasiva() {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [filas, setFilas] = useState([])
  const [empresaIdArchivo, setEmpresaIdArchivo] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [descargando, setDescargando] = useState(false)
  const [emitiendo, setEmitiendo] = useState(false)
  const [progreso, setProgreso] = useState({ actual: 0, total: 0 })
  const [errores, setErrores] = useState([])

  const handleSubir = useCallback(async (e) => {
    const file = e?.target?.files?.[0]
    if (!file || !empresaId) {
      toast.error('Selecciona una empresa y un archivo')
      return
    }
    setCargando(true)
    setErrores([])
    try {
      const data = await subirArchivoCargaMasiva(file, empresaId)
      setFilas(data.filas || [])
      setEmpresaIdArchivo(data.empresa_id)
      const conError = (data.filas || []).filter((f) => f._errores?.length > 0)
      if (conError.length > 0) {
        toast(`Se cargaron ${data.total} filas. ${conError.length} tienen errores de validación.`)
      } else {
        toast.success(`Se cargaron ${data.total} facturas para revisión`)
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Error al subir el archivo'
      toast.error(msg)
      setFilas([])
    } finally {
      setCargando(false)
      e.target.value = ''
    }
  }, [empresaId])

  const handleDescargarPlantilla = useCallback(async () => {
    setDescargando(true)
    try {
      await descargarPlantillaEjemplo()
      toast.success('Plantilla descargada')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al descargar')
    } finally {
      setDescargando(false)
    }
  }, [])

  const actualizarFila = useCallback((idx, campo, valor) => {
    setFilas((prev) => {
      const next = [...prev]
      if (!next[idx]) return next
      const f = { ...next[idx], [campo]: valor }
      if (campo === 'producto' && f.items?.length) {
        f.items = [...f.items]
        f.items[0] = { ...f.items[0], producto: valor }
      }
      if (campo === 'cantidad' && f.items?.length) {
        f.items = [...f.items]
        f.items[0] = { ...f.items[0], cantidad: Number(valor) || 1 }
      }
      if (campo === 'precio_unitario' && f.items?.length) {
        f.items = [...f.items]
        f.items[0] = { ...f.items[0], precio_unitario: Number(valor) || 0 }
      }
      if (f._errores?.length) f._errores = []
      next[idx] = f
      return next
    })
  }, [])

  const filasValidas = filas.filter((f) => !f._errores?.length)
  const filasInvalidas = filas.filter((f) => f._errores?.length > 0)

  const handleEmitir = useCallback(async () => {
    if (filasValidas.length === 0) {
      toast.error('No hay filas válidas para emitir. Corrige los errores en la tabla.')
      return
    }
    if (!empresaIdArchivo || !empresaId) {
      toast.error('Falta la empresa')
      return
    }
    setEmitiendo(true)
    setProgreso({ actual: 0, total: filasValidas.length })
    const fallidas = []
    let emitidas = 0
    for (let i = 0; i < filasValidas.length; i++) {
      const fila = filasValidas[i]
      setProgreso((p) => ({ ...p, actual: i }))
      try {
        const body = filaToPayload(fila, empresaIdArchivo)
        const { data } = await apiClient.post('/ventas/crear-con-detalles/', body, { timeout: 60000 })
        const rechazado = (data?.estado_dte || '').includes('Rechazado') || (data?.estado_dte || '').includes('Error')
        if (rechazado) {
          const mensaje = data?.mensaje || data?.observaciones_mh || 'Rechazado por Hacienda'
          fallidas.push({
            fila: fila._fila,
            mensaje,
            receptor_preview: data?.receptor_preview,
            dte_json_preview: data?.dte_json_preview,
          })
          setFilas((prev) =>
            prev.map((f) =>
              f === fila ? { ...f, _estado: 'error', _error_mensaje: mensaje } : f
            )
          )
        } else {
          emitidas++
          const ventaId = data?.id
          setFilas((prev) =>
            prev.map((f) =>
              f === fila ? { ...f, _estado: 'ok', _venta_id: ventaId } : f
            )
          )
        }
      } catch (err) {
        const d = err.response?.data
        const mensaje = d?.mensaje || d?.error || d?.detail
          || (typeof d === 'object' ? JSON.stringify(d) : err.message)
        fallidas.push({
          fila: fila._fila,
          mensaje,
          receptor_preview: d?.receptor_preview,
          dte_json_preview: d?.dte_json_preview,
        })
        setFilas((prev) =>
          prev.map((f) =>
            f === fila ? { ...f, _estado: 'error', _error_mensaje: mensaje } : f
          )
        )
      }
    }
    setProgreso({ actual: filasValidas.length, total: filasValidas.length })
    setEmitiendo(false)
    setErrores(fallidas)
    if (fallidas.length > 0) {
      toast.error(`${emitidas} emitidas. ${fallidas.length} fallaron. Revisa los detalles.`)
    } else {
      toast.success(`Se emitieron ${emitidas} facturas correctamente`)
    }
  }, [filasValidas, empresaIdArchivo, empresaId])

  if (!empresaId) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-amber-800">
          <p>Selecciona una empresa en el selector superior para usar la carga masiva.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-800">Carga Masiva de Facturas</h1>
        <p className="text-slate-600 text-sm mt-1">
          Sube un archivo Excel o CSV con las facturas a emitir. Valida y corrige antes de confirmar.
        </p>
      </div>

      {/* Acciones */}
      <div className="flex flex-wrap gap-3 mb-6">
        <label className="inline-flex items-center gap-2 px-4 py-2 bg-agil-primary text-white rounded-lg cursor-pointer hover:bg-agil-primary/90 transition-colors disabled:opacity-60">
          <Upload className="w-4 h-4" />
          {cargando ? 'Cargando...' : 'Subir archivo'}
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={handleSubir}
            disabled={cargando}
          />
        </label>
        <button
          type="button"
          onClick={handleDescargarPlantilla}
          disabled={descargando}
          className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-60"
        >
          {descargando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          Descargar plantilla de ejemplo
        </button>
      </div>

      {filas.length === 0 && (
        <div className="border-2 border-dashed border-slate-200 rounded-xl p-12 text-center text-slate-500">
          <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Sube un archivo Excel o CSV. Descarga la plantilla de ejemplo con todos los campos necesarios.</p>
          <p className="text-xs mt-2 text-slate-400">Soporta hasta 3 ítems por factura (producto_2, cantidad_2, precio_2, etc.)</p>
        </div>
      )}

      {filas.length > 0 && (
        <>
          <div className="mb-3 flex flex-wrap gap-4 text-sm text-slate-600">
            <span className="flex items-center gap-1.5">
              <span className="w-4 h-4 rounded bg-emerald-100 border border-emerald-200" />
              Producto en catálogo
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-4 h-4 rounded bg-amber-100 border border-amber-200" />
              Producto nuevo (se creó al importar)
            </span>
          </div>
          <div className="overflow-x-auto border border-slate-200 rounded-xl bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left p-2 font-medium">#</th>
                  <th className="text-left p-2 font-medium">Cliente / NRC</th>
                  <th className="text-left p-2 font-medium">Tipo</th>
                  <th className="text-left p-2 font-medium">Producto</th>
                  <th className="text-right p-2 font-medium">Cant.</th>
                  <th className="text-right p-2 font-medium">P.Unit.</th>
                  <th className="text-left p-2 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((fila, idx) => (
                  <tr
                    key={idx}
                    className={`border-b border-slate-100 last:border-0 ${
                      fila._errores?.length ? 'bg-red-50' : fila._estado === 'error' ? 'bg-red-50' : fila._estado === 'ok' ? 'bg-emerald-50' : ''
                    }`}
                  >
                    <td className="p-2 text-slate-500">{fila._fila}</td>
                    <td className="p-2">
                      <input
                        type="text"
                        value={fila.cliente ?? ''}
                        onChange={(e) => actualizarFila(idx, 'cliente', e.target.value)}
                        className="w-full max-w-[140px] border border-slate-200 rounded px-2 py-1 text-sm"
                      />
                    </td>
                    <td className="p-2">
                      <select
                        value={fila.tipo_dte ?? '01'}
                        onChange={(e) => actualizarFila(idx, 'tipo_dte', e.target.value)}
                        className="border border-slate-200 rounded px-2 py-1 text-sm"
                      >
                        <option value="01">01 - CF</option>
                        <option value="03">03 - CCF</option>
                      </select>
                    </td>
                    <td
                      className={`p-2 ${
                        fila._producto_reconocido === true
                          ? 'bg-emerald-50'
                          : fila._producto_reconocido === false
                            ? 'bg-amber-50'
                            : ''
                      }`}
                      title={
                        fila._producto_reconocido === true
                          ? 'Producto encontrado en catálogo'
                          : fila._producto_reconocido === false
                            ? 'Producto nuevo (se creó automáticamente)'
                            : ''
                      }
                    >
                      <input
                        type="text"
                        value={fila.producto ?? ''}
                        onChange={(e) => actualizarFila(idx, 'producto', e.target.value)}
                        className="w-full max-w-[180px] border border-slate-200 rounded px-2 py-1 text-sm bg-transparent"
                      />
                    </td>
                    <td className="p-2 text-right">
                      <input
                        type="number"
                        step="0.01"
                        min="0.01"
                        value={fila.cantidad ?? ''}
                        onChange={(e) => actualizarFila(idx, 'cantidad', e.target.value)}
                        className="w-20 border border-slate-200 rounded px-2 py-1 text-sm text-right"
                      />
                    </td>
                    <td className="p-2 text-right">
                      <input
                        type="number"
                        step="0.00000001"
                        min="0"
                        value={fila.precio_unitario ?? ''}
                        onChange={(e) => actualizarFila(idx, 'precio_unitario', e.target.value)}
                        className="w-24 border border-slate-200 rounded px-2 py-1 text-sm text-right"
                      />
                    </td>
                    <td className="p-2">
                      {fila._errores?.length ? (
                        <span className="text-red-600 flex items-center gap-1" title={fila._errores.join(', ')}>
                          <AlertCircle className="w-4 h-4 shrink-0" />
                          {fila._errores[0]}
                        </span>
                      ) : fila._estado === 'ok' ? (
                        <span className="text-emerald-600 flex items-center gap-1">
                          <CheckCircle2 className="w-4 h-4 shrink-0" />
                          Emitida
                        </span>
                      ) : fila._estado === 'error' ? (
                        <span className="text-red-600 text-xs" title={fila._error_mensaje}>
                          Error
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={handleEmitir}
              disabled={emitiendo || filasValidas.length === 0}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {emitiendo ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Emitiendo {progreso.actual}/{progreso.total}...
                </>
              ) : (
                'Confirmar y Emitir Todas'
              )}
            </button>
            {emitiendo && (
              <div className="flex-1 min-w-[120px] max-w-xs">
                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 transition-all duration-300"
                    style={{ width: `${progreso.total ? (progreso.actual / progreso.total) * 100 : 0}%` }}
                  />
                </div>
              </div>
            )}
            <span className="text-sm text-slate-500">
              {filasValidas.length} válidas, {filasInvalidas.length} con errores
            </span>
          </div>

          {errores.length > 0 && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <h3 className="font-medium text-red-800 mb-2">Facturas que fallaron ({errores.length})</h3>
              <ul className="text-sm text-red-700 space-y-3">
                {errores.map((e, i) => (
                  <li key={i} className="border-b border-red-100 pb-2 last:border-0">
                    <div><strong>Fila {e.fila}:</strong> {e.mensaje}</div>
                    {e.receptor_preview && (
                      <details className="mt-1">
                        <summary className="cursor-pointer text-red-600 hover:underline">Ver receptor enviado a MH</summary>
                        <pre className="mt-1 p-2 bg-white/80 rounded text-xs overflow-x-auto max-h-40 overflow-y-auto">
                          {JSON.stringify(e.receptor_preview, null, 2)}
                        </pre>
                      </details>
                    )}
                    {e.dte_json_preview && !e.receptor_preview && (
                      <details className="mt-1">
                        <summary className="cursor-pointer text-red-600 hover:underline">Ver JSON DTE enviado</summary>
                        <pre className="mt-1 p-2 bg-white/80 rounded text-xs overflow-x-auto max-h-60 overflow-y-auto">
                          {JSON.stringify(e.dte_json_preview, null, 2)}
                        </pre>
                      </details>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}
