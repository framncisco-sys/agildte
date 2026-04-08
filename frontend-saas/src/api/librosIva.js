import apiClient from './axios'
import { useEmpresaStore } from '../stores/useEmpresaStore'

/**
 * Obtiene vista previa del libro de IVA (JSON).
 * @param {number} mes - 1 a 12
 * @param {number} anio - ej. 2026
 * @param {string} tipoLibro - 'consumidor' | 'contribuyente'
 * @returns {Promise<{ datos: Array, totales: Object, periodo: string, empresa: string }>}
 */
export async function getLibroIvaPreview(mes, anio, tipoLibro) {
  const empresaId = useEmpresaStore.getState().empresaId
  if (!empresaId) throw new Error('Seleccione una empresa')
  const { data } = await apiClient.get('/libros-iva/reporte/', {
    params: { mes, anio, tipo_libro: tipoLibro, empresa_id: empresaId },
  })
  return data
}

/**
 * Descarga el reporte en PDF o CSV.
 * @param {number} mes - 1 a 12
 * @param {number} anio - ej. 2026
 * @param {string} tipoLibro - 'consumidor' | 'contribuyente'
 * @param {string} format - 'pdf' | 'csv'
 * @returns {Promise<Blob>}
 */
export async function getLibroIvaBlob(mes, anio, tipoLibro, format) {
  const empresaId = useEmpresaStore.getState().empresaId
  if (!empresaId) throw new Error('Seleccione una empresa')
  const response = await apiClient.get('/libros-iva/reporte/', {
    params: { mes, anio, tipo_libro: tipoLibro, empresa_id: empresaId, export: format },
    responseType: 'blob',
  })
  return response.data
}

/**
 * Informe CF consolidado por día (primer/último DTE y total por fecha) en Excel .xlsx
 * Mismo mes/año que Libro Consumidor Final. Requiere rol contador (igual que Libros IVA).
 */
export async function downloadInformeCfDiarioXlsx(mes, anio) {
  const empresaId = useEmpresaStore.getState().empresaId
  if (!empresaId) throw new Error('Seleccione una empresa')
  const { data } = await apiClient.get('/libros-iva/informe-cf-diario.xlsx/', {
    params: { mes, anio, empresa_id: empresaId },
    responseType: 'blob',
  })
  return data
}
