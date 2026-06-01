import { useEffect, useRef } from 'react'
import { Terminal } from 'lucide-react'

/**
 * Terminal simulada con logs de auditoría del proceso de estrés.
 */
export function AuditLogTerminal({ logs = [], autoScroll = true }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs, autoScroll])

  const levelColor = {
    ok: 'text-emerald-400',
    error: 'text-red-400',
    warn: 'text-amber-400',
    info: 'text-slate-300',
  }

  return (
    <div className="rounded-xl border border-slate-700 overflow-hidden bg-slate-900 shadow-inner">
      <div className="flex items-center gap-2 px-4 py-2 bg-slate-800 border-b border-slate-700">
        <Terminal className="h-4 w-4 text-emerald-400" />
        <span className="text-xs font-mono text-slate-400">Logs de auditoría — stress test DTE</span>
      </div>
      <div className="h-64 overflow-y-auto p-4 font-mono text-xs leading-relaxed">
        {logs.length === 0 ? (
          <p className="text-slate-500">Los eventos del proceso aparecerán aquí en tiempo real…</p>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex gap-2 mb-1">
              <span className="text-slate-500 shrink-0">[{log.time}]</span>
              <span className={levelColor[log.level] || 'text-slate-300'}>{log.message}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
