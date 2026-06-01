import { useCallback, useRef, useState } from 'react'
import {
  STRESS_CONFIG,
  emitirDocumentoStressConSello,
  invalidarDocumentoStress,
  emitirNotaCreditoStress,
  ejecutarCicloContingenciaStress,
  obtenerClienteStress,
  extractError,
  sleepWithProgress,
  ventaProcesadaPorMH,
} from '../../../api/stressTest'

const INITIAL_PROGRESS = {
  phase: null,
  fe: { current: 0, total: STRESS_CONFIG.FE_COUNT },
  ccf: { current: 0, total: STRESS_CONFIG.CCF_COUNT },
  invalidaciones: { current: 0, total: STRESS_CONFIG.INVALIDATION_COUNT },
  notasCredito: { current: 0, total: STRESS_CONFIG.NC_COUNT },
  contingencia: { cycle: 0, totalCycles: STRESS_CONFIG.CONTINGENCY_CYCLES, step: 'idle' },
}

const PHASE_ORDER = ['emision_fe', 'emision_ccf', 'invalidacion', 'notas_credito', 'contingencia']

const PAUSE_AFTER_PHASE = {
  emision_fe: '100 CF completadas — inicio 100 CCF',
  emision_ccf: 'Fin emisión CCF — inicio invalidaciones',
  invalidacion: 'Fin invalidaciones — inicio notas de crédito',
  notas_credito: 'Fin notas de crédito — inicio contingencia',
}

function shufflePick(arr, count) {
  const copy = [...arr]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy.slice(0, Math.min(count, copy.length))
}

/**
 * Orquesta el ciclo de estrés DTE: emite uno a uno, espera selloRecibido, luego el siguiente (como carga masiva).
 */
