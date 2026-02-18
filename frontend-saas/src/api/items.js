import apiClient from './axios'

const BASE = '/productos'

/**
 * Lista ítems/productos de la empresa. Opcional: búsqueda por texto.
 * @param {{ empresa_id?: string|number, q?: string }} params
 * @returns {Promise<Array>}
 */
export async function getItems(params = {}) {
  const searchParams = new URLSearchParams()
  if (params.empresa_id != null && params.empresa_id !== '') {
    searchParams.set('empresa_id', params.empresa_id)
  }
  if (params.q && params.q.trim()) {
    searchParams.set('q', params.q.trim())
  }
  const query = searchParams.toString()
  const url = query ? `${BASE}/?${query}` : `${BASE}/`
  const { data } = await apiClient.get(url)
  return Array.isArray(data) ? data : data?.results ?? []
}

/**
 * Busca ítems por descripción o código (para autocomplete en facturación).
 * @param {{ empresa_id?: string|number, q: string }}
 * @returns {Promise<Array>}
 */
export async function searchItems({ empresa_id, q = '' }) {
  return getItems({ empresa_id, q: q.trim() })
}

/**
 * Crea un ítem/producto.
 * @param {Object} payload - { empresa_id, descripcion, precio_unitario, codigo?, tipo_impuesto?, tipo_item? }
 * @returns {Promise<Object>}
 */
export async function createItem(payload) {
  const { data } = await apiClient.post(`${BASE}/crear/`, payload)
  return data
}

/**
 * Obtiene un ítem por ID.
 * @param {number} id
 * @returns {Promise<Object>}
 */
export async function getItemById(id) {
  const { data } = await apiClient.get(`${BASE}/${id}/`)
  return data
}

/**
 * Actualiza un ítem.
 * @param {number} id
 * @param {Object} payload - Campos a actualizar (partial)
 * @returns {Promise<Object>}
 */
export async function updateItem(id, payload) {
  const { data } = await apiClient.patch(`${BASE}/${id}/`, payload)
  return data
}

/**
 * Elimina (desactiva) un ítem.
 * @param {number} id
 */
export async function deleteItem(id) {
  await apiClient.delete(`${BASE}/${id}/`)
}
