import { useState, useEffect, useMemo } from 'react'
import { DollarSign, FileText, TrendingUp } from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { getDashboardStats } from '../../api/dashboard'
import { getEmpresa } from '../../api/empresa'
import { useEmpresaStore } from '../../stores/useEmpresaStore'
import { ComprasDelMesCard } from './components/ComprasDelMesCard'
import { buildEmptyDashboardStats, normalizeDashboardStats } from './dashboardStatsEmpty'

function SkeletonCard() {
  return (
    <div className="bg-agil-bg-white rounded-xl border border-agil-border-subtle shadow-sm p-5 animate-pulse">
      <div className="h-5 w-20 bg-agil-border-subtle rounded mb-3" />
      <div className="h-8 w-24 bg-agil-border-subtle rounded" />
    </div>
  )
}

function SkeletonChart() {
  return (
    <div className="bg-agil-bg-white rounded-xl border border-agil-border-subtle shadow-sm p-5 animate-pulse">
      <div className="h-6 w-56 bg-agil-border-subtle rounded mb-4" />
      <div className="h-64 bg-agil-bg-main rounded" />
    </div>
  )
}

function isServerUnavailable(err) {
  const status = err?.response?.status
  if (status === 502 || status === 503 || status === 504) return true
  const msg = String(err?.message || '').toLowerCase()
  return msg.includes('network') || msg.includes('timeout') || msg.includes('502')
}

