import { useState } from 'react'
import { Loader2, Lock, MessageCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { enviarFacturaWhatsApp } from '../api/facturas'

/**
 * Envío de factura por WhatsApp Cloud API (AgilDTE).
 * No abre pestañas; muestra loading y toast según respuesta del backend.
 */
export function WhatsAppFacturaButton({
  ventaId,
  telefono,
  premiumEnabled = false,
  facturaProcesada = true,
  disabled = false,
  className = '',
  title,
  showLabel = false,
}) {
  const [loading, setLoading] = useState(false)
  const locked = !premiumEnabled
  const sinTelefono = !(telefono || '').trim()
  const sinProcesar = !facturaProcesada

  const handleClick = async () => {
    if (locked || loading || disabled || sinTelefono || sinProcesar) return
    setLoading(true)
    try {
      const data = await enviarFacturaWhatsApp(ventaId, telefono.trim())
      toast.success(data?.mensaje || 'Mensaje enviado por WhatsApp.')
    } catch (err) {
      const detail =
        err.response?.data?.detail ??
        err.response?.data?.mensaje ??
        err.message ??
        'No se pudo enviar el WhatsApp.'
      toast.error(typeof detail === 'string' ? detail : 'Error al enviar WhatsApp.')
    } finally {
      setLoading(false)
    }
  }

  const base =
    'p-2 rounded-lg transition-colors inline-flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed'
  const active = 'text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800'
  const lockedCls = 'text-gray-400 bg-gray-50 cursor-not-allowed'

  let hint = title
  if (!hint) {
    if (locked) hint = 'WhatsApp premium no habilitado (actívalo en Django admin → Empresa)'
    else if (sinProcesar) hint = 'Disponible cuando la factura esté PROCESADA por Hacienda'
    else if (sinTelefono) hint = 'Cliente sin teléfono en ficha'
    else hint = 'Enviar factura por WhatsApp'
  }

  const inactivo = locked || sinTelefono || sinProcesar

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={locked || loading || disabled || sinTelefono || sinProcesar}
      className={`${base} ${inactivo ? lockedCls : active} ${className}`}
      title={hint}
      aria-label={hint}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : locked ? (
        <Lock className="w-4 h-4" />
      ) : (
        <MessageCircle className="w-4 h-4" />
      )}
      {showLabel && <span className="ml-1 text-xs font-medium">WhatsApp</span>}
    </button>
  )
}
