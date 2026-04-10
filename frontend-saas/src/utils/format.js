/**
 * Utilidades de formateo para moneda, fechas, etc.
 */

/** Zona horaria de facturación MH / negocio (El Salvador, UTC-6 fijo). */
const TZ_EL_SALVADOR = 'America/El_Salvador'

/**
 * Fecha civil actual en El Salvador como YYYY-MM-DD.
 * No usar toISOString() para "hoy": es UTC y puede cambiar el día respecto al calendario local.
 */
export function fechaHoyElSalvadorISO() {
  return new Date().toLocaleDateString('en-CA', { timeZone: TZ_EL_SALVADOR })
}

export function formatCurrency(value, currency = 'USD') {
  return new Intl.NumberFormat('es-SV', {
    style: 'currency',
    currency,
  }).format(value ?? 0)
}

export function formatDate(date, options = {}) {
  if (!date) return ''
  const d = typeof date === 'string' ? new Date(date) : date
  return new Intl.DateTimeFormat('es-SV', {
    dateStyle: options.short ? 'short' : 'medium',
    ...options,
  }).format(d)
}
