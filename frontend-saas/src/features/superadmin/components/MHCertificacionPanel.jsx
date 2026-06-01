import { CheckCircle2, Circle, AlertCircle } from 'lucide-react'

/**
 * Checklist de requisitos para certificación MH (ambiente de pruebas → producción).
 * No ejecuta DTEs; guía la configuración de la empresa.
 */
export function MHCertificacionPanel({ empresa }) {
  if (!empresa) return null

  const checks = [
    {
      ok: Boolean(empresa.user_api_mh),
      label: 'Usuario API MH configurado (guarde también la clave API)',
    },
    {
      ok: Boolean(empresa.archivo_certificado),
      label: 'Certificado digital (.crt) cargado en el sistema',
    },
    {
      ok: Boolean(empresa.archivo_certificado),
      label: 'Contraseña del certificado (guárdela al subir el .crt)',
    },
    {
      ok: Boolean(empresa.cod_actividad && empresa.desc_actividad),
      label: 'Actividad económica del emisor (código + descripción MH)',
    },
    {
      ok: Boolean(empresa.cod_establecimiento && empresa.cod_punto_venta),
      label: 'Códigos de establecimiento y punto de venta',
    },
    {
      ok: empresa.ambiente === '01',
      label: 'Ambiente en Pruebas (01) mientras certifica con MH',
      warn: empresa.ambiente === '00',
      warnText: 'Está en Producción — use Pruebas hasta aprobar certificación',
    },
  ]

  const listos = checks.filter((c) => c.ok).length

  return (
    <div className="bg-white rounded-xl border border-emerald-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-emerald-100 bg-emerald-50">
        <h2 className="font-semibold text-emerald-900">Certificación MH → Producción</h2>
        <p className="text-sm text-emerald-800 mt-0.5">
          Complete esta configuración antes de solicitar el pase a ambiente productivo en Hacienda.
          {' '}{listos}/{checks.length} requisitos cumplidos.
        </p>
      </div>
      <ul className="p-5 space-y-3">
        {checks.map((c) => (
          <li key={c.label} className="flex items-start gap-2 text-sm">
            {c.ok ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
            ) : c.warn ? (
              <AlertCircle className="h-5 w-5 text-amber-500 shrink-0" />
            ) : (
              <Circle className="h-5 w-5 text-slate-300 shrink-0" />
            )}
            <span className={c.ok ? 'text-slate-800' : c.warn ? 'text-amber-800' : 'text-slate-600'}>
              {c.label}
              {c.warnText && <span className="block text-xs text-amber-700 mt-0.5">{c.warnText}</span>}
            </span>
          </li>
        ))}
      </ul>
      <div className="px-5 pb-4 text-xs text-slate-500">
        Tipo de sistema: <strong>{empresa.tipo_sistema || 'AGILDTE'}</strong>
        {' · '}
        WhatsApp: <strong>{empresa.whatsapp_premium_enabled ? 'Activo' : 'Inactivo'}</strong>
      </div>
    </div>
  )
}
