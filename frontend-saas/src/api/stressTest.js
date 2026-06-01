import apiClient from './axios'
import { fechaHoyElSalvadorISO } from '../utils/format'
import { activarContingencia, procesarContingenciaCompleta } from './empresa'
import { getClientes } from './clientes'

export const STRESS_CONFIG = {
  FE_COUNT: 100,
  CCF_COUNT: 100,
  INVALIDATION_COUNT: 10,
  NC_COUNT: 50,
  CONTINGENCY_CYCLES: 5,
  CF_PER_CONTINGENCY: 2,
  /** Pausa entre bloques (FE → CCF → invalidaciones → NC). */
  PHASE_PAUSE_MS: 10000,
  /** Consulta estado MH (solo si quedó en cola async). */
  SELLO_POLL_INTERVAL_MS: 2000,
  SELLO_POLL_MAX_WAIT_MS: 600000,
  /** Reintentos automáticos si el backend responde throttled (429). */
  THROTTLE_RETRY_MAX: 20,
  /** Segundos extra tras el tiempo indicado por el servidor. */
  THROTTLE_BUFFER_MS: 3000,
}

/**
 * Cliente fijo para CCF/NC en la prueba de estrés.
 * Datos completos del receptor según ficha en el sistema (Francisco Jose Salamanca Gonzalez).
 */
export const STRESS_CLIENTE_CCF = {
  nombre: 'francisco José salamanca',
  nombre_comercial: 'francisco José salamanca',
  tipo_documento: 'NIT',
  documento_identidad: '047276888',
  nit: '047276888',
  dui: null,
  nrc: '2984414',
  correo: 'consumidor@AgilDTE.com',
  email_contacto: 'consumidor@AgilDTE.com',
  telefono: '78966925',
  departamento: '13',
  municipio: '22',
  direccion: '8 calle poniente poligono B10c casa 31, ciudada pacifica san miguel',
  cod_actividad: '70200',
  desc_actividad: 'Actividades de consultoría en gestión empresarial',
}

function companyHeaders(empresaId) {
  return { 'X-Company-ID': String(empresaId) }
}

function resolveReceptorCorreo(cliente) {
  const raw = cliente?.correo || cliente?.email_contacto || STRESS_CLIENTE_CCF.correo || ''
  const trimmed = String(raw).trim()
  // CharField del backend no acepta null; cadena vacía es válida (allow_blank).
  return trimmed || STRESS_CLIENTE_CCF.correo
}

function soloDigitos(val) {
  return String(val || '').replace(/\D/g, '')
}

/** Normaliza DUI/NIT/NRC como espera MH. El perfil STRESS prevalece sobre BD (evita NRC viejos erróneos). */
function normalizeClienteForMH(cliente) {
  const merged = { ...(cliente || {}), ...STRESS_CLIENTE_CCF }
  if (cliente?.id) merged.id = cliente.id

  const doc = soloDigitos(
    STRESS_CLIENTE_CCF.documento_identidad ||
      STRESS_CLIENTE_CCF.nit ||
      merged.documento_identidad ||
      merged.dui ||
      merged.nit
  )
  let tipo = String(STRESS_CLIENTE_CCF.tipo_documento || merged.tipo_documento || 'NIT').toUpperCase()
  let nit = null
  let dui = null

  if (doc.length === 9 || doc.length === 8) {
    const nit9 = doc.length === 8 ? `0${doc}` : doc
    tipo = 'NIT'
    nit = nit9
    dui = null
  } else if (doc.length >= 13) {
    tipo = 'NIT'
    nit = doc.length === 13 ? `0${doc}` : doc.slice(0, 14)
  } else if (doc) {
    tipo = doc.length <= 10 ? 'DUI' : 'NIT'
    if (tipo === 'DUI') dui = doc
    else nit = doc
  }

  const nrc = soloDigitos(STRESS_CLIENTE_CCF.nrc).slice(0, 8)
  const correo = String(
    STRESS_CLIENTE_CCF.correo || merged.correo || merged.email_contacto
  ).trim()

  return {
    ...merged,
    nombre: STRESS_CLIENTE_CCF.nombre,
    nombre_comercial: STRESS_CLIENTE_CCF.nombre_comercial,
    tipo_documento: tipo,
    documento_identidad: nit || dui || doc || STRESS_CLIENTE_CCF.documento_identidad,
    nit,
    dui,
    nrc,
    correo,
    email_contacto: correo,
    direccion: STRESS_CLIENTE_CCF.direccion,
    desc_actividad: STRESS_CLIENTE_CCF.desc_actividad,
    cod_actividad: STRESS_CLIENTE_CCF.cod_actividad,
    departamento: String(STRESS_CLIENTE_CCF.departamento).padStart(2, '0').slice(-2),
    municipio: String(STRESS_CLIENTE_CCF.municipio).padStart(2, '0').slice(-2),
    telefono: STRESS_CLIENTE_CCF.telefono,
  }
}

