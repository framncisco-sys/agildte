import apiClient from './axios'

/**
 * Mapea datos del formulario frontend al payload que espera Django.
 * Backend: POST /api/ventas/crear-con-detalles/
 */
function mapearPayloadFrontendADjango(payload) {
  const { cliente, items, tipoDocumento, totalGravadas, iva, condicionOperacion, plazoPago, periodoPago } = payload
  const empresaId = payload.empresaId // desde useEmpresaStore
  const hoy = new Date().toISOString().slice(0, 10)
  const periodo = new Date().toISOString().slice(0, 7) // YYYY-MM

  // tipoDocumento: '01'=CF, '03'=CCF, '05'=NC, '06'=ND, '14'=FSE, '07'=CCF
  const tipoVentaMap = { '01': 'CF', '03': 'CCF', '05': 'NC', '06': 'ND', '14': 'FSE', '07': 'CCF' }
  const tipoVenta = tipoVentaMap[tipoDocumento] ?? 'CCF'
  const esFSE = tipoDocumento === '14'

  // CF y FSE: usar datos manuales del form (nombreCompleto, documento, direccion, correo)
  const nombreReceptor = (tipoVenta === 'CF' || esFSE)
    ? (cliente?.nombreCompleto?.trim() || (esFSE ? 'Proveedor Sujeto Excluido' : 'Consumidor Final'))
    : (cliente?.nombreCompleto ?? '')
  const nrcReceptor = (tipoVenta === 'CF' || esFSE) ? null : (cliente?.numeroDocumento ?? '')
  const documentoReceptor = (tipoVenta === 'CF' || esFSE)
    ? (cliente?.numeroDocumento?.trim() || null)
    : null
  const tipoDocReceptor = cliente?.tipoDocCliente ?? 'NIT'

  const ventaGravada = Math.round((totalGravadas ?? 0) * 100) / 100
  const debitoFiscal = Math.round((iva ?? 0) * 100) / 100

  const docRel = payload.documentoRelacionado
  const documentoRelacionadoId = docRel?.codigoGeneracion || null

  const detalles = (items || []).map((it, idx) => {
    const cant = Number(it.cantidad) || 0
    const precio = Number(it.precioUnitario) || 0
    const gravada = cant * precio
    const aplicaIVA = ['03', '05', '06'].includes(tipoDocumento)
    const ivaItem = aplicaIVA ? Math.round(gravada * 0.13 * 100) / 100 : 0
    return {
      cantidad: cant,
      descripcion_libre: it.descripcion || null,
      codigo_libre: null,
      precio_unitario: precio,
      monto_descuento: 0,
      venta_no_sujeta: 0,
      venta_exenta: 0,
      venta_gravada: gravada,
      iva_item: ivaItem,
      numero_item: idx + 1,
    }
  })

  // Para CCF: priorizar NRC del formulario (nrc del cliente en form > nrcReceptor derivado del NIT)
  const nrcFinal = tipoVenta === 'CCF' ? (cliente?.nrc?.trim() || nrcReceptor || null) : null

  const body = {
    empresa: empresaId,
    tipo_dte: tipoDocumento,
    cliente_id: payload.clienteId ?? null,
    nombre_receptor: nombreReceptor,
    documento_receptor: documentoReceptor,
    tipo_doc_receptor: tipoDocReceptor,
    receptor_direccion: cliente?.direccion?.trim() || null,
    receptor_correo: cliente?.correo?.trim() || null,
    fecha_emision: hoy,
    periodo_aplicado: periodo,
    tipo_venta: tipoVenta,
    nrc_receptor: nrcFinal,
    venta_gravada: ventaGravada,
    venta_exenta: 0,
    venta_no_sujeta: 0,
    debito_fiscal: debitoFiscal,
    estado_dte: 'Generado',
    clase_documento: '4',
    clasificacion_venta: '1',
    tipo_ingreso: '3',
    condicion_operacion: Number(condicionOperacion ?? cliente?.condicionOperacion ?? 1),
    plazo_pago: plazoPago ?? null,
    periodo_pago: periodoPago ?? null,
    cod_actividad_receptor: cliente?.codActividad?.trim() || null,
    desc_actividad_receptor: cliente?.descActividad?.trim() || null,
    detalles,
  }
  if (documentoRelacionadoId) {
    body.documento_relacionado_id = documentoRelacionadoId
  }
  return body
}

/**
 * Crea una venta con detalles y genera el DTE.
 * @param {Object} payload - Datos del formulario (cliente, items, tipoDocumento, totalGravadas, iva, empresaId)
 * @returns {Promise<{data}>}
 */
