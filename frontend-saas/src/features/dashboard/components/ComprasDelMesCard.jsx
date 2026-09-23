import { useEffect, useState } from 'react'
import { getResumenIvaMesContable } from '../../../api/dashboard'

/**
 * Cuadro resumen compras / IVA del mes (premium).
 * Datos publicados por el Sistema Contable (no líneas de compras).
 */
const COMPRAS_MES_VACIO = {
  ventas: 0,
  debito: 0,
  retencion: 0,
  compras: 0,
  credito_fiscal: 0,
  valor_a_pagar: null,
  tiene_datos: false,
  periodo: null,
  actualizado_en: null,
}

function formatMoney(n) {
  const x = Number(n)
  if (!Number.isFinite(x)) return '$ 0.00'
  return `$ ${x.toLocaleString('es-SV', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const ROWS = [
  { key: 'ventas', label: 'Ventas' },
  { key: 'debito', label: 'Débito' },
  { key: 'retencion', label: 'Retención' },
  { key: 'compras', label: 'Compras' },
  { key: 'credito_fiscal', label: 'Crédito fiscal' },
]

export function ComprasDelMesCard({ empresaId }) {
  const [data, setData] = useState(COMPRAS_MES_VACIO)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!empresaId) {
      setData(COMPRAS_MES_VACIO)
      setError(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    getResumenIvaMesContable(empresaId)
      .then((res) => {
        if (cancelled) return
        setData({
          ...COMPRAS_MES_VACIO,
          ...res,
          tiene_datos: !!res?.tiene_datos,
        })
      })
      .catch((err) => {
        if (cancelled) return
        setData(COMPRAS_MES_VACIO)
        setError(
          err.response?.data?.error
          || err.message
          || 'No se pudo cargar el resumen contable.',
        )
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [empresaId])

  const debito = Number(data.debito) || 0
  const credito = Number(data.credito_fiscal) || 0
  const retencion = Number(data.retencion) || 0
  const valorPagar = data.valor_a_pagar != null && Number.isFinite(Number(data.valor_a_pagar))
    ? Number(data.valor_a_pagar)
    : Math.round((debito - credito - retencion) * 100) / 100

  const subtexto = loading
    ? 'Cargando resumen…'
    : error
      ? error
      : data.tiene_datos_compras
        ? `Ventas en vivo (AgilDTE)${data.periodo ? ` · compras del contable (${data.periodo})` : ''}.`
        : 'Ventas en vivo (AgilDTE). Aún no hay compras publicadas desde el servidor contable; se muestran $0 en compras/crédito.'

  return (
    <div className="bg-agil-bg-white rounded-xl border border-agil-border-subtle shadow-sm p-4 sm:p-5 h-full flex flex-col min-h-[280px]">
      <div className="flex items-start justify-between gap-2 mb-3">
        <h2 className="text-base sm:text-lg font-semibold text-agil-text-primary leading-tight">
          Compras del mes
        </h2>
        <span className="shrink-0 text-[10px] uppercase tracking-wide font-semibold px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 border border-amber-200">
          Premium
        </span>
      </div>
      <p className="text-xs text-agil-text-secondary mb-3">
        {subtexto}
      </p>
      <div className="flex-1 overflow-auto rounded-lg border border-agil-border-subtle">
        <table className="w-full text-sm">
          <tbody>
            {ROWS.map(({ key, label }) => (
              <tr key={key} className="border-b border-agil-border-subtle last:border-b-0">
                <td className="px-3 py-2.5 text-agil-text-primary font-medium">{label}</td>
                <td className="px-3 py-2.5 text-right text-agil-text-primary tabular-nums whitespace-nowrap">
                  {loading ? '…' : formatMoney(data[key])}
                </td>
              </tr>
            ))}
            <tr className="bg-agil-bg-main/80">
              <td className="px-3 py-3 text-agil-text-primary font-semibold text-xs sm:text-sm leading-snug">
                Valor a pagar el fin de mes
              </td>
              <td className="px-3 py-3 text-right font-bold text-agil-primary tabular-nums whitespace-nowrap">
                {loading ? '…' : formatMoney(valorPagar)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-agil-text-secondary mt-2 leading-snug">
        Cálculo: Débito (AgilDTE) − Crédito fiscal (contable) − Retención (AgilDTE)
        {data.actualizado_en
          ? ` · Compras actualizadas ${new Date(data.actualizado_en).toLocaleString('es-SV')}`
          : ' · Sin publicación de compras aún (se conserva vacío, no se borra histórico de otros periodos)'}
      </p>
    </div>
  )
}
