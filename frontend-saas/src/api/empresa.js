import apiClient from './axios'

/**
 * Obtiene los datos de una empresa por ID.
 */
export async function getEmpresa(id) {
  const { data } = await apiClient.get(`/empresas/${id}/`)
  return data
}

/**
 * Actualiza una empresa. Si se pasa `logo` (File), envía multipart/form-data.
 */
export async function updateEmpresa(id, payload) {
  const logo = payload.logo
  const isMultipart = logo instanceof File

  if (isMultipart) {
    const form = new FormData()
    const keys = Object.keys(payload).filter((k) => k !== 'logo' && payload[k] !== undefined && payload[k] !== null)
    keys.forEach((k) => form.append(k, payload[k]))
    form.append('logo', logo)
    const { data } = await apiClient.patch(`/empresas/${id}/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }

  const { logo_url, ...rest } = payload
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
