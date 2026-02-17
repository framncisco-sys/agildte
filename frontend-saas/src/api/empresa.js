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
