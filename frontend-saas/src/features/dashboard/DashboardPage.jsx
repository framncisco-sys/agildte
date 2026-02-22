import { useState, useEffect } from 'react'
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
import { useEmpresaStore } from '../../stores/useEmpresaStore'

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 animate-pulse">
      <div className="h-5 w-20 bg-gray-200 rounded mb-3" />
      <div className="h-8 w-24 bg-gray-200 rounded" />
    </div>
  )
}

function SkeletonChart() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 animate-pulse">
      <div className="h-6 w-56 bg-gray-200 rounded mb-4" />
      <div className="h-64 bg-gray-100 rounded" />
    </div>
  )
}

export function DashboardPage() {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const empresaNombre = useEmpresaStore((s) => s.empresaNombre)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!empresaId) {
      setLoading(false)
      setStats(null)
      setError(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    setStats(null)
    getDashboardStats(empresaId)
      .then((data) => {
        if (!cancelled) {
          setStats(data)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.response?.data?.detail ?? err.message ?? 'Error al cargar estadísticas')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [empresaId])

  const formatCurrency = (n) =>
    typeof n === 'number' ? `$ ${n.toLocaleString('es-SV', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '$ 0.00'

  const chartData = stats?.ventas_por_dia ?? []
  const hasChartData = chartData.some((d) => Number(d.total) > 0)

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Dashboard</h1>
        <p className="mt-1 text-gray-500 text-sm">
          Métricas de facturación del mes actual
          {empresaNombre && <span className="ml-1 font-medium text-blue-600">— {empresaNombre}</span>}
        </p>
      </div>

      {!empresaId && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 text-sm">
          Selecciona una empresa en la barra superior para ver las estadísticas.
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm">
          {error}
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
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex items-start gap-4">
              <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
                <DollarSign size={24} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Ventas del mes</p>
                <p className="text-2xl font-bold text-gray-900 mt-0.5">
                  {formatCurrency(stats?.total_ventas_mes ?? 0)}
                </p>
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex items-start gap-4">
              <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
                <FileText size={24} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">DTEs emitidos (mes)</p>
                <p className="text-2xl font-bold text-gray-900 mt-0.5">
                  {stats?.cantidad_dtes_mes ?? 0}
                </p>
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex items-start gap-4">
              <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
                <TrendingUp size={24} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Ventas hoy</p>
                <p className="text-2xl font-bold text-gray-900 mt-0.5">
                  {formatCurrency(stats?.ventas_hoy ?? 0)}
                </p>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Sección media: Gráfico de tendencia */}
      <div className="w-full lg:w-2/3 min-w-0">
        {loading ? (
          <SkeletonChart />
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 sm:p-5 overflow-hidden">
            <h2 className="text-base sm:text-lg font-semibold text-gray-800 mb-4">
              Comportamiento de Ventas (Este Mes)
            </h2>
            {chartData.length === 0 ? (
              <div className="h-48 sm:h-64 flex items-center justify-center text-gray-400 text-sm border border-dashed border-gray-200 rounded-lg">
                No hay datos del mes para mostrar
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={260} minHeight={220}>
                <AreaChart
                  data={chartData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
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
                    stroke="#4F46E5"
                    strokeWidth={2}
                    fill="url(#colorTotal)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        )}
      </div>

      {/* Sección inferior: Últimos documentos emitidos */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden min-w-0">
        <h2 className="text-base sm:text-lg font-semibold text-gray-800 px-4 sm:px-5 py-4 border-b border-gray-100">
          Últimos Documentos Emitidos
        </h2>
        {loading ? (
          <div className="p-4 sm:p-5 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            {/* Móvil: cards */}
            {stats?.ultimas_ventas?.length > 0 && (
              <div className="md:hidden divide-y divide-gray-100">
                {stats.ultimas_ventas.map((v) => (
                  <div key={v.id} className="p-4 space-y-1">
                    <p className="font-medium text-gray-800">{v.numero_control}</p>
                    <p className="text-sm text-gray-600 truncate">{v.cliente}</p>
                    <p className="text-sm font-medium text-gray-900">{formatCurrency(v.total)}</p>
                    <span
                      className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        v.estado === 'AceptadoMH' ? 'bg-green-100 text-green-800'
                          : v.estado === 'Enviado' ? 'bg-blue-100 text-blue-800'
                          : v.estado === 'Borrador' ? 'bg-gray-100 text-gray-700'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {v.estado}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {/* Escritorio: tabla con scroll horizontal */}
            <div className="overflow-x-auto">
            {(!stats?.ultimas_ventas || stats.ultimas_ventas.length === 0) ? (
              <p className="text-gray-500 text-sm px-4 sm:px-5 py-8 text-center">
                No hay documentos recientes
              </p>
            ) : (
              <table className="w-full text-sm min-w-[400px] hidden md:table">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="px-5 py-3 text-left font-semibold text-gray-600">Nº Control</th>
                    <th className="px-5 py-3 text-left font-semibold text-gray-600">Cliente</th>
                    <th className="px-5 py-3 text-right font-semibold text-gray-600">Total</th>
                    <th className="px-5 py-3 text-left font-semibold text-gray-600">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.ultimas_ventas.map((v) => (
                    <tr
                      key={v.id}
                      className="border-b border-gray-100 hover:bg-gray-50/50 transition-colors"
                    >
                      <td className="px-5 py-3 text-gray-800 font-medium">{v.numero_control}</td>
                      <td className="px-5 py-3 text-gray-600 truncate max-w-[200px]">{v.cliente}</td>
                      <td className="px-5 py-3 text-right text-gray-800 font-medium">
                        {formatCurrency(v.total)}
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                            v.estado === 'AceptadoMH'
                              ? 'bg-green-100 text-green-800'
                              : v.estado === 'Enviado'
                                ? 'bg-blue-100 text-blue-800'
                                : v.estado === 'Borrador'
                                  ? 'bg-gray-100 text-gray-700'
                                  : 'bg-amber-100 text-amber-800'
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
