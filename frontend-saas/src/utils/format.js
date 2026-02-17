/**
 * Utilidades de formateo para moneda, fechas, etc.
 */

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
