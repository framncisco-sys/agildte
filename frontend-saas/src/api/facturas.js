import apiClient from './axios'

/**
 * Mapea datos del formulario frontend al payload que espera Django.
 * Backend: POST /api/ventas/crear-con-detalles/
 */
function mapearPayloadFrontendADjango(payload) {
  const { cliente, items, tipoDocumento, totalGravadas, iva, ivaRetenido1, condicionOperacion, plazoPago, periodoPago } = payload
  const empresaId = payload.empresaId // desde useEmpresaStore
  const hoy = new Date().toISOString().slice(0, 10)
  const fechaEmisionFinal = payload.fechaFacturacion || hoy
  const periodo = String(fechaEmisionFinal).slice(0, 7) // YYYY-MM

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

  // Consumidor Final (01): el precio ingresado ya incluye IVA. Desglose: Monto Gravado = Total/1.13
  const esCF = tipoDocumento === '01'
  const aplicaIVA = ['03', '05', '06'].includes(tipoDocumento)

  let ventaGravada, debitoFiscal
  if (esCF) {
    const totalConIva = Math.round((totalGravadas ?? 0) * 100) / 100
    ventaGravada = Math.round((totalConIva / 1.13) * 100) / 100
    debitoFiscal = Math.round((totalConIva - ventaGravada) * 100) / 100
  } else {
    ventaGravada = Math.round((totalGravadas ?? 0) * 100) / 100
    debitoFiscal = Math.round((iva ?? 0) * 100) / 100
  }

  const docRel = payload.documentoRelacionado
  const documentoRelacionadoId = docRel?.codigoGeneracion || null

  const detalles = (items || []).map((it, idx) => {
    const cant = Number(it.cantidad) || 0
    const precio = Number(it.precioUnitario) || 0
    const totalLinea = cant * precio
    let gravada, ivaItem
    if (esCF) {
      gravada = Math.round((totalLinea / 1.13) * 100) / 100
      ivaItem = Math.round((totalLinea - gravada) * 100) / 100
    } else {
      gravada = totalLinea
      ivaItem = aplicaIVA ? Math.round(gravada * 0.13 * 100) / 100 : 0
    }
    return {
      cantidad: cant,
      descripcion_libre: it.descripcion || null,
      codigo_libre: null,
      precio_unitario: esCF ? Math.round((gravada / cant) * 100) / 100 : precio,
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
    fecha_emision: fechaEmisionFinal,
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
    iva_retenido_1: ivaRetenido1 ?? 0,
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
 * Lista ventas con filtros opcionales y paginación server-side.
 * @param {Object} filters - { fecha_inicio, fecha_fin, search, tipo_dte, empresa_id, periodo, tipo, solo_procesadas, page, page_size }
 * @returns {Promise<{ count, total_pages, page, page_size, has_next, has_previous, results }>}
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
  params.append('page', filters.page ?? 1)
  params.append('page_size', filters.page_size ?? 20)

  const { data } = await apiClient.get(`/ventas/listar/?${params.toString()}`)
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
 * Descarga un ZIP con los PDFs (o JSONs DTE) de las facturas que cumplen los filtros actuales.
 * Backend: GET /api/facturas/descarga-zip/?format=pdf|json&...
 *
 * @param {Object} filters - { fecha_inicio, fecha_fin, search, tipo_dte, empresa_id }
 * @param {'pdf'|'json'} format - Contenido del ZIP
 */
export async function downloadFacturasFiltradasZip(filters = {}, format = 'pdf') {
  const params = new URLSearchParams()
  params.append('format', format)
  if (filters.fecha_inicio) params.append('fecha_inicio', filters.fecha_inicio)
  if (filters.fecha_fin) params.append('fecha_fin', filters.fecha_fin)
  if (filters.search) params.append('search', filters.search)
  if (filters.tipo_dte) params.append('tipo_dte', filters.tipo_dte)
  if (filters.empresa_id) params.append('empresa_id', filters.empresa_id)

  const qs = params.toString()
  try {
    // Misma base que getVentas: baseURL del cliente (/api o http://host/api) + facturas/descarga-zip/
    const { data } = await apiClient.get(`facturas/descarga-zip/?${qs}`, {
      responseType: 'blob',
    })
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
      const trimmed = text.trim()
      let parsed = null
      try {
        parsed = JSON.parse(trimmed)
      } catch {
        // Respuesta no JSON (p. ej. traza Python "AssertionError: ..." o HTML de error 500)
      }
      if (parsed && typeof parsed === 'object') {
        if (parsed.error) throw new Error(parsed.error)
        if (parsed.detail) {
          const d = parsed.detail
          throw new Error(typeof d === 'string' ? d : JSON.stringify(d))
        }
      }
      if (trimmed.startsWith('<!DOCTYPE') || trimmed.toLowerCase().startsWith('<html')) {
        throw new Error(
          'El servidor devolvió una página de error. Revisa los logs del backend o el modo DEBUG.'
        )
      }
      throw new Error(trimmed.slice(0, 500) || 'Error al descargar el lote')
    }
    throw err
  }
}

/** Alias retrocompatible */
export const downloadBatch = downloadFacturasFiltradasZip

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