export function useStressTest() {
  const [status, setStatus] = useState('idle')
  const [progress, setProgress] = useState(INITIAL_PROGRESS)
  const [logs, setLogs] = useState([])
  const abortRef = useRef(false)
  const sessionRef = useRef({
    feVentas: [],
    ccfVentas: [],
    clienteStress: null,
    completedPhases: [],
  })

  const appendLog = useCallback((level, message) => {
    const entry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      time: new Date().toLocaleTimeString('es-SV'),
      level,
      message,
    }
    setLogs((prev) => [...prev.slice(-499), entry])
  }, [])

  const checkAbort = useCallback(() => {
    if (abortRef.current) throw new Error('CANCELLED')
  }, [])

  const reset = useCallback(() => {
    abortRef.current = false
    setStatus('idle')
    setProgress({ ...INITIAL_PROGRESS })
    setLogs([])
    sessionRef.current = {
      feVentas: [],
      ccfVentas: [],
      clienteStress: null,
      completedPhases: [],
    }
  }, [])

  const cancel = useCallback(() => {
    abortRef.current = true
    appendLog('warn', 'Cancelación solicitada. Finalizando paso actual…')
  }, [appendLog])

  const runOrchestration = useCallback(async (empresaId, empresa, phasesToRun) => {
    const session = sessionRef.current
    const dteOptions = {
      onWait: (waitMs, attempt, msg) => {
        const secs = Math.ceil(waitMs / 1000)
        appendLog(
          'warn',
          `[THROTTLE] Límite backend/MH alcanzado (reintento ${attempt}). Esperando ${secs}s… (${msg})`
        )
      },
      onLog: appendLog,
      checkAbort,
    }

    const pauseBetweenPhases = async (label) => {
      await sleepWithProgress(STRESS_CONFIG.PHASE_PAUSE_MS, {
        label,
        onLog: appendLog,
        checkAbort,
      })
    }

    const runEmisionFe = async () => {
      setProgress((p) => ({ ...p, phase: 'emision_fe' }))
      appendLog('info', 'Fase 1: 100 CF — emitir → selloRecibido → siguiente (como carga masiva)')

      for (let i = 0; i < STRESS_CONFIG.FE_COUNT; i++) {
        checkAbort()
        const data = await emitirDocumentoStressConSello(
          empresaId,
          { tipoDte: '01', cliente: null, index: i },
          { ...dteOptions, selloLabel: `CF ${String(i + 1).padStart(4, '0')}` }
        )
        session.feVentas.push(data)
        setProgress((p) => ({ ...p, fe: { ...p.fe, current: i + 1 } }))
        appendLog(
          'ok',
          `[OK] CF ${String(i + 1).padStart(4, '0')} — sello: ${data.sello_recepcion || '—'}`
        )
      }

      session.completedPhases.push('emision_fe')
    }

    const runEmisionCcf = async () => {
      setProgress((p) => ({ ...p, phase: 'emision_ccf' }))
      appendLog('info', 'Fase 2: 100 CCF — emitir → selloRecibido → siguiente')

      session.clienteStress = await obtenerClienteStress(empresaId)
      appendLog(
        'ok',
        `Cliente CCF: ${session.clienteStress.nombre} · NRC ${session.clienteStress.nrc} · ${session.clienteStress.correo}`
      )

      for (let i = 0; i < STRESS_CONFIG.CCF_COUNT; i++) {
        checkAbort()
        const data = await emitirDocumentoStressConSello(
          empresaId,
          {
            tipoDte: '03',
            cliente: session.clienteStress,
            index: i,
          },
          { ...dteOptions, selloLabel: `CCF ${String(i + 1).padStart(4, '0')}` }
        )
        session.ccfVentas.push(data)
        setProgress((p) => ({ ...p, ccf: { ...p.ccf, current: i + 1 } }))
        appendLog(
          'ok',
          `[OK] CCF ${String(i + 1).padStart(4, '0')} — sello: ${data.sello_recepcion || '—'}`
        )
      }

      session.completedPhases.push('emision_ccf')
    }

    const runInvalidacion = async () => {
      if (!session.feVentas.length) {
        throw new Error('Ejecute primero la Fase 1 (100 CF) antes de invalidar.')
      }

      setProgress((p) => ({ ...p, phase: 'invalidacion' }))
      appendLog('info', 'Fase 3: Invalidación — 10 CF con sello MH')

      const feConSello = session.feVentas.filter(ventaProcesadaPorMH)
      if (feConSello.length < STRESS_CONFIG.INVALIDATION_COUNT) {
        throw new Error(
          `Solo ${feConSello.length} FE tienen sello MH; se requieren ${STRESS_CONFIG.INVALIDATION_COUNT} para invalidar.`
        )
      }
      const aInvalidar = shufflePick(feConSello, STRESS_CONFIG.INVALIDATION_COUNT)

      for (let i = 0; i < aInvalidar.length; i++) {
        checkAbort()
        const venta = aInvalidar[i]
        await invalidarDocumentoStress(empresaId, venta, empresa, dteOptions)
        setProgress((p) => ({ ...p, invalidaciones: { ...p.invalidaciones, current: i + 1 } }))
        appendLog('ok', `[OK] FE ${venta.numero_control || venta.id} invalidada correctamente`)
      }

      session.completedPhases.push('invalidacion')
    }

    const runNotasCredito = async () => {
      if (!session.ccfVentas.length) {
        throw new Error('Ejecute primero la Fase 2 (100 CCF) antes de emitir notas de crédito.')
      }
      if (!session.clienteStress) {
        session.clienteStress = await obtenerClienteStress(empresaId)
      }

      setProgress((p) => ({ ...p, phase: 'notas_credito' }))
      appendLog('info', 'Fase 4: 50 NC — emitir → selloRecibido → siguiente')

      const ccfConSello = session.ccfVentas.filter(ventaProcesadaPorMH)
      if (ccfConSello.length < STRESS_CONFIG.NC_COUNT) {
        throw new Error(
          `Solo ${ccfConSello.length} CCF tienen sello MH; se requieren ${STRESS_CONFIG.NC_COUNT} para notas de crédito.`
        )
      }
      const ccfParaNc = ccfConSello.slice(0, STRESS_CONFIG.NC_COUNT)

      for (let i = 0; i < ccfParaNc.length; i++) {
        checkAbort()
        const ccf = ccfParaNc[i]
        const nc = await emitirNotaCreditoStress(empresaId, ccf, session.clienteStress, i, dteOptions)
        setProgress((p) => ({ ...p, notasCredito: { ...p.notasCredito, current: i + 1 } }))
        appendLog(
          'ok',
          `[OK] NC ${String(i + 1).padStart(2, '0')} — sello: ${nc.sello_recepcion || '—'}`
        )
      }

      session.completedPhases.push('notas_credito')
    }

    const runContingencia = async () => {
      setProgress((p) => ({ ...p, phase: 'contingencia' }))
      appendLog('info', 'Fase 5: Ciclo de contingencia — 5 iteraciones')

      for (let ciclo = 0; ciclo < STRESS_CONFIG.CONTINGENCY_CYCLES; ciclo++) {
        checkAbort()
        setProgress((p) => ({
          ...p,
          contingencia: { cycle: ciclo + 1, totalCycles: STRESS_CONFIG.CONTINGENCY_CYCLES, step: 'activando' },
        }))

        const logContingencia = (levelOrMsg, maybeMsg) => {
          if (maybeMsg !== undefined) {
            appendLog(levelOrMsg, maybeMsg)
          } else {
            appendLog('info', levelOrMsg)
          }
        }

        const { resultado } = await ejecutarCicloContingenciaStress(
          empresaId,
          ciclo,
          (levelOrMsg, maybeMsg) => {
            logContingencia(levelOrMsg, maybeMsg)
            const text = maybeMsg !== undefined ? maybeMsg : levelOrMsg
            if (String(text).includes('F05') || String(text).includes('post-cierre') || String(text).includes('pendientes')) {
              setProgress((p) => ({
                ...p,
                contingencia: { ...p.contingencia, step: 'transmitiendo' },
              }))
            }
          },
          dteOptions
        )

        const eventoOk = resultado?.resultado_contingencia?.estado === 'RECIBIDO'
        const resumen = resultado?.resumen_envio
        const envioOk =
          !resumen ||
          ((resumen.rechazadas ?? 0) === 0 && (resumen.errores ?? 0) === 0)
        const mhOk = eventoOk && envioOk
        appendLog(
          mhOk ? 'ok' : 'error',
          mhOk
            ? `[OK] Contingencia ciclo ${ciclo + 1}: F05 RECIBIDO · ${resumen?.aceptadas ?? '?'}/${resultado?.ventas_procesadas?.length ?? resumen?.total ?? '?'} CF con sello`
            : `[ERROR] Contingencia ciclo ${ciclo + 1}: ${resultado?.mensaje || resultado?.resultado_contingencia?.mensaje || 'fallo en MH'}`
        )
        setProgress((p) => ({
          ...p,
          contingencia: { cycle: ciclo + 1, totalCycles: STRESS_CONFIG.CONTINGENCY_CYCLES, step: 'completado' },
        }))

        if (ciclo < STRESS_CONFIG.CONTINGENCY_CYCLES - 1) {
          await pauseBetweenPhases(`Fin contingencia ${ciclo + 1} — siguiente ciclo`)
        }
      }

      session.completedPhases.push('contingencia')
    }

    const phaseRunners = {
      emision_fe: runEmisionFe,
      emision_ccf: runEmisionCcf,
      invalidacion: runInvalidacion,
      notas_credito: runNotasCredito,
      contingencia: runContingencia,
    }

    appendLog('info', `[INICIO] Ciclo de estrés para empresa ${empresa?.nombre || empresaId}`)
    appendLog(
      'info',
      `Modo secuencial con MH síncrono (sello en respuesta) · pausa ${Math.round(STRESS_CONFIG.PHASE_PAUSE_MS / 1000)}s entre bloques`
    )

    for (let i = 0; i < phasesToRun.length; i++) {
      const phaseKey = phasesToRun[i]
      await phaseRunners[phaseKey]()

      const nextPhase = phasesToRun[i + 1]
      if (nextPhase && PAUSE_AFTER_PHASE[phaseKey]) {
        await pauseBetweenPhases(PAUSE_AFTER_PHASE[phaseKey])
      }
    }
  }, [appendLog, checkAbort])

  const start = useCallback(async (empresaId, empresa) => {
    if (!empresaId) return
    abortRef.current = false
    setStatus('running')
    setLogs([])
    setProgress({ ...INITIAL_PROGRESS, phase: 'emision_fe' })
    sessionRef.current = {
      feVentas: [],
      ccfVentas: [],
      clienteStress: null,
      completedPhases: [],
    }

    try {
      await runOrchestration(empresaId, empresa, PHASE_ORDER)
      setStatus('completed')
      appendLog('ok', '[FIN] Ciclo completo de validación y estrés finalizado.')
    } catch (err) {
      if (err.message === 'CANCELLED') {
        setStatus('cancelled')
        appendLog('warn', '[CANCELADO] Proceso detenido por el usuario.')
      } else {
        setStatus('error')
        appendLog('error', `[ERROR] ${extractError(err)}`)
      }
    }
  }, [appendLog, runOrchestration])

  const startPhase = useCallback(async (empresaId, empresa, phaseKey) => {
    if (!empresaId || !PHASE_ORDER.includes(phaseKey)) return
    abortRef.current = false
    setStatus('running')

    if (phaseKey === 'emision_fe') {
      sessionRef.current.feVentas = []
      setProgress((p) => ({
        ...p,
        phase: 'emision_fe',
        fe: { ...p.fe, current: 0 },
      }))
    } else if (phaseKey === 'emision_ccf') {
      sessionRef.current.ccfVentas = []
      setProgress((p) => ({
        ...p,
        phase: 'emision_ccf',
        ccf: { ...p.ccf, current: 0 },
      }))
    } else {
      setProgress((p) => ({ ...p, phase: phaseKey }))
    }

    appendLog('info', `[FASE INDIVIDUAL] Ejecutando ${phaseKey}…`)

    try {
      await runOrchestration(empresaId, empresa, [phaseKey])
      setStatus('completed')
      appendLog('ok', `[FIN] Fase ${phaseKey} completada.`)
    } catch (err) {
      if (err.message === 'CANCELLED') {
        setStatus('cancelled')
        appendLog('warn', '[CANCELADO] Proceso detenido por el usuario.')
      } else {
        setStatus('error')
        appendLog('error', `[ERROR] ${extractError(err)}`)
      }
    }
  }, [appendLog, runOrchestration])

  return {
    status,
    progress,
    logs,
    start,
    startPhase,
    cancel,
    reset,
    isRunning: status === 'running',
  }
}
