import apiClient from './axios'
import { buildEmpresaPayload, needsEmpresaMultipart, empresaPayloadToFormData } from './empresaPayload'

const BASE = '/empresas'

/**
 * Lista todas las empresas (superusuario: todas; usuario normal: allowlist).
 * @returns {Promise<Array>}
 */
export async function listEmpresas() {
  const { data } = await apiClient.get(`${BASE}/`)
  return Array.isArray(data) ? data : data?.results ?? []
}

/**
 * Crea una nueva empresa integrada al SaaS.
 * @param {Object} rawPayload
 */
export async function createEmpresa(rawPayload) {
  const payload = buildEmpresaPayload(rawPayload)

  if (needsEmpresaMultipart(payload)) {
    const form = empresaPayloadToFormData(payload)
    const { data } = await apiClient.post(`${BASE}/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }

  const { data } = await apiClient.post(`${BASE}/`, payload)
  return data
}

/**
 * Elimina una empresa por ID.
 * @param {number|string} id
 */
export async function deleteEmpresa(id) {
  await apiClient.delete(`${BASE}/${id}/`)
}

/**
 * Estado modo prueba / online (ambiente MH).
 */
export async function getModoOperacion(empresaId) {
  const { data } = await apiClient.get(`${BASE}/${empresaId}/modo-operacion/`)
  return data
}

/**
 * Cambia modo: 'prueba' | 'online'. Online requiere confirmarReinicio.
 */
export async function cambiarModoOperacion(empresaId, modo, { confirmarReinicio = false } = {}) {
  const { data } = await apiClient.post(`${BASE}/${empresaId}/modo-operacion/`, {
    modo,
    confirmar_reinicio: confirmarReinicio,
  })
  return data
}