function mergeClienteStress(clienteApi) {
  return normalizeClienteForMH(clienteApi)
}

function matchClienteStress(c) {
  const nrc = soloDigitos(c?.nrc)
  const doc = soloDigitos(c?.documento_identidad || c?.nit || c?.dui || '')
  return (
    nrc === STRESS_CLIENTE_CCF.nrc ||
    doc === STRESS_CLIENTE_CCF.documento_identidad ||
    (c?.nombre || '').toLowerCase().includes('salamanca')
  )
}

function buildDetalle(cantidad, precioUnitario, esCF, docNumero) {
  const cant = Number(cantidad) || 1
  const prec = Number(precioUnitario) || 0
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
  return {
    cantidad: cant,
    descripcion_libre: `Ítem stress test #${docNumero}`,
    codigo_libre: null,
    precio_unitario: precioUnit,
    monto_descuento: 0,
    venta_no_sujeta: 0,
    venta_exenta: 0,
    venta_gravada: gravadaItem,
    iva_item: ivaItem,
    // MH: numItem correlativo dentro del documento (1, 2, 3…). Un ítem por DTE → siempre 1.
    numero_item: 1,
  }
}

function buildVentaBody({ empresaId, tipoDte, cliente, index, documentoRelacionadoId }) {
  const hoy = fechaHoyElSalvadorISO()
  const esCF = tipoDte === '01'
  const tipoVenta = esCF ? 'CF' : tipoDte === '03' ? 'CCF' : 'NC'
  const det = buildDetalle(1, esCF ? 11.3 : 10, esCF, index + 1)
  const ventaGravada = det.venta_gravada
  const debitoFiscal = det.iva_item

  const nrcDigits = esCF ? '' : soloDigitos(cliente?.nrc)
  const docDigits = esCF ? '' : soloDigitos(cliente?.documento_identidad || cliente?.nit || cliente?.dui)

  const body = {
    empresa: empresaId,
    tipo_dte: tipoDte,
    cliente_id: cliente?.id ?? null,
    cliente: esCF ? null : nrcDigits,
    nombre_receptor: esCF
      ? `Consumidor Final Stress ${index + 1}`
      : (cliente?.nombre || `Cliente Stress ${index + 1}`),
    fecha_emision: hoy,
    periodo_aplicado: hoy.slice(0, 7),
    tipo_venta: tipoVenta,
    nrc_receptor: esCF ? null : nrcDigits,
    venta_gravada: ventaGravada,
    venta_exenta: 0,
    venta_no_sujeta: 0,
    debito_fiscal: debitoFiscal,
    estado_dte: 'Generado',
    clase_documento: '4',
    clasificacion_venta: '1',
    tipo_ingreso: '3',
    condicion_operacion: 1,
    plazo_pago: null,
    periodo_pago: null,
    detalles: [det],
  }

  if (esCF) {
    // CharField del backend: allow_blank sí, allow_null no — nunca enviar null en CF.
    body.receptor_correo = ''
    body.receptor_direccion = ''
  } else {
    body.nombre_comercial_receptor = cliente?.nombre_comercial || cliente?.nombre || null
    body.nit_receptor = cliente?.nit || docDigits || null
    body.documento_receptor = docDigits
    body.tipo_doc_receptor = cliente?.tipo_documento || 'NIT'
    body.receptor_direccion = cliente?.direccion || STRESS_CLIENTE_CCF.direccion
    body.receptor_correo = resolveReceptorCorreo(cliente)
    body.receptor_departamento = cliente?.departamento || STRESS_CLIENTE_CCF.departamento
    body.receptor_municipio = cliente?.municipio || STRESS_CLIENTE_CCF.municipio
    body.receptor_telefono = cliente?.telefono || STRESS_CLIENTE_CCF.telefono
    body.cod_actividad_receptor = cliente?.cod_actividad || STRESS_CLIENTE_CCF.cod_actividad
    body.desc_actividad_receptor = cliente?.desc_actividad || STRESS_CLIENTE_CCF.desc_actividad
  }

  if (documentoRelacionadoId) {
    body.documento_relacionado_id = documentoRelacionadoId
  }

  return body
}