export function DashboardPage() {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const empresaNombre = useEmpresaStore((s) => s.empresaNombre)
  const [stats, setStats] = useState(() => buildEmptyDashboardStats())
  const [loading, setLoading] = useState(true)
  const [apiWarning, setApiWarning] = useState(null)
  const [comprasPremium, setComprasPremium] = useState(false)

  useEffect(() => {
    if (!empresaId) {
      setComprasPremium(false)
      return
    }
    let cancelled = false
    getEmpresa(empresaId)
      .then((emp) => {
        if (!cancelled) {
          setComprasPremium(!!emp?.dashboard_compras_premium_enabled)
        }
      })
      .catch(() => {
        if (!cancelled) setComprasPremium(false)
      })
    return () => { cancelled = true }
  }, [empresaId])

  useEffect(() => {
    if (!empresaId) {
      setLoading(false)
      setStats(buildEmptyDashboardStats())
      setApiWarning(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setApiWarning(null)
    getDashboardStats(empresaId)
      .then((data) => {
        if (!cancelled) {
          setStats(normalizeDashboardStats(data))
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setStats(buildEmptyDashboardStats())
          if (isServerUnavailable(err)) {
            setApiWarning(
              'No se pudo conectar con el servidor (error 502/503). Se muestran valores en cero. '
              + 'Si acaba de desplegar, ejecute migraciones y reinicie el backend.'
            )
          } else {
            setApiWarning(
              err.response?.data?.detail
              || err.response?.data?.error
              || err.message
              || 'No se pudieron cargar las estadísticas; se muestran ceros.'
            )
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [empresaId])

  const formatCurrency = (n) => {
    const x = Number(n)
    if (!Number.isFinite(x)) return '$ 0.00'
    return `$ ${x.toLocaleString('es-SV', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const chartData = useMemo(() => stats?.ventas_por_dia ?? [], [stats])
  const sinVentasEnMes = !chartData.some((d) => Number(d.total) > 0)

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-agil-text-primary">Dashboard</h1>
        <p className="mt-1 text-agil-text-secondary text-sm">
          Métricas de facturación del mes actual
          {empresaNombre && <span className="ml-1 font-medium text-agil-primary">— {empresaNombre}</span>}
        </p>
      </div>

      {!empresaId && (
        <div className="rounded-xl bg-agil-orange-light border border-agil-orange text-agil-text-primary px-4 py-3 text-sm flex items-center gap-2">
          <span className="text-agil-orange">●</span>
          Selecciona una empresa en la barra superior para ver las estadísticas.
        </div>
      )}

      {apiWarning && (
        <div className="rounded-xl bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 text-sm">
          {apiWarning}
        </div>
      )}

      {/* Sección superior: 3 Cards KPI */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <div className="bg-agil-bg-white rounded-xl border border-agil-border-subtle shadow-sm hover:shadow-md transition-shadow p-5 flex items-start gap-4">
              <div className="p-2.5 rounded-xl bg-[#D1FAE5] text-agil-success">
                <DollarSign size={24} strokeWidth={2} />
              </div>
              <div>
                <p className="text-sm font-medium text-agil-text-secondary">Ventas del mes</p>
                <p className="text-2xl font-bold text-agil-success mt-0.5">
                  {formatCurrency(stats?.total_ventas_mes ?? 0)}
                </p>
              </div>
            </div>
            <div className="bg-agil-bg-white rounded-xl border border-agil-border-subtle shadow-sm hover:shadow-md transition-shadow p-5 flex items-start gap-4">
              <div className="p-2.5 rounded-xl bg-[#DBEAFE] text-agil-primary">
                <FileText size={24} strokeWidth={2} />
              </div>
              <div>
                <p className="text-sm font-medium text-agil-text-secondary">DTEs emitidos (mes)</p>
                <p className="text-2xl font-bold text-agil-primary mt-0.5">
                  {stats?.cantidad_dtes_mes ?? 0}
                </p>
              </div>
            </div>
            <div className="bg-agil-bg-white rounded-xl border border-agil-border-subtle shadow-sm hover:shadow-md transition-shadow p-5 flex items-start gap-4">
              <div className="p-2.5 rounded-xl bg-[#D1FAE5] text-agil-success">
                <TrendingUp size={24} strokeWidth={2} />
              </div>
              <div>
                <p className="text-sm font-medium text-agil-text-secondary">Ventas hoy</p>
                <p className="text-2xl font-bold text-agil-text-primary mt-0.5">
                  {formatCurrency(stats?.ventas_hoy ?? 0)}
                </p>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Gráfico de ventas + Compras del mes (premium) */}
      <div className={`grid grid-cols-1 gap-4 min-w-0 ${comprasPremium ? 'lg:grid-cols-3' : ''}`}>
        <div className={comprasPremium ? 'lg:col-span-2 min-w-0' : 'min-w-0'}>
          {loading ? (
            <SkeletonChart />
          ) : (
            <div className="bg-agil-bg-white rounded-xl border border-agil-border-subtle shadow-sm p-4 sm:p-5 overflow-hidden h-full">
              <h2 className="text-base sm:text-lg font-semibold text-agil-text-primary mb-1">
                Comportamiento de Ventas (Este Mes)
              </h2>
              {sinVentasEnMes && (
                <p className="text-xs text-agil-text-secondary mb-3">
                  Sin ventas registradas este mes — gráfico en $ 0.00
                </p>
              )}
              {!sinVentasEnMes && <div className="mb-4" />}
              <ResponsiveContainer width="100%" height={260} minHeight={220}>
                <AreaChart
                  data={chartData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#1A56DB" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#1A56DB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis
                    dataKey="dia"
                    tick={{ fontSize: 11, fill: '#6B7280' }}
                    axisLine={{ stroke: '#E5E7EB' }}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#6B7280' }}
                    axisLine={false}
                    domain={[0, 'auto']}
                    tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v))}
                  />
                  <Tooltip
                    formatter={(value) => [formatCurrency(Number(value)), 'Total']}
                    labelFormatter={(label) => `Día ${label}`}
                    contentStyle={{ borderRadius: '8px', border: '1px solid #E5E7EB' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="total"
                    stroke="#1A56DB"
                    strokeWidth={2}
                    fill="url(#colorTotal)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
        {comprasPremium && (
          <div className="lg:col-span-1 min-w-0">
            <ComprasDelMesCard />
          </div>
        )}
      </div>

      {/* Sección inferior: Últimos documentos emitidos */}
      <div className="bg-agil-bg-white rounded-xl border border-agil-border-subtle shadow-sm overflow-hidden min-w-0">
        <h2 className="text-base sm:text-lg font-semibold text-agil-text-primary px-4 sm:px-5 py-4 border-b border-agil-border-subtle">
          Últimos Documentos Emitidos
        </h2>
        {loading ? (
          <div className="p-4 sm:p-5 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-10 bg-agil-bg-main rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            {stats?.ultimas_ventas?.length > 0 && (
              <div className="md:hidden divide-y divide-agil-border-subtle">
                {stats.ultimas_ventas.map((v) => (
                  <div key={v.id} className="p-4 space-y-1">
                    <p className="font-medium text-agil-text-primary">{v.numero_control}</p>
                    <p className="text-sm text-agil-text-secondary truncate">{v.cliente}</p>
                    <p className="text-sm font-medium text-agil-text-primary">{formatCurrency(v.total)}</p>
                    <span
                      className={`inline-flex px-2 py-0.5 rounded-lg text-xs font-medium ${
                        v.estado === 'AceptadoMH' ? 'bg-[#D1FAE5] text-agil-success'
                          : v.estado === 'Enviado' ? 'bg-[#DBEAFE] text-agil-primary'
                          : v.estado === 'Borrador' ? 'bg-agil-bg-main text-agil-text-secondary'
                          : 'bg-agil-orange-light text-agil-orange'
                      }`}
                    >
                      {v.estado}
                    </span>
                  </div>
                ))}
              </div>
            )}
            <div className="overflow-x-auto">
              {(!stats?.ultimas_ventas || stats.ultimas_ventas.length === 0) ? (
                <p className="text-agil-text-secondary text-sm px-4 sm:px-5 py-8 text-center">
                  No hay documentos recientes
                </p>
              ) : (
                <table className="w-full text-sm min-w-[400px] hidden md:table">
                  <thead>
                    <tr className="bg-agil-bg-main border-b border-agil-border-subtle">
                      <th className="px-5 py-3 text-left font-semibold text-agil-text-secondary">Nº Control</th>
                      <th className="px-5 py-3 text-left font-semibold text-agil-text-secondary">Cliente</th>
                      <th className="px-5 py-3 text-right font-semibold text-agil-text-secondary">Total</th>
                      <th className="px-5 py-3 text-left font-semibold text-agil-text-secondary">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.ultimas_ventas.map((v) => (
                      <tr
                        key={v.id}
                        className="border-b border-agil-border-subtle hover:bg-agil-bg-main/50 transition-colors"
                      >
                        <td className="px-5 py-3 text-agil-text-primary font-medium">{v.numero_control}</td>
                        <td className="px-5 py-3 text-agil-text-secondary truncate max-w-[200px]">{v.cliente}</td>
                        <td className="px-5 py-3 text-right text-agil-text-primary font-medium">
                          {formatCurrency(v.total)}
                        </td>
                        <td className="px-5 py-3">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded-lg text-xs font-medium ${
                              v.estado === 'AceptadoMH'
                                ? 'bg-[#D1FAE5] text-agil-success'
                                : v.estado === 'Enviado'
                                  ? 'bg-[#DBEAFE] text-agil-primary'
                                  : v.estado === 'Borrador'
                                    ? 'bg-agil-bg-main text-agil-text-secondary'
                                    : 'bg-agil-orange-light text-agil-orange'
                            }`}
                          >
                            {v.estado}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
