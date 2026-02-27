import apiClient from './axios'

/**
 * Sube archivo Excel/CSV para carga masiva.
 * @param {File} archivo - Archivo .xlsx o .csv
 * @param {number} empresaId - ID de la empresa
 * @returns {Promise<{filas, total, empresa_id}>}
 */
export async function subirArchivoCargaMasiva(archivo, empresaId) {
  const formData = new FormData()
  formData.append('archivo', archivo)
  formData.append('empresa_id', empresaId)
  const { data } = await apiClient.post('/carga-masiva/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data
}

/**
 * Descarga la plantilla de ejemplo para carga masiva.
 */
export async function descargarPlantillaEjemplo() {
  const { data } = await apiClient.get('/carga-masiva/plantilla-ejemplo/', {
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  }))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', 'plantilla_carga_masiva.xlsx')
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
