import { useState } from 'react'
import { X, Save, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { invalidarVenta } from '../../../api/facturas'

const TIPOS_INVALIDACION = [
  { value: 'Rescisión', label: 'Rescisión (Cancelar operación)' },
  { value: 'Nulidad', label: 'Nulidad (Error formal - requiere documento reemplazo)' },
]

const TIPOS_DOC = [
  { value: 'NIT', label: 'NIT' },
  { value: 'DUI', label: 'DUI' },
]

/**
 * Modal para invalidar (anular) un DTE procesado por MH.
 * @param {{ open: boolean, onClose: () => void, venta: object, onExito: (ventaActualizada) => void }} props
 */
export function InvalidacionModal({ open, onClose, venta, onExito }) {
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    tipoInvalidacion: 'Rescisión',
    motivoInvalidacion: '',
    tipoDocResponsable: 'NIT',
    numeroDocResponsable: '',
    nombreResponsable: '',
    tipoDocSolicitante: 'NIT',
    numeroDocSolicitante: '',
    nombreSolicitante: '',
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((f) => ({ ...f, [name]: value }))
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!venta?.id) return

    const motivo = form.motivoInvalidacion?.trim()
    if (!motivo) {
      setError('El motivo de invalidación es obligatorio')
      return
    }

    setEnviando(true)
    setError('')

    try {
      await invalidarVenta(venta.id, {
        motivoInvalidacion: motivo,
        tipoInvalidacion: form.tipoInvalidacion,
        nombreResponsable: form.nombreResponsable?.trim() || '',
        tipoDocResponsable: form.tipoDocResponsable,
        numeroDocResponsable: form.numeroDocResponsable?.trim() || '',
        nombreSolicitante: form.nombreSolicitante?.trim() || '',
        tipoDocSolicitante: form.tipoDocSolicitante,
        numeroDocSolicitante: form.numeroDocSolicitante?.trim() || '',
      })

      toast.success('Documento invalidado correctamente')
      onExito?.({ ...venta, estado_dte: 'Anulado', estado: 'ANULADO' })
      onClose()
    } catch (err) {
      const d = err.response?.data
      const msg = d?.mensaje ?? d?.error ?? err.message ?? 'Error al invalidar el documento'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setEnviando(false)
    }
  }

  const handleClose = () => {
    if (!enviando) {
      setForm({
        tipoInvalidacion: 'Rescisión',
        motivoInvalidacion: '',
        tipoDocResponsable: 'NIT',
        numeroDocResponsable: '',
        nombreResponsable: '',
        tipoDocSolicitante: 'NIT',
        numeroDocSolicitante: '',
        nombreSolicitante: '',
      })
      setError('')
      onClose()
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={handleClose}>
      <div
        className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Invalidación de DTE</h2>
          <button
            onClick={handleClose}
            disabled={enviando}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors disabled:opacity-50"
            aria-label="Cerrar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {venta?.numero_control && (
          <div className="px-6 py-2 bg-gray-50 border-b border-gray-100">
            <p className="text-sm text-gray-600">
              Documento: <span className="font-mono font-medium">{venta.numero_control}</span>
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de invalidación</label>
                <select
                  name="tipoInvalidacion"
                  value={form.tipoInvalidacion}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {TIPOS_INVALIDACION.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Motivo de invalidación *</label>
                <textarea
                  name="motivoInvalidacion"
                  value={form.motivoInvalidacion}
                  onChange={handleChange}
                  required
                  rows={2}
                  placeholder="Ej: Error en el precio"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                />
              </div>
            </div>

            <div className="border-t border-gray-200 pt-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Responsable de anulación</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1">Tipo Documento</label>
                  <select
                    name="tipoDocResponsable"
                    value={form.tipoDocResponsable}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    {TIPOS_DOC.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1">Número de Doc</label>
                  <input
                    type="text"
                    name="numeroDocResponsable"
                    value={form.numeroDocResponsable}
                    onChange={handleChange}
                    placeholder="Sin guiones"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-600 mb-1">Nombre del responsable</label>
                  <input
                    type="text"
                    name="nombreResponsable"
                    value={form.nombreResponsable}
                    onChange={handleChange}
                    placeholder="Nombre completo"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            <div className="border-t border-gray-200 pt-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Quien solicita la anulación</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1">Tipo Documento</label>
                  <select
                    name="tipoDocSolicitante"
                    value={form.tipoDocSolicitante}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    {TIPOS_DOC.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1">Número de Doc</label>
                  <input
                    type="text"
                    name="numeroDocSolicitante"
                    value={form.numeroDocSolicitante}
                    onChange={handleChange}
                    placeholder="Sin guiones"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-600 mb-1">Nombre de quien solicita</label>
                  <input
                    type="text"
                    name="nombreSolicitante"
                    value={form.nombreSolicitante}
                    onChange={handleChange}
                    placeholder="Nombre completo"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}
          </div>

          <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={enviando}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Cerrar
            </button>
            <button
              type="submit"
              disabled={enviando}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {enviando ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Cargando...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Invalidar Documento
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
