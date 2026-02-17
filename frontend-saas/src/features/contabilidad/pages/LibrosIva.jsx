import { useState } from 'react'
import { Search, FileDown, FileSpreadsheet } from 'lucide-react'
import { getLibroIvaPreview, getLibroIvaBlob } from '../../../api/librosIva'

const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

function formatNum(n) {
  if (n == null || n === '') return '0.00'
  const x = Number(n)
  return Number.isNaN(x) ? '0.00' : x.toLocaleString('es-SV', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function LibrosIva() {
  const currentYear = new Date().getFullYear()
  const [mes, setMes] = useState(new Date().getMonth() + 1)
  const [anio, setAnio] = useState(currentYear)
  const [tipoLibro, setTipoLibro] = useState('consumidor')
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [downloading, setDownloading] = useState(null)

  const handleGenerar = () => {
    setError(null)
    setPreview(null)
    setLoading(true)
    getLibroIvaPreview(mes, anio, tipoLibro)
      .then((data) => setPreview(data))
      .catch((err) => setError(err.response?.data?.error ?? err.message ?? 'Error al generar vista previa'))
      .finally(() => setLoading(false))
  }

  const handleDownload = async (format) => {
    setError(null)
    setDownloading(format)
    try {
      const blob = await getLibroIvaBlob(mes, anio, tipoLibro, format)
      const sufijo = tipoLibro === 'consumidor' ? 'CF' : 'CCF'
      const ext = format === 'pdf' ? 'pdf' : 'csv'
      const nombre = `LIBRO_VENTAS_${sufijo}_${preview?.empresa || 'reporte'}_${preview?.periodo || `${anio}-${String(mes).padStart(2, '0')}`}.${ext}`
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = nombre
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.response?.data?.error ?? err.message ?? `Error al descargar ${format.toUpperCase()}`)
    } finally {
      setDownloading(null)
    }
  }

  const datos = preview?.datos ?? []
  const totales = preview?.totales ?? {}
  const isConsumidor = tipoLibro === 'consumidor'

  return (
    <div className="p-4 sm:p-6 max-w-[1400px] mx-auto space-y-4 min-w-0">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800">Libros de IVA</h1>
        <p className="mt-1 text-gray-500 text-sm">Reportes de ventas para declaración de impuestos</p>
      </div>

      {/* Barra de herramientas */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Mes</label>
            <select
              value={mes}
              onChange={(e) => setMes(Number(e.target.value))}
              className="block w-40 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {MESES.map((nombre, i) => (
                <option key={i} value={i + 1}>{nombre}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Año</label>
            <input
              type="number"
              min={2020}
              max={2030}
              value={anio}
              onChange={(e) => setAnio(Number(e.target.value) || currentYear)}
              className="block w-24 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="flex rounded-lg overflow-hidden border border-gray-300">
            <button
              type="button"
              onClick={() => setTipoLibro('consumidor')}
              className={`px-4 py-2 text-sm font-medium ${tipoLibro === 'consumidor' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              Libro Consumidor Final
            </button>
            <button
              type="button"
              onClick={() => setTipoLibro('contribuyente')}
              className={`px-4 py-2 text-sm font-medium ${tipoLibro === 'contribuyente' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              Libro Contribuyentes
            </button>
          </div>
          <button
            type="button"
            onClick={handleGenerar}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Search className="h-4 w-4" />
            {loading ? 'Cargando…' : 'Generar vista previa'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Exportación */}
      {preview && (
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => handleDownload('pdf')}
            disabled={downloading !== null}
            className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            <FileDown className="h-4 w-4" />
            {downloading === 'pdf' ? 'Descargando…' : 'Descargar PDF'}
          </button>
          <button
            type="button"
            onClick={() => handleDownload('csv')}
            disabled={downloading !== null}
            className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            <FileSpreadsheet className="h-4 w-4" />
            {downloading === 'csv' ? 'Descargando…' : 'Descargar CSV/Excel'}
          </button>
        </div>
      )}

      {/* Tabla vista previa */}
      {preview && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden min-w-0">
          <div className="px-4 py-2 border-b border-gray-200 bg-gray-50 text-xs text-gray-600">
            {preview.empresa} — {preview.periodo} — {preview.total_registros} registro(s)
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-gray-100 text-gray-700 font-semibold">
                  {isConsumidor ? (
                    <>
                      <th className="text-left py-2 px-2 border border-gray-200">Fecha Emisión</th>
                      <th className="text-left py-2 px-2 border border-gray-200">Clase Doc.</th>
                      <th className="text-left py-2 px-2 border border-gray-200">Tipo</th>
                      <th className="text-left py-2 px-2 border border-gray-200">Nº Resolución</th>
                      <th className="text-left py-2 px-2 border border-gray-200">Serie</th>
                      <th className="text-left py-2 px-2 border border-gray-200">Nº Correlativo</th>
                      <th className="text-right py-2 px-2 border border-gray-200">Ventas Exentas</th>
                      <th className="text-right py-2 px-2 border border-gray-200">Ventas Gravadas</th>
                      <th className="text-right py-2 px-2 border border-gray-200">No Sujetas</th>
                      <th className="text-right py-2 px-2 border border-gray-200">Total Ventas</th>
                    </>
                  ) : (
                    <>
                      <th className="text-left py-2 px-2 border border-gray-200">Fecha Emisión</th>
                      <th className="text-left py-2 px-2 border border-gray-200">Nº Correlativo</th>
                      <th className="text-left py-2 px-2 border border-gray-200">Nombre Cliente</th>
                      <th className="text-left py-2 px-2 border border-gray-200">NRC Cliente</th>
                      <th className="text-right py-2 px-2 border border-gray-200">Monto Neto</th>
                      <th className="text-right py-2 px-2 border border-gray-200">Débito Fiscal</th>
                      <th className="text-right py-2 px-2 border border-gray-200">Total Venta</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {datos.map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    {isConsumidor ? (
                      <>
                        <td className="py-1.5 px-2 border border-gray-200">{row.fecha_emision}</td>
                        <td className="py-1.5 px-2 border border-gray-200">{row.clase_documento}</td>
                        <td className="py-1.5 px-2 border border-gray-200">{row.tipo_documento}</td>
                        <td className="py-1.5 px-2 border border-gray-200">{row.numero_resolucion}</td>
                        <td className="py-1.5 px-2 border border-gray-200">{row.serie}</td>
                        <td className="py-1.5 px-2 border border-gray-200">{row.numero_control}</td>
                        <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(row.ventas_exentas)}</td>
                        <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(row.ventas_internas_gravadas)}</td>
                        <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(row.ventas_no_sujetas)}</td>
                        <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(row.total_ventas)}</td>
                      </>
                    ) : (
                      <>
                        <td className="py-1.5 px-2 border border-gray-200">{row.fecha_emision}</td>
                        <td className="py-1.5 px-2 border border-gray-200">{row.numero_control}</td>
                        <td className="py-1.5 px-2 border border-gray-200">{row.nombre_cliente}</td>
                        <td className="py-1.5 px-2 border border-gray-200">{row.nrc_cliente}</td>
                        <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(row.monto_neto)}</td>
                        <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(row.debito_fiscal)}</td>
                        <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(row.total_venta)}</td>
                      </>
                    )}
                  </tr>
                ))}
                {/* Fila TOTALES */}
                <tr className="bg-gray-100 font-semibold">
                  {isConsumidor ? (
                    <>
                      <td colSpan={6} className="py-1.5 px-2 border border-gray-200 text-right">TOTALES</td>
                      <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(totales.ventas_exentas)}</td>
                      <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(totales.ventas_internas_gravadas)}</td>
                      <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(totales.ventas_no_sujetas)}</td>
                      <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(totales.total_ventas)}</td>
                    </>
                  ) : (
                    <>
                      <td colSpan={4} className="py-1.5 px-2 border border-gray-200 text-right">TOTALES</td>
                      <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(totales.monto_neto)}</td>
                      <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(totales.debito_fiscal)}</td>
                      <td className="py-1.5 px-2 border border-gray-200 text-right">{formatNum(totales.total_venta)}</td>
                    </>
                  )}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {preview && datos.length === 0 && (
        <p className="text-sm text-gray-500">No hay registros para el periodo y tipo de libro seleccionados.</p>
      )}
    </div>
  )
}
