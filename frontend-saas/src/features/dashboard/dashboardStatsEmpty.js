/**
 * Estadísticas vacías del dashboard (sin ventas en el mes o API no disponible).
 */
export function buildEmptyDashboardStats(date = new Date()) {
  const year = date.getFullYear()
  const month = date.getMonth()
  const lastDay = new Date(year, month + 1, 0).getDate()
  const ventas_por_dia = []
  for (let d = 1; d <= lastDay; d += 1) {
    ventas_por_dia.push({ dia: String(d).padStart(2, '0'), total: 0 })
  }
  return {
    total_ventas_mes: 0,
    cantidad_dtes_mes: 0,
    ventas_hoy: 0,
    ventas_por_dia,
    ultimas_ventas: [],
  }
}

export function normalizeDashboardStats(data) {
  if (!data || typeof data !== 'object') return buildEmptyDashboardStats()
  const empty = buildEmptyDashboardStats()
  const ventasPorDia = Array.isArray(data.ventas_por_dia) && data.ventas_por_dia.length
    ? data.ventas_por_dia
    : empty.ventas_por_dia
  return {
    total_ventas_mes: Number(data.total_ventas_mes) || 0,
    cantidad_dtes_mes: Number(data.cantidad_dtes_mes) || 0,
    ventas_hoy: Number(data.ventas_hoy) || 0,
    ventas_por_dia: ventasPorDia,
    ultimas_ventas: Array.isArray(data.ultimas_ventas) ? data.ultimas_ventas : [],
  }
}
