import apiClient from './axios'

const BASE = '/clientes'

/**
 * Lista todos los clientes (con búsqueda opcional).
 * @param {{ search?: string }} params - search filtra por nombre o NIT/documento
 * @returns {Promise<Array>}
 */
export async function getClientes(params = {}) {
  const searchParams = new URLSearchParams()
  if (params.search && params.search.trim()) {
    searchParams.set('search', params.search.trim())
  }
  const query = searchParams.toString()
  const url = query ? `${BASE}/?${query}` : `${BASE}/`
  const { data } = await apiClient.get(url)
  return Array.isArray(data) ? data : data?.results ?? []
}

/**
 * Obtiene un cliente por ID.
 * @param {number} id
 * @returns {Promise<Object>}
 */
export async function getClienteById(id) {
  const { data } = await apiClient.get(`${BASE}/${id}/`)
  return data
}

/**
 * Crea un cliente.
 * @param {Object} payload - Campos del cliente (nombre, documento_identidad, tipo_documento, nrc, correo, etc.)
 * @returns {Promise<Object>} Cliente creado
 * @throws {Error} Con response.data con errores de validación del backend
 */
export async function createCliente(payload) {
  const { data } = await apiClient.post(BASE + '/', payload)
  return data
}

/**
 * Actualiza un cliente.
 * @param {number} id
 * @param {Object} payload - Campos a actualizar
 * @returns {Promise<Object>} Cliente actualizado
 * @throws {Error} Con response.data con errores de validación del backend
 */
export async function updateCliente(id, payload) {
  const { data } = await apiClient.put(`${BASE}/${id}/`, payload)
  return data
}

/**
 * Elimina un cliente.
 * @param {number} id
 * @returns {Promise<void>}
 */
export async function deleteCliente(id) {
  await apiClient.delete(`${BASE}/${id}/`)
}

/**
 * Busca clientes por nombre y/o documento (NIT/DUI).
 * Compatible con el modal de búsqueda existente.
 * @param {{ nombre?: string, documento?: string }}
 * @returns {Promise<Array>}
 */
export async function searchClientes({ nombre = '', documento = '' }) {
  const query = [nombre, documento].filter(Boolean).join(' ').trim()
  const params = new URLSearchParams()
  if (query) params.set('search', query)
  const { data } = await apiClient.get(`${BASE}/?${params.toString()}`)
  return Array.isArray(data) ? data : data?.results ?? []
}
