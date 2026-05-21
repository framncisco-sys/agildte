/**
 * Convierte errores de respuesta DRF/axios a texto legible.
 * @param {unknown} data
 * @param {string} fallback
 */
export function formatApiErrorMessage(data, fallback = 'Error en la solicitud') {
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (typeof data !== 'object') return fallback

  if (typeof data.error === 'string') return data.error
  if (typeof data.mensaje === 'string') return data.mensaje
  if (typeof data.detail === 'string') return data.detail

  const flatten = (value, prefix = '') => {
    if (value == null) return []
    if (typeof value === 'string') return [prefix ? `${prefix}: ${value}` : value]
    if (Array.isArray(value)) {
      return value.flatMap((item, i) => {
        if (typeof item === 'string') return [prefix ? `${prefix}: ${item}` : item]
        if (item && typeof item === 'object') {
          const nested = flatten(item, prefix ? `${prefix}[${i}]` : `Ítem ${i + 1}`)
          return nested.length ? nested : [prefix ? `${prefix}: error de validación` : `Ítem ${i + 1}: error de validación`]
        }
        return []
      })
    }
    if (typeof value === 'object') {
      return Object.entries(value).flatMap(([k, v]) => {
        const label = prefix ? `${prefix}.${k}` : k
        return flatten(v, label)
      })
    }
    return [prefix ? `${prefix}: ${String(value)}` : String(value)]
  }

  const parts = flatten(data)
  return parts.length ? parts.join(' | ') : fallback
}
