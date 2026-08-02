import { useEffect, useState } from 'react'
import { X, MessageCircle, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { enviarFacturaWhatsApp } from '../../../api/facturas'

export function telefonoDestinatarioVenta(venta) {
  if (!venta) return ''
  return (
    (venta.cliente_telefono || venta.telefono_receptor || venta.cliente_detalle?.telefono || '')
      .trim()
  )
}

/**
 * Modal para confirmar envío por WhatsApp y elegir el número de destino.
 */
export function EnviarWhatsAppModal({ open, onClose, venta, onExito }) {
  const telefonoGuardado = telefonoDestinatarioVenta(venta)
  const [telefono, setTelefono] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setTelefono(telefonoGuardado)
    setError('')
  }, [open, venta?.id, telefonoGuardado])

  if (!open || !venta?.id) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    const destino = telefono.trim()
    if (!destino) {
      setError('Indique el número de WhatsApp al que desea enviar.')
      return
    }
    const digitos = destino.replace(/\D/g, '')
    if (digitos.length < 8) {
      setError('El teléfono no tiene un formato válido (mín. 8 dígitos).')
      return
    }

    setEnviando(true)
    try {
      const data = await enviarFacturaWhatsApp(venta.id, destino)
      toast.success(data.mensaje || `WhatsApp enviado a ${destino}`)
      onExito?.({ ...venta, cliente_telefono: destino })
      onClose()
    } catch (err) {
      const d = err.response?.data
      const msg = d?.detail ?? d?.mensaje ?? d?.error ?? err.message ?? 'No se pudo enviar el WhatsApp'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setEnviando(false)
    }
  }

  const tituloDoc = venta.numero_control || venta.codigo_generacion || `#${venta.id}`
  const cliente = venta.nombre_receptor || venta.cliente_detalle?.nombre || 'Cliente'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="enviar-whatsapp-titulo"
      onClick={(e) => {
        if (e.target === e.currentTarget && !enviando) onClose()
      }}
    >
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
        <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between gap-3">
          <h2 id="enviar-whatsapp-titulo" className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-emerald-600" />
            Enviar por WhatsApp
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={enviando}
            className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 disabled:opacity-50"
            aria-label="Cerrar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <p className="text-sm text-gray-600">
            ¿Desea enviar esta factura por WhatsApp?
          </p>
          <p className="text-sm text-gray-600">
            Documento: <span className="font-mono text-gray-800">{tituloDoc}</span>
            <span className="text-gray-400"> · </span>
            <span className="text-gray-800">{cliente}</span>
          </p>

          <div>
            <label htmlFor="whatsapp-destino" className="block text-sm font-medium text-gray-800 mb-1.5">
              ¿A qué número de WhatsApp lo desea enviar?
            </label>
            <input
              id="whatsapp-destino"
              type="tel"
              autoFocus
              value={telefono}
              onChange={(e) => {
                setTelefono(e.target.value)
                setError('')
              }}
              placeholder="50371234567 o 71234567"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              disabled={enviando}
            />
            {telefonoGuardado ? (
              <p className="text-xs text-gray-500 mt-1.5">
                Teléfono del cliente: <span className="text-emerald-700 font-medium">{telefonoGuardado}</span>
                . Puede cambiarlo antes de enviar.
              </p>
            ) : (
              <p className="text-xs text-amber-700 mt-1.5">
                Esta factura no tiene teléfono guardado. Escriba el número de destino.
              </p>
            )}
          </div>

          {error && (
            <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
          )}

          <div className="flex gap-2 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={enviando}
              className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={enviando}
              className="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 inline-flex items-center gap-2"
            >
              {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageCircle className="w-4 h-4" />}
              Enviar WhatsApp
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
