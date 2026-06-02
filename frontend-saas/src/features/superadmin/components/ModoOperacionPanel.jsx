import { useState } from 'react'
import { FlaskConical, Globe, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { cambiarModoOperacion, getModoOperacion } from '../../../api/empresas'

/**
 * Panel superadmin: versión prueba vs online (reinicio correlativos al pasar a producción).
 */
export function ModoOperacionPanel({ empresaId, empresa, onUpdated }) {
  const [loading, setLoading] = useState(false)
  const modoActual = empresa?.ambiente === '00' ? 'online' : 'prueba'

  const aplicar = async (modo) => {
    if (modo === 'online') {
      const ok = window.confirm(
        '¿Activar modo ONLINE (producción)?\n\n' +
          'Se reiniciarán los correlativos de facturas DTE del año en curso.\n' +
          'Los documentos de prueba no se mezclarán con producción.\n\n' +
          '¿Continuar?'
      )
      if (!ok) return
    }
    setLoading(true)
    try {
      const data = await cambiarModoOperacion(empresaId, modo, {
        confirmarReinicio: modo === 'online',
      })
      toast.success(data?.mensaje || 'Modo actualizado')
      const fresh = await getModoOperacion(empresaId)
      onUpdated?.({ ...empresa, ambiente: fresh?.ambiente ?? (modo === 'online' ? '00' : '01') })
    } catch (err) {
      const d = err.response?.data
      toast.error(d?.detail || d?.mensaje || 'No se pudo cambiar el modo')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
      <h3 className="font-semibold text-slate-800 mb-2 flex items-center gap-2">
        <FlaskConical className="h-5 w-5 text-amber-600" />
        Modo de operación (caja y facturación)
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        <strong>Versión prueba:</strong> DTE y tickets marcados como prueba (AgilDTE apitest).
        <strong className="ml-1">Online:</strong> producción real; reinicia correlativos al activar.
      </p>
      <div className="flex flex-wrap gap-2 mb-4">
        <span
          className={`text-sm font-medium px-3 py-1 rounded-full ${
            modoActual === 'prueba' ? 'bg-amber-100 text-amber-900' : 'bg-emerald-100 text-emerald-800'
          }`}
        >
          {modoActual === 'prueba' ? 'Versión prueba' : 'Online — producción'}
        </span>
        <span className="text-sm text-slate-500 px-2 py-1">
          Ambiente AgilDTE: {empresa?.ambiente === '00' ? '00 Producción' : '01 Pruebas'}
        </span>
      </div>
      {modoActual === 'prueba' && (
        <div className="flex items-start gap-2 text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm mb-4">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>Los comprobantes impresos desde PosAgil mostrarán la leyenda <strong>PRUEBA</strong>.</span>
        </div>
      )}
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={loading || modoActual === 'prueba'}
          onClick={() => aplicar('prueba')}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-amber-300 bg-amber-50 text-amber-900 text-sm font-medium disabled:opacity-50 hover:bg-amber-100"
        >
          <FlaskConical className="h-4 w-4" />
          Versión prueba
        </button>
        <button
          type="button"
          disabled={loading || modoActual === 'online'}
          onClick={() => aplicar('online')}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-emerald-300 bg-emerald-50 text-emerald-900 text-sm font-medium disabled:opacity-50 hover:bg-emerald-100"
        >
          <Globe className="h-4 w-4" />
          Online — producción
        </button>
      </div>
    </div>
  )
}
