import apiClient from './axios'

/**
 * Obtiene las estadísticas del dashboard: KPIs del mes, ventas por día y últimas ventas.
 * @param {number|null} empresaId - ID de la empresa para filtrar (obligatorio en multi-empresa)
 * @returns {Promise<{ total_ventas_mes: number, cantidad_dtes_mes: number, ventas_hoy: number, ventas_por_dia: Array<{dia: string, total: number}>, ultimas_ventas: Array }>}
 */
export async function getDashboardStats(empresaId = null) {
  const params = empresaId ? `?empresa_id=${empresaId}` : ''
  const { data } = await apiClient.get(`/dashboard-stats/${params}`)
  return data
}
