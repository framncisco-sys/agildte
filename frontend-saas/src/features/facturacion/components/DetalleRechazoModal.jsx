import { X } from 'lucide-react'

/**
 * Modal que muestra el detalle del rechazo de MH: código, descripción y lista de observaciones.
 * @param {{ open: boolean, onClose: () => void, venta: { observaciones_mh?: { codigo?: string, descripcion?: string, observaciones?: string[] }, numero_control?: string } }} props
 */
export function DetalleRechazoModal({ open, onClose, venta }) {
  if (!open) return null

  const detalle = venta?.observaciones_mh || {}
  const { codigo, descripcion, observaciones = [] } = detalle

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Detalle del Rechazo</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
            aria-label="Cerrar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {venta?.numero_control && (
            <p className="text-sm text-gray-500">
              Documento: <span className="font-medium text-gray-700">{venta.numero_control}</span>
            </p>
          )}

          {codigo && (
            <div>
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Código del Mensaje</span>
              <p className="mt-1 text-gray-800 font-mono">{codigo}</p>
            </div>
          )}

          {descripcion && (
            <div>
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Descripción</span>
              <p className="mt-1 text-gray-800">{descripcion}</p>
            </div>
          )}

          {observaciones?.length > 0 && (
            <div>
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Observaciones de MH</span>
              <ul className="mt-2 space-y-1 list-disc list-inside text-gray-700">
                {observaciones.map((obs, i) => (
                  <li key={i}>{typeof obs === 'string' ? obs : String(obs)}</li>
                ))}
              </ul>
            </div>
          )}

          {!codigo && !descripcion && (!observaciones || observaciones.length === 0) && (
            <p className="text-gray-500 italic">No hay detalles adicionales del rechazo.</p>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  )
}
