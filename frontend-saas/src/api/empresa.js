import apiClient from './axios'
import { buildEmpresaPayload, needsEmpresaMultipart, empresaPayloadToFormData } from './empresaPayload'

/**
 * Obtiene los datos de una empresa por ID.
 */
export async function getEmpresa(id) {
  const { data } = await apiClient.get(`/empresas/${id}/`)
  return data
}

/**
 * Actualiza una empresa. Soporta logo y certificado (.crt) vía multipart.
 */
export async function updateEmpresa(id, rawPayload) {
  const payload = buildEmpresaPayload(rawPayload)

  if (needsEmpresaMultipart(payload)) {
    const form = empresaPayloadToFormData(payload)
    const { data } = await apiClient.patch(`/empresas/${id}/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }

  const { logo, archivo_certificado, logo_url, certificado_nombre, ...rest } = payload
  const { data } = await apiClient.patch(`/empresas/${id}/`, rest)
  return data
}

/**
 * Obtiene los correlativos del año actual (siguiente número por tipo DTE).
 */
export async function getCorrelativos(empresaId) {
  const { data } = await apiClient.get(`/empresas/${empresaId}/correlativos/`)
  return data
}

/**
 * Actualiza el siguiente número correlativo por tipo DTE.
 * Ej: { "01": 25, "03": 35 } = CF próxima 25, CCF próxima 35.
 */
export async function updateCorrelativos(empresaId, payload) {
  const { data } = await apiClient.patch(`/empresas/${empresaId}/correlativos/`, payload)
  return data
}

/**
 * Activa la contingencia MH para una empresa.
 * Body opcional: { tipoContingencia, motivo }
 */
export async function activarContingencia(empresaId, payload = {}) {
  const { data } = await apiClient.post(`/empresas/${empresaId}/activar-contingencia/`, payload)
  return data
}

/**
 * Desactiva la contingencia MH y encola las ventas pendientes.
 * Body opcional: { tipoContingencia, motivo } para ajustar el reporte.
 */
export async function desactivarContingencia(empresaId, payload = {}) {
  const { data } = await apiClient.post(`/empresas/${empresaId}/desactivar-contingencia/`, payload)
  return data
}

/**
 * Procesa la contingencia completa:
 * 1) Genera y envía el reporte de contingencia.
 * 2) Envía todas las facturas en PendienteEnvio y devuelve un resumen.
 */
export async function procesarContingenciaCompleta(empresaId, payload = {}) {
  const { data } = await apiClient.post(`/empresas/${empresaId}/procesar-contingencia-completa/`, payload, { timeout: 600000 })
  return data
}
