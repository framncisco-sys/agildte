import { useEffect, useState } from 'react'
import { X, Mail, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { reenviarCorreoVenta } from '../../../api/facturas'

export function correoDestinatarioVenta(venta) {
  if (!venta) return ''
  return (
    (venta.correo_receptor || venta.cliente_detalle?.correo || venta.cliente_detalle?.email_contacto || '')
      .trim()
  )
}

/**
 * Modal para reenviar factura por correo (mismo u otro destinatario).
 */
export function ReenviarCorreoModal({ open, onClose, venta, onExito }) {
  const correoGuardado = correoDestinatarioVenta(venta)
  const [modo, setModo] = useState('mismo')
  const [correoOtro, setCorreoOtro] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setModo(correoGuardado ? 'mismo' : 'otro')
    setCorreoOtro('')
    setError('')
  }, [open, venta?.id, correoGuardado])

  if (!open || !venta?.id) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    const destino = modo === 'mismo' ? correoGuardado : correoOtro.trim()
    if (!destino) {
      setError('Indique un correo de destino.')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(destino)) {
      setError('El correo no tiene un formato válido.')
      return
    }

    setEnviando(true)
    try {
      const data = await reenviarCorreoVenta(
        venta.id,
        modo === 'otro' || !correoGuardado ? { correo: destino } : {}
      )
      toast.success(data.mensaje || `Correo reenviado a ${destino}`)
      onExito?.({ ...venta, correo_receptor: data.correo_receptor || destino })
      onClose()
    } catch (err) {
      const d = err.response?.data
      const msg = d?.mensaje ?? d?.error ?? err.message ?? 'No se pudo reenviar el correo'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setEnviando(false)
    }
  }

  const tituloDoc = venta.numero_control || venta.codigo_generacion || `#${venta.id}`

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reenviar-correo-titulo"
    >
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
        <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between gap-3">
          <h2 id="reenviar-correo-titulo" className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <Mail className="w-5 h-5 text-blue-600" />
            Reenviar correo
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
            Documento: <span className="font-mono text-gray-800">{tituloDoc}</span>
          </p>

          {correoGuardado ? (
            <label className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50">
              <input
                type="radio"
                name="modoCorreo"
                value="mismo"
                checked={modo === 'mismo'}
                onChange={() => setModo('mismo')}
                className="mt-1"
              />
              <span className="text-sm">
                <span className="font-medium text-gray-800 block">Enviar al mismo correo</span>
                <span className="text-blue-700 break-all">{correoGuardado}</span>
                <span className="text-gray-500 block mt-0.5">Correo registrado al emitir la factura.</span>
              </span>
            </label>
          ) : (
            <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              Esta factura no tiene correo guardado. Indique el destinatario abajo.
            </p>
          )}

          <label className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50">
            <input
              type="radio"
              name="modoCorreo"
              value="otro"
              checked={modo === 'otro'}
              onChange={() => setModo('otro')}
              className="mt-1"
            />
            <span className="text-sm flex-1">
              <span className="font-medium text-gray-800 block">Enviar a otro correo</span>
              <span className="text-gray-500 block mb-2">Corrija el destinatario sin anular la factura.</span>
              <input
                type="email"
                value={correoOtro}
                onChange={(e) => {
                  setCorreoOtro(e.target.value)
                  setModo('otro')
                  setError('')
                }}
                placeholder="cliente@ejemplo.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={enviando}
              />
            </span>
          </label>

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
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 inline-flex items-center gap-2"
            >
              {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
              Reenviar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
