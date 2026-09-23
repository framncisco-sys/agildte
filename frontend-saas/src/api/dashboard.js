import apiClient from './axios'

/**
 * Obtiene las estadísticas del dashboard: KPIs del mes, ventas por día y últimas ventas.
 * @param {number|null} empresaId - ID de la empresa para filtrar (obligatorio en multi-empresa)
 * @returns {Promise<{ total_ventas_mes: number, cantidad_dtes_mes: number, ventas_hoy: number, ventas_por_dia: Array<{dia: string, total: number}>, ultimas_ventas: Array }>}
 */
export async function getDashboardStats(empresaId = null) {
  const { data } = await apiClient.get('/dashboard-stats/', {
    params: empresaId != null && empresaId !== '' ? { empresa_id: empresaId } : {},
  })
  return data
}

/**
 * Resumen IVA mensual publicado por el Sistema Contable (cuadro premium).
 * @param {number} empresaId
 * @param {string|null} periodo YYYY-MM
 */
export async function getResumenIvaMesContable(empresaId, periodo = null) {
  const params = { empresa_id: empresaId }
  if (periodo) params.periodo = periodo
  const { data } = await apiClient.get('/integraciones/contable/resumen-iva-mes/', { params })
  return data
}