function extractError(err) {
  const d = err.response?.data
  if (!d) return err.message || 'Error desconocido'
  if (typeof d === 'string') return d
  if (d.mensaje) return d.mensaje
  if (d.error) return typeof d.error === 'string' ? d.error : JSON.stringify(d.error)
  if (d.detail) return typeof d.detail === 'string' ? d.detail : JSON.stringify(d.detail)
  const parts = Object.entries(d).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
  return parts.length ? parts.join(' · ') : err.message || 'Error desconocido'
}

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function parseThrottleWaitMs(message) {
  if (!message) return 35000
  const text = String(message)
  const esMatch = text.match(/(\d+)\s*segundos?/i)
  if (esMatch) return Number(esMatch[1]) * 1000
  const enMatch = text.match(/available in (\d+)/i)
  if (enMatch) return Number(enMatch[1]) * 1000
  return 35000
}

export function isThrottleError(err) {
  if (err?.response?.status === 429) return true
  const msg = extractError(err).toLowerCase()
  return msg.includes('throttl') || msg.includes('regulada') || msg.includes('rate limit')
}

export async function withThrottleRetry(fn, { onWait, maxRetries = STRESS_CONFIG.THROTTLE_RETRY_MAX } = {}) {
  let attempt = 0
  while (true) {
    try {
      return await fn()
    } catch (err) {
      if (!isThrottleError(err) || attempt >= maxRetries) throw err
      attempt += 1
      const waitMs = parseThrottleWaitMs(extractError(err)) + STRESS_CONFIG.THROTTLE_BUFFER_MS
      onWait?.(waitMs, attempt, extractError(err))
      await sleep(waitMs)
    }
  }
}

/**
 * Pausa con logs periódicos (respeta checkAbort si se pasa).
 */
export async function sleepWithProgress(ms, { label, onLog, checkAbort, chunkSec = 10 } = {}) {
  let remainingMs = ms
  const totalSec = Math.ceil(ms / 1000)
  onLog?.('warn', `[ESPERA] ${label} — ${totalSec}s…`)
  while (remainingMs > 0) {
    checkAbort?.()
    const chunkMs = Math.min(remainingMs, chunkSec * 1000)
    await sleep(chunkMs)
    remainingMs -= chunkMs
    if (remainingMs > 0) {
      onLog?.('info', `[ESPERA] ${label} — ${Math.ceil(remainingMs / 1000)}s restantes…`)
    }
  }
  onLog?.('info', `[CONTINÚA] ${label}`)
}

function isVentaOk(data) {
  const estado = (data?.estado_dte || '').toLowerCase()
  if (estado.includes('rechazado') || estado.includes('error')) return false
  return true
}

export async function getVentaStress(empresaId, ventaId) {
  const { data } = await apiClient.get(`ventas/${ventaId}/`, {
    headers: companyHeaders(empresaId),
  })
  return data
}