export async function crearVenta(payload) {
  const body = mapearPayloadFrontendADjango(payload)
  const { data } = await apiClient.post('/ventas/crear-con-detalles/', body)
  return data
}

/**
 * Lista ventas con filtros opcionales.
 * @param {Object} filters - { fecha_inicio, fecha_fin, search, tipo_dte, empresa_id, periodo, tipo, solo_procesadas }
 * @returns {Promise<Array>}
 */
export async function getVentas(filters = {}) {
  const params = new URLSearchParams()
  if (filters.fecha_inicio) params.append('fecha_inicio', filters.fecha_inicio)
  if (filters.fecha_fin) params.append('fecha_fin', filters.fecha_fin)
  if (filters.search) params.append('search', filters.search)
  if (filters.tipo_dte) params.append('tipo_dte', filters.tipo_dte)
  if (filters.empresa_id) params.append('empresa_id', filters.empresa_id)
  if (filters.periodo) params.append('periodo', filters.periodo)
  if (filters.tipo) params.append('tipo', filters.tipo)
  if (filters.solo_procesadas) params.append('solo_procesadas', '1')

  const qs = params.toString()
  const url = qs ? `/ventas/listar/?${qs}` : '/ventas/listar/'
  const { data } = await apiClient.get(url)
  return data
}

/**
 * Descarga el PDF de una factura.
 * @param {number} id - ID de la venta
 * @param {string} filename - Nombre sugerido para el archivo
 */
export async function downloadPDF(id, filename = 'factura.pdf') {
  const { data } = await apiClient.get(`ventas/${id}/generar-pdf/`, {
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

/**
 * Descarga el JSON DTE firmado de una factura.
 * @param {number} id - ID de la venta
 * @param {string} filename - Nombre sugerido para el archivo
 */
export async function downloadJSON(id, filename) {
  const { data } = await apiClient.get(`ventas/${id}/generar-dte/`)
  const jsonStr = JSON.stringify(data.dte_json || data, null, 2)
  const blob = new Blob([jsonStr], { type: 'application/json' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename || `dte_${id}.json`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

/**
 * Descarga PDFs o JSONs de ventas filtradas en un archivo ZIP.
 * @param {Object} filters - { fecha_inicio, fecha_fin, search, tipo_dte, empresa_id }
 * @param {'pdf'|'json'} format - Tipo de archivos a descargar
 */
export async function downloadBatch(filters = {}, format = 'pdf') {
  const params = new URLSearchParams()
  params.append('format', format)
  if (filters.fecha_inicio) params.append('fecha_inicio', filters.fecha_inicio)
  if (filters.fecha_fin) params.append('fecha_fin', filters.fecha_fin)
  if (filters.search) params.append('search', filters.search)
  if (filters.tipo_dte) params.append('tipo_dte', filters.tipo_dte)
  if (filters.empresa_id) params.append('empresa_id', filters.empresa_id)

  const url = `ventas/descargar-lote/?${params.toString()}`
  try {
    const { data } = await apiClient.get(url, { responseType: 'blob' })
    const blob = new Blob([data], { type: 'application/zip' })
    const urlObj = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = urlObj
    link.setAttribute('download', `facturas_${format}.zip`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(urlObj)
  } catch (err) {
    if (err.response?.data instanceof Blob) {
      const text = await err.response.data.text()
      try {
        const j = JSON.parse(text)
        if (j.error) throw new Error(j.error)
      } catch (e) {
        if (e instanceof Error && e.message !== err.message) throw e
      }
    }
    throw err
  }
}

/**
 * Reenvía una factura pendiente de forma síncrona.
 * Espera la respuesta de MH para mostrar errores (contraseña, rechazo, etc.).
 * @param {number} id - ID de la venta
 * @returns {Promise<{data}>} - { mensaje, exito, estado, ... } o error con mensaje
 */
export async function reenviarVenta(id) {
  const { data } = await apiClient.post(`ventas/${id}/reenviar/`, {}, { timeout: 60000 })
  return data
}

/**
 * Invalida (anula) un DTE ya procesado por MH.
 * @param {number} id - ID de la venta
 * @param {Object} datos - { motivoInvalidacion, tipoInvalidacion, nombreResponsable, tipoDocResponsable, numeroDocResponsable, nombreSolicitante, tipoDocSolicitante, numeroDocSolicitante }
 * @returns {Promise<{data}>}
 */
export async function invalidarVenta(id, datos) {
  const { data } = await apiClient.post(`ventas/${id}/invalidar/`, datos)
  return data
}
