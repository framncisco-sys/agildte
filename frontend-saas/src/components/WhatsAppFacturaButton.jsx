import { Lock, MessageCircle } from 'lucide-react'

/**
 * Botón de WhatsApp en el historial.
 * Abre el modal de confirmación (mismo patrón que reenviar correo).
 * No envía directo: el envío ocurre en EnviarWhatsAppModal.
 */
export function WhatsAppFacturaButton({
  premiumEnabled = false,
  facturaProcesada = true,
  disabled = false,
  className = '',
  title,
  showLabel = false,
  compact = false,
  onOpen,
}) {
  const locked = !premiumEnabled
  const sinProcesar = !facturaProcesada

  const handleClick = () => {
    if (locked || disabled || sinProcesar) return
    onOpen?.()
  }

  const base = compact
    ? 'p-1 rounded-md transition-colors inline-flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed shrink-0'
    : 'p-2 rounded-lg transition-colors inline-flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed'
  const iconCls = compact ? 'w-3.5 h-3.5' : 'w-4 h-4'
  const active = 'text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800'
  const lockedCls = 'text-gray-400 bg-gray-50 cursor-not-allowed'

  let hint = title
  if (!hint) {
    if (locked) hint = 'Módulo de WhatsApp no habilitado'
    else if (sinProcesar) hint = 'Disponible cuando la factura esté PROCESADA por Hacienda'
    else hint = 'Enviar factura por WhatsApp'
  }

  const inactivo = locked || sinProcesar

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={locked || disabled || sinProcesar}
      className={`${base} ${inactivo ? lockedCls : active} ${className}`}
      title={hint}
      aria-label={hint}
    >
      {locked ? <Lock className={iconCls} /> : <MessageCircle className={iconCls} />}
      {showLabel && !compact && <span className="ml-1 text-xs font-medium">WhatsApp</span>}
    </button>
  )
}