export function ventaProcesadaPorMH(venta) {
  const sello = String(venta?.sello_recepcion || '').trim()
  if (sello) return true
  return (venta?.estado_dte || '').trim() === 'AceptadoMH'
}

/** Durante contingencia activa el backend deja la venta en PendienteEnvio (sin sello hasta el cierre). */
export function ventaRegistradaEnContingencia(venta) {
  if (venta?.procesamiento === 'contingencia') return true
  const estado = (venta?.estado_dte || '').trim()
  return estado === 'PendienteEnvio' && !String(venta?.sello_recepcion || '').trim()
}

export function ventaFallidaMH(venta) {
  const estado = (venta?.estado_dte || '').trim()
  return ['RechazadoMH', 'ErrorEnvio', 'Anulado'].includes(estado)
}

function mensajeEstadoVenta(venta) {
  return (
    venta?.mensaje ||
    venta?.error_envio_mensaje ||
    venta?.observaciones_mh ||
    venta?.estado_dte ||
    'sin detalle'
  )
}

/**
 * Espera selloRecibido de un solo documento (modo carga masiva: emitir → sello → siguiente).
 */
export async function esperarSelloVenta(empresaId, venta, options = {}) {
  if (!venta?.id) return venta
  if (ventaProcesadaPorMH(venta)) return venta

  const {
    onLog,
    checkAbort,
    label = `venta ${venta.id}`,
    maxWaitMs = STRESS_CONFIG.SELLO_POLL_MAX_WAIT_MS,
    pollIntervalMs = STRESS_CONFIG.SELLO_POLL_INTERVAL_MS,
  } = options

  if (venta.procesamiento === 'asincrono') {
    onLog?.('info', `[MH] Documento en cola — esperando selloRecibido (${label})…`)
  }

  const deadline = Date.now() + maxWaitMs
  let polls = 0
  while (true) {
    checkAbort?.()
    if (Date.now() > deadline) {
      throw new Error(`Tiempo agotado esperando selloRecibido de MH para ${label}`)
    }

    if (polls > 0) {
      await sleep(pollIntervalMs)
    }

    const fresh = await getVentaStress(empresaId, venta.id).catch(() => null)
    if (fresh) {
      if (ventaProcesadaPorMH(fresh)) {
        return { ...venta, ...fresh }
      }
      if (ventaFallidaMH(fresh)) {
        throw new Error(`${label}: ${fresh.estado_dte} — ${mensajeEstadoVenta(fresh)}`)
      }
    }

    polls += 1
    onLog?.(
      'warn',
      `[MH] ${label} sin sello (${fresh?.estado_dte || 'consultando'}) — reintento ${polls} en ${pollIntervalMs / 1000}s…`
    )
  }
}

/**
 * Emite un DTE y espera selloRecibido antes de devolver (igual que carga masiva, uno a uno).
 */
export async function emitirDocumentoStressConSello(empresaId, params, options = {}) {
  const { selloLabel, onLog, checkAbort, onWait } = options
  const label =
    selloLabel ||
    `DTE ${params.tipoDte} #${String((params.index ?? 0) + 1).padStart(params.tipoDte === '01' ? 4 : 2, '0')}`

  const data = await emitirDocumentoStress(empresaId, params, { onWait })
  if (ventaProcesadaPorMH(data)) return data

  if (ventaFallidaMH(data)) {
    throw new Error(`${label}: ${data.estado_dte} — ${mensajeEstadoVenta(data)}`)
  }

  if (data.procesamiento === 'sincrono') {
    throw new Error(`${label}: MH no devolvió sello en emisión síncrona — ${mensajeEstadoVenta(data)}`)
  }

  return esperarSelloVenta(empresaId, data, { onLog, checkAbort, label })
}

/**
 * Emite CF/CCF durante contingencia: no espera sello (MH lo entrega al cerrar el evento F05).
 */
