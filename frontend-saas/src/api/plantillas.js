import apiClient from './axios'

/**
 * Lista plantillas de facturación rápida para una empresa.
 * @param {{ empresa_id?: number, search?: string }} params
 */
export async function listarPlantillas(params = {}) {
  const qs = new URLSearchParams()
  if (params.empresa_id) qs.append('empresa_id', params.empresa_id)
  if (params.search) qs.append('search', params.search)
  const url = qs.toString() ? `/plantillas-factura/?${qs.toString()}` : '/plantillas-factura/'
  const { data } = await apiClient.get(url)
  return data
}

/**
 * Crea una nueva plantilla de factura rápida.
 */
export async function crearPlantilla(payload) {
  const { data } = await apiClient.post('/plantillas-factura/crear/', payload)
  return data
}

/**
 * Obtiene el detalle de una plantilla.
 */
export async function obtenerPlantilla(id) {
  const { data } = await apiClient.get(`/plantillas-factura/${id}/`)
  return data
}

/**
 * Actualiza una plantilla existente.
 */
export async function actualizarPlantilla(id, payload) {
  const { data } = await apiClient.put(`/plantillas-factura/${id}/`, payload)
  return data
}

/**
 * Elimina (soft-delete) una plantilla.
 */
export async function eliminarPlantilla(id) {
  await apiClient.delete(`/plantillas-factura/${id}/`)
}

