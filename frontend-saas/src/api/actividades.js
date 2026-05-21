import apiClient from './axios'

const BASE = '/actividades'

/**
 * Busca actividades económicas (paginado). Para autocomplete usar search con 2+ caracteres.
 * @param {{ search?: string, limit?: number, offset?: number }} params
 * @returns {Promise<{ results: Array<{codigo: string, descripcion: string}>, count: number, next?: string, previous?: string }>}
 */
export async function getActividades(params = {}) {
  const searchParams = new URLSearchParams()
  if (params.search && params.search.trim()) searchParams.set('search', params.search.trim())
  if (params.limit != null) searchParams.set('limit', params.limit)
  if (params.offset != null) searchParams.set('offset', params.offset)
  const query = searchParams.toString()
  const url = query ? `${BASE}/?${query}` : `${BASE}/`
  const { data } = await apiClient.get(url)
  return data
}

/**
 * Importa/actualiza el catálogo MH desde CSV (;) o Excel.
 * @param {File} file
 * @returns {Promise<{ ok: boolean, mensaje: string, created: number, updated: number, total_en_bd: number }>}
 */
export async function importarCatalogoActividades(file) {
  const form = new FormData()
  form.append('archivo', file)
  const { data } = await apiClient.post(`${BASE}/importar-catalogo/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