export async function emitirDocumentoStressContingencia(empresaId, params, options = {}) {
  const { selloLabel, onLog, onWait } = options
  const label =
    selloLabel ||
    `CF contingencia #${String((params.index ?? 0) + 1).padStart(2, '0')}`

  const data = await emitirDocumentoStress(empresaId, params, { onWait })

  if (ventaRegistradaEnContingencia(data)) {
    onLog?.(
      'ok',
      `[OK] ${label} registrado (${data.numero_control || `id ${data.id}`}) — PendienteEnvio hasta cierre F05`
    )
    return data
  }

  if (ventaProcesadaPorMH(data)) {
    onLog?.('ok', `[OK] ${label} — sello: ${data.sello_recepcion || '—'}`)
    return data
  }

  if (ventaFallidaMH(data)) {
    throw new Error(`${label}: ${data.estado_dte} — ${mensajeEstadoVenta(data)}`)
  }

  throw new Error(`${label}: estado inesperado (${data.estado_dte || '—'}) — ${mensajeEstadoVenta(data)}`)
}

/**
 * Tras procesar-contingencia-completa: valida F05 RECIBIDO y confirma sellos de CF pendientes.
 */
export async function confirmarEnvioPostContingencia(empresaId, emitidas, resultado, options = {}) {
  const { onLog, checkAbort } = options
  const evento = resultado?.resultado_contingencia || {}
  const resumen = resultado?.resumen_envio

  const estadoF05 = String(evento.estado || '').trim()
  if (estadoF05 && estadoF05 !== 'RECIBIDO') {
    throw new Error(`F05 contingencia rechazado por MH: ${evento.mensaje || estadoF05}`)
  }

  const selloF05 = evento.sello_recibido || evento.selloRecibido || ''
  onLog?.(
    'ok',
    `[OK F05] Evento contingencia RECIBIDO${selloF05 ? ` — sello: ${selloF05}` : ''}`
  )

  const idsSet = new Set(emitidas.map((v) => v?.id).filter(Boolean))

  if (resumen) {
    const detallesCiclo = (resumen.detalles || []).filter((d) => idsSet.has(d.venta_id))
    const aceptadasCiclo = detallesCiclo.filter((d) => d.estado_dte === 'AceptadoMH').length
    const rechazadasCiclo = detallesCiclo.filter((d) => d.estado_dte === 'RechazadoMH').length
    const erroresCiclo = detallesCiclo.filter(
      (d) => d.estado_dte !== 'AceptadoMH' && d.estado_dte !== 'RechazadoMH'
    ).length

    onLog?.(
      'info',
      `[MH] Envío post-cierre (este ciclo): ${aceptadasCiclo}/${idsSet.size} aceptadas · ${rechazadasCiclo} rechazadas · ${erroresCiclo} errores`
    )
    if (resultado?.ventas_excluidas > 0) {
      onLog?.(
        'warn',
        `[MH] ${resultado.ventas_excluidas} PendienteEnvio antiguo(s) excluido(s) del F05 (no pertenecen a este ciclo).`
      )
    }

    const fallos = detallesCiclo.filter((d) => d.estado_dte !== 'AceptadoMH')
    if (fallos.length > 0) {
      const msg = fallos
        .map((d) => `#${d.venta_id}: ${d.estado_dte}${d.mensaje ? ` — ${d.mensaje}` : ''}`)
        .join('; ')
      throw new Error(`Fallo en envío post-contingencia: ${msg || 'ver resumen_envio'}`)
    }
  }

  const ids = emitidas.map((v) => v?.id).filter(Boolean)
  if (!ids.length) return emitidas

  onLog?.('info', `[MH] Confirmando selloRecibido en ${ids.length} CF tras cierre de contingencia…`)

  const refreshed = await Promise.all(
    ids.map(async (id) => {
      const original = emitidas.find((v) => v.id === id) || { id }
      const fresh = await getVentaStress(empresaId, id).catch(() => null)
      return fresh ? { ...original, ...fresh } : original
    })
  )

  for (const v of refreshed) {
    if (ventaProcesadaPorMH(v)) {
      onLog?.('ok', `[OK] CF ${v.numero_control || v.id} — sello: ${v.sello_recepcion || '—'}`)
    } else if (ventaFallidaMH(v)) {
      throw new Error(`CF ${v.numero_control || v.id}: ${v.estado_dte} — ${mensajeEstadoVenta(v)}`)
    }
  }

  const pendientes = refreshed.filter((v) => !ventaProcesadaPorMH(v) && !ventaFallidaMH(v))
  if (pendientes.length === 0) return refreshed

  return esperarSellosVentas(empresaId, refreshed, {
    ...options,
    label: 'CF contingencia',
  })
}

