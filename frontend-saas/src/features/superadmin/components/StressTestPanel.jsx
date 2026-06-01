import { useState } from 'react'
import { AlertTriangle, Loader2, Play, Square, RotateCcw, Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import { useStressTest } from '../hooks/useStressTest'
import { StressTestStepper } from './StressTestStepper'
import { AuditLogTerminal } from './AuditLogTerminal'
import { STRESS_CONFIG } from '../../../api/stressTest'

/**
 * Panel de pruebas y simulación (Stress & Compliance Test) dentro del detalle de empresa.
 */
export function StressTestPanel({ empresaId, empresa }) {
  const { status, progress, logs, start, startPhase, cancel, reset, isRunning } = useStressTest()
  const [confirmStep, setConfirmStep] = useState(0)
  const [pendingPhase, setPendingPhase] = useState(null)

  const credencialesOk = Boolean(
    empresa?.user_api_mh && empresa?.archivo_certificado
  )

  const phasePauseSec = Math.round(STRESS_CONFIG.PHASE_PAUSE_MS / 1000)

  const phaseButtons = [
    { key: 'emision_fe', label: 'Solo Fase 1', hint: '100 CF (Consumidor Final)' },
    { key: 'emision_ccf', label: 'Solo Fase 2', hint: '100 CCF (Crédito Fiscal)' },
    { key: 'invalidacion', label: 'Solo Fase 3', hint: 'Requiere Fase 1 previa', needsFe: true },
    { key: 'notas_credito', label: 'Solo Fase 4', hint: 'Requiere Fase 2 previa', needsCcf: true },
    { key: 'contingencia', label: 'Solo Fase 5', hint: '5 ciclos contingencia' },
  ]

  const handleStartClick = () => {
    if (!credencialesOk) {
      toast.error('Configure credenciales MH y certificado antes de ejecutar el estrés.')
      return
    }
    setConfirmStep(1)
  }

  const handleFirstConfirm = () => {
    setConfirmStep(2)
  }

  const handleFinalConfirm = () => {
    setConfirmStep(0)
    if (pendingPhase) {
      startPhase(empresaId, empresa, pendingPhase)
      setPendingPhase(null)
    } else {
      start(empresaId, empresa)
    }
  }

  const handleStartPhase = (phaseKey) => {
    if (!credencialesOk) {
      toast.error('Configure credenciales MH y certificado antes de ejecutar el estrés.')
      return
    }
    setPendingPhase(phaseKey)
    setConfirmStep(1)
  }

  const handleCancelConfirm = () => {
    setConfirmStep(0)
    setPendingPhase(null)
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-200 bg-gradient-to-r from-amber-50 to-orange-50">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-amber-100">
            <Zap className="h-5 w-5 text-amber-700" />
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-slate-800">Prueba de carga interna (opcional)</h2>
            <p className="text-sm text-slate-600 mt-0.5">
              Simulación de volumen para validar infraestructura — <strong>no sustituye</strong> la certificación oficial de MH.
              Complete primero el checklist de certificación y guarde certificado + actividad económica arriba.
            </p>
          </div>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {!credencialesOk && (
          <div className="flex gap-3 p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-sm">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <p>
              Esta empresa no tiene credenciales MH o certificado configurados. El estrés transaccional
              requiere conexión real con el Ministerio de Hacienda.
            </p>
          </div>
        )}

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          <p>
            Emite <strong>uno a uno</strong> con MH <strong>síncrono</strong> (sello en la misma petición), excepto en{' '}
            <strong>contingencia</strong>: allí registra CF en PendienteEnvio y el sello llega al cerrar el evento F05.
            Pausa <strong>{phasePauseSec}s</strong> entre bloques.
          </p>
        </div>

        <StressTestStepper progress={progress} status={status} />

        <div className="flex flex-wrap gap-3">
          {!isRunning ? (
            <>
              <button
                type="button"
                onClick={handleStartClick}
                disabled={!empresaId || status === 'running'}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                <Play className="h-4 w-4" />
                Iniciar Ciclo Completo de Validación y Estrés
              </button>
              {(status === 'completed' || status === 'error' || status === 'cancelled') && (
                <button
                  type="button"
                  onClick={reset}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  <RotateCcw className="h-4 w-4" />
                  Reiniciar panel
                </button>
              )}
            </>
          ) : (
            <button
              type="button"
              onClick={cancel}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-red-300 text-red-700 hover:bg-red-50"
            >
              <Square className="h-4 w-4" />
              Detener proceso
            </button>
          )}
          {isRunning && (
            <span className="inline-flex items-center gap-2 text-sm text-indigo-700">
              <Loader2 className="h-4 w-4 animate-spin" />
              Ejecutando… no cierre esta pestaña.
            </span>
          )}
        </div>

        {!isRunning && (
          <div className="flex flex-wrap gap-2">
            {phaseButtons.map((phase) => {
              const disabled =
                !empresaId ||
                !credencialesOk ||
                (phase.needsFe && progress.fe.current === 0) ||
                (phase.needsCcf && progress.ccf.current === 0)
              return (
                <button
                  key={phase.key}
                  type="button"
                  disabled={disabled}
                  onClick={() => handleStartPhase(phase.key)}
                  title={phase.hint}
                  className="inline-flex flex-col items-start px-3 py-2 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 disabled:opacity-40 text-xs"
                >
                  <span className="font-medium">{phase.label}</span>
                  <span className="text-slate-500">{phase.hint}</span>
                </button>
              )
            })}
          </div>
        )}

        <AuditLogTerminal logs={logs} />
      </div>

      {confirmStep > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
            {confirmStep === 1 ? (
              <>
                <div className="flex items-center gap-3 mb-4">
                  <AlertTriangle className="h-8 w-8 text-amber-500" />
                  <h3 className="text-lg font-semibold text-slate-800">Confirmación requerida</h3>
                </div>
                <p className="text-slate-600 mb-6">
                  {pendingPhase
                    ? `¿Ejecutar solo la fase seleccionada (${pendingPhase})? Se respetarán pausas y reintentos automáticos ante throttling.`
                    : `¿Estás seguro de que deseas estresar el entorno de esta empresa? Se emitirán cientos de DTEs reales hacia el ambiente MH configurado (${empresa?.ambiente === '00' ? 'Producción' : 'Pruebas'}). El proceso tardará varios minutos.`}
                </p>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={handleCancelConfirm}
                    className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    onClick={handleFirstConfirm}
                    className="px-4 py-2 rounded-lg bg-amber-600 text-white hover:bg-amber-700"
                  >
                    Sí, continuar
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center gap-3 mb-4">
                  <AlertTriangle className="h-8 w-8 text-red-500" />
                  <h3 className="text-lg font-semibold text-slate-800">Última confirmación</h3>
                </div>
                <p className="text-slate-600 mb-2">
                  Esta acción es <strong>irreversible</strong> en términos de correlativos y registros fiscales.
                </p>
                <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3 mb-6">
                  Empresa: <strong>{empresa?.nombre}</strong>. Escribe mentalmente «ESTRESAR» y confirma solo si
                  estás en ambiente de pruebas o tienes autorización explícita.
                </p>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={handleCancelConfirm}
                    className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                  >
                    No, cancelar
                  </button>
                  <button
                    type="button"
                    onClick={handleFinalConfirm}
                    className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 font-medium"
                  >
                    Confirmar — Ejecutar estrés
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
