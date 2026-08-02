/**
 * Confirma si se deben guardar en la ficha del cliente los cambios hechos al facturar.
 */
export function ConfirmActualizarClienteModal({
  open,
  nombreCliente,
  cambios = [],
  onConfirmar,
  onOmitir,
  onCancelar,
  enviando = false,
}) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-cliente-title"
        className="w-full max-w-lg rounded-xl bg-white shadow-xl"
      >
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 id="confirm-cliente-title" className="text-lg font-semibold text-slate-900">
            ¿Actualizar ficha del cliente?
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Detectamos cambios en los datos de{' '}
            <span className="font-medium text-slate-800">{nombreCliente || 'este cliente'}</span>{' '}
            respecto a su ficha guardada. ¿Desea registrarlos en el cliente?
          </p>
        </div>

        <div className="max-h-64 overflow-y-auto px-5 py-3">
          <ul className="space-y-2">
            {cambios.map((c) => (
              <li
                key={c.campo}
                className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm"
              >
                <div className="font-medium text-slate-800">{c.label}</div>
                <div className="mt-0.5 text-slate-600">
                  <span className="text-slate-400">{c.anterior}</span>
                  <span className="mx-1.5 text-slate-400">→</span>
                  <span className="font-medium text-emerald-700">{c.nuevo}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex flex-col-reverse gap-2 border-t border-slate-200 px-5 py-4 sm:flex-row sm:justify-end">
          <button
            type="button"
            disabled={enviando}
            onClick={onCancelar}
            className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-50"
          >
            Cancelar emisión
          </button>
          <button
            type="button"
            disabled={enviando}
            onClick={onOmitir}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Solo esta factura
          </button>
          <button
            type="button"
            disabled={enviando}
            onClick={onConfirmar}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {enviando ? 'Emitiendo…' : 'Sí, actualizar cliente'}
          </button>
        </div>
      </div>
    </div>
  )
}