/**
 * Espera hasta que todas las ventas tengan selloRecibido / AceptadoMH.
 */
export async function esperarSellosVentas(empresaId, ventas, options = {}) {
  const ids = [...new Set(ventas.map((v) => v?.id).filter(Boolean))]
  if (!ids.length) return ventas

  const {
    onLog,
    checkAbort,
    label = 'documentos',
    maxWaitMs = STRESS_CONFIG.SELLO_POLL_MAX_WAIT_MS,
    pollIntervalMs = STRESS_CONFIG.SELLO_POLL_INTERVAL_MS,
  } = options

  const deadline = Date.now() + maxWaitMs
  const pending = new Set(ids)
  const updated = new Map(ventas.filter((v) => v?.id).map((v) => [v.id, v]))

  onLog?.('info', `[MH] Esperando selloRecibido en ${pending.size} ${label}…`)

  while (pending.size > 0) {
    checkAbort?.()
    if (Date.now() > deadline) {
      throw new Error(
        `Tiempo agotado: ${pending.size} ${label} siguen sin selloRecibido de MH. Espere y reintente la fase.`
      )
    }

    const snapshots = await Promise.all(
      [...pending].map((id) => getVentaStress(empresaId, id).catch(() => null))
    )

    for (const fresh of snapshots) {
      if (!fresh?.id) continue
      if (ventaProcesadaPorMH(fresh)) {
        updated.set(fresh.id, { ...updated.get(fresh.id), ...fresh })
        pending.delete(fresh.id)
      }
    }

    if (pending.size > 0) {
      onLog?.(
        'warn',
        `[MH] ${pending.size} ${label} sin sello — nueva consulta en ${pollIntervalMs / 1000}s…`
      )
      await sleep(pollIntervalMs)
    }
  }

  onLog?.('ok', `[OK MH] ${ids.length} ${label} con selloRecibido — listos para continuar.`)
  return ventas.map((v) => (v?.id ? updated.get(v.id) || v : v))
}

/**
 * Emite y firma un DTE (FE, CCF o NC) para la empresa indicada.
 */
export async function emitirDocumentoStress(empresaId, { tipoDte, cliente, index, documentoRelacionadoId }, options = {}) {
  const { onWait } = options
  return withThrottleRetry(async () => {
    const body = buildVentaBody({ empresaId, tipoDte, cliente, index, documentoRelacionadoId })
    const { data } = await apiClient.post('/ventas/crear-con-detalles/', body, {
      headers: {
        ...companyHeaders(empresaId),
        'X-Facturacion-Sincrona': 'true',
      },
      timeout: 120000,
    })
    if (!isVentaOk(data)) {
      throw new Error(data?.mensaje || data?.observaciones_mh || 'Documento rechazado por MH')
    }
    return data
  }, { onWait })
}

/**
 * Invalida un DTE ya procesado por MH.
 */
