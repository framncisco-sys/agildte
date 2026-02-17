import apiClient from './axios'

/**
 * Obtiene las estadísticas del dashboard: KPIs del mes, ventas por día y últimas ventas.
 * @returns {Promise<{ total_ventas_mes: number, cantidad_dtes_mes: number, ventas_hoy: number, ventas_por_dia: Array<{dia: string, total: number}>, ultimas_ventas: Array }>}
 */
export async function getDashboardStats() {
  const { data } = await apiClient.get('/dashboard-stats/')
  return data
}
