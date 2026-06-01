import { CheckCircle2, Circle, Loader2 } from 'lucide-react'

const PHASES = [
  { key: 'emision_fe', label: 'Fase 1 — Consumidor Final (CF)' },
  { key: 'emision_ccf', label: 'Fase 2 — Crédito Fiscal (CCF)' },
  { key: 'invalidacion', label: 'Fase 3 — Invalidación' },
  { key: 'notas_credito', label: 'Fase 4 — Notas de crédito' },
  { key: 'contingencia', label: 'Fase 5 — Contingencia' },
]

function PhaseBar({ label, current, total, active, done }) {
  const pct = total ? Math.round((current / total) * 100) : 0
  return (
    <div className={`rounded-lg border p-3 ${active ? 'border-indigo-300 bg-indigo-50' : 'border-slate-200 bg-white'}`}>
      <div className="flex justify-between text-sm mb-2">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-500 tabular-nums">{current}/{total}</span>
      </div>
      <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${done ? 'bg-emerald-500' : active ? 'bg-indigo-500' : 'bg-slate-300'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export function StressTestStepper({ progress, status }) {
  const { phase, fe, ccf, invalidaciones, notasCredito, contingencia } = progress
  const phaseOrder = PHASES.map((p) => p.key)
  const currentIdx = phaseOrder.indexOf(phase)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {PHASES.map((p, idx) => {
          const done = currentIdx > idx || status === 'completed'
          const active = phase === p.key && status === 'running'
          const Icon = done ? CheckCircle2 : active ? Loader2 : Circle
          return (
            <div
              key={p.key}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border ${
                done
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : active
                    ? 'bg-indigo-50 border-indigo-200 text-indigo-800'
                    : 'bg-slate-50 border-slate-200 text-slate-500'
              }`}
            >
              <Icon className={`h-3.5 w-3.5 ${active ? 'animate-spin' : ''}`} />
              {p.label}
            </div>
          )
        })}
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <PhaseBar
          label="Facturas Consumidor Final (CF)"
          current={fe.current}
          total={fe.total}
          active={phase === 'emision_fe'}
          done={fe.current >= fe.total}
        />
        <PhaseBar
          label="Comprobantes Crédito Fiscal (CCF)"
          current={ccf.current}
          total={ccf.total}
          active={phase === 'emision_ccf'}
          done={ccf.current >= ccf.total}
        />
        <PhaseBar
          label="Invalidaciones"
          current={invalidaciones.current}
          total={invalidaciones.total}
          active={phase === 'invalidacion'}
          done={invalidaciones.current >= invalidaciones.total}
        />
        <PhaseBar
          label="Notas de crédito (NC)"
          current={notasCredito.current}
          total={notasCredito.total}
          active={phase === 'notas_credito'}
          done={notasCredito.current >= notasCredito.total}
        />
      </div>

      {(phase === 'contingencia' || contingencia.cycle > 0) && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-900">
            Ciclo de Contingencia {contingencia.cycle}/{contingencia.totalCycles}
            {contingencia.step === 'transmitiendo' && ' — Transmitiendo F05 a MH…'}
            {contingencia.step === 'activando' && ' — Activando evento…'}
            {contingencia.step === 'completado' && contingencia.cycle === contingencia.totalCycles && ' — Completado'}
          </p>
          <div className="mt-2 h-2 bg-amber-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-500 transition-all duration-300"
              style={{ width: `${(contingencia.cycle / contingencia.totalCycles) * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