export async function invalidarDocumentoStress(empresaId, venta, empresa, options = {}) {
  const { onWait } = options
  return withThrottleRetry(async () => {
    const payload = {
      motivoInvalidacion: 'Prueba automatizada de estrés — invalidación de documento',
      tipoInvalidacion: 'Rescisión',
      nombreResponsable: empresa?.nombre || 'Responsable Stress Test',
      tipoDocResponsable: 'NIT',
      numeroDocResponsable: (empresa?.nit || '').replace(/-/g, '') || '06140101011011',
      nombreSolicitante: empresa?.nombre || 'Solicitante Stress Test',
      tipoDocSolicitante: 'NIT',
      numeroDocSolicitante: (empresa?.nit || '').replace(/-/g, '') || '06140101011011',
    }
    const { data } = await apiClient.post(`ventas/${venta.id}/invalidar/`, payload, {
      headers: companyHeaders(empresaId),
      timeout: 120000,
    })
    return data
  }, { onWait })
}

/**
 * Emite NC referenciando un CCF emitido.
 */
export async function emitirNotaCreditoStress(empresaId, ccfVenta, cliente, index, options = {}) {
  const codigo = ccfVenta.codigo_generacion
  if (!codigo) throw new Error('CCF sin código de generación para NC')
  return emitirDocumentoStressConSello(
    empresaId,
    {
      tipoDte: '05',
      cliente,
      index,
      documentoRelacionadoId: codigo,
    },
    {
      ...options,
      selloLabel: `NC #${String(index + 1).padStart(2, '0')} sobre CCF ${ccfVenta.numero_control || ccfVenta.id}`,
    }
  )
}

/**
 * Resuelve el cliente CCF/NC: busca en BD y fusiona con STRESS_CLIENTE_CCF (perfil fijo).
 */
export async function obtenerClienteStress(empresaId) {
  const clientes = await getClientes({ empresa_id: empresaId })
  const match = clientes.find(matchClienteStress)
  if (match) return mergeClienteStress(match)

  const conDocumento = clientes.filter((c) => c.nrc || c.nit || c.documento_identidad)
  if (conDocumento.length) return mergeClienteStress(conDocumento[0])

  return { ...STRESS_CLIENTE_CCF }
}

/**
 * Ciclo completo de contingencia: activar → CF sin sello → F05 + envío pendientes → confirmar sellos.
 */
export async function ejecutarCicloContingenciaStress(empresaId, cicloIndex, onLog, options = {}) {
  onLog?.(`Ciclo ${cicloIndex + 1}: abriendo evento de contingencia…`)
  const activacion = await activarContingencia(empresaId, {
    tipoContingencia: 1,
    motivo: `Stress test — ciclo de contingencia ${cicloIndex + 1}`,
  })

  const previos = activacion?.pendientes_previos ?? 0
  if (previos > 0) {
    onLog?.(
      'warn',
      `Hay ${previos} documento(s) PendienteEnvio de sesiones anteriores; el cierre solo procesará los CF de este ciclo.`
    )
  }

  const emitidas = []
  for (let i = 0; i < STRESS_CONFIG.CF_PER_CONTINGENCY; i++) {
    onLog?.(
      `Ciclo ${cicloIndex + 1}: emitiendo CF contingencia ${i + 1}/${STRESS_CONFIG.CF_PER_CONTINGENCY} (sin esperar sello)…`
    )
    const data = await emitirDocumentoStressContingencia(
      empresaId,
      {
        tipoDte: '01',
        cliente: null,
        index: cicloIndex * 10 + i,
      },
      {
        ...options,
        onLog,
        selloLabel: `CF contingencia ciclo ${cicloIndex + 1} #${i + 1}`,
      }
    )
    emitidas.push(data)
  }

  const ventaIds = emitidas.map((v) => v.id).filter(Boolean)
  onLog?.(
    `Ciclo ${cicloIndex + 1}: cerrando contingencia — F05 a MH y envío de ${ventaIds.length} CF de este ciclo…`
  )
  const resultado = await procesarContingenciaCompleta(empresaId, {
    tipoContingencia: 1,
    motivo: `Stress test — cierre ciclo ${cicloIndex + 1}`,
    venta_ids: ventaIds,
  })

  const confirmadas = await confirmarEnvioPostContingencia(empresaId, emitidas, resultado, {
    ...options,
    onLog,
  })

  return { emitidas: confirmadas, resultado }
}

export { extractError, isVentaOk }
