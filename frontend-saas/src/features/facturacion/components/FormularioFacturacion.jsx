import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm, useFieldArray } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Trash2, Loader2, Search, FileText } from 'lucide-react'
import toast from 'react-hot-toast'
import { ModalBuscadorCliente } from './ModalBuscadorCliente'
import { BuscarDocumentoModal } from './BuscarDocumentoModal'
import { DEPARTAMENTOS, MUNICIPIOS_POR_DEPARTAMENTO } from '../../../data/departamentos-municipios'
import { crearVenta } from '../../../api/facturas'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'

const TITULOS_POR_TIPO = {
  '01': 'NUEVA FACTURA CONSUMIDOR FINAL',
  '03': 'NUEVO CRÉDITO FISCAL',
  '05': 'NUEVA NOTA DE CRÉDITO',
  '06': 'NUEVA NOTA DE DÉBITO',
  '14': 'FACTURA SUJETO EXCLUIDO',
  '07': 'COMPROBANTE DE RETENCIÓN',
}

const schema = z.object({
  nombreCompleto: z.string().min(1, 'Nombre o razón social es requerido'),
  nombreComercial: z.string().optional(),
  tipoDocCliente: z.enum(['NIT', 'DUI']),
  numeroDocumento: z.string().optional(),
  correo: z.union([z.string().email('Correo inválido'), z.literal('')]),
  telefono: z.string().optional(),
  departamento: z.string().optional(),
  municipio: z.string().optional(),
  direccion: z.string().optional(),
  items: z.array(
    z.object({
      cantidad: z.coerce.number().min(0.01, 'Cantidad requerida'),
      descripcion: z.string().min(1, 'Descripción requerida'),
      precioUnitario: z.coerce.number().min(0, 'Precio requerido'),
    })
  ).min(1, 'Debe agregar al menos un ítem'),
})

const defaultValues = {
  nombreCompleto: '',
  nombreComercial: '',
  tipoDocCliente: 'NIT',
  numeroDocumento: '',
  correo: '',
  telefono: '',
  departamento: '06',
  municipio: '14',
  direccion: '',
  items: [{ cantidad: 1, descripcion: '', precioUnitario: 0 }],
}

export function FormularioFacturacion({ tipoDocumento, onChangeTipo }) {
  const navigate = useNavigate()
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [clienteIdSeleccionado, setClienteIdSeleccionado] = useState(null)
  const [documentoRelacionado, setDocumentoRelacionado] = useState(null)
  const [errorDocumentoRelacionado, setErrorDocumentoRelacionado] = useState('')
  const [modalDocumentoAbierto, setModalDocumentoAbierto] = useState(false)
  const requiereDocumentoRelacionado = tipoDocumento === '05' || tipoDocumento === '06'

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    control,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues,
  })

  const { fields, append, remove, replace } = useFieldArray({ control, name: 'items' })
  const items = watch('items')
  const departamentoSeleccionado = watch('departamento')
  const municipios = MUNICIPIOS_POR_DEPARTAMENTO[departamentoSeleccionado] ?? []

  const totalGravadas = (items ?? []).reduce(
    (sum, it) => sum + (Number(it.cantidad) || 0) * (Number(it.precioUnitario) || 0),
    0
  )
  const esCreditoFiscal = ['03', '05', '06'].includes(tipoDocumento)
  const iva = esCreditoFiscal ? totalGravadas * 0.13 : 0
  const totalPagar = totalGravadas + iva

  const onClienteSeleccionado = (cliente) => {
    setClienteIdSeleccionado(cliente?.id ?? null)
    const tieneNit = !!cliente.nit
    const tieneDui = !!cliente.dui
    const tipoDoc = tieneNit ? 'NIT' : tieneDui ? 'DUI' : 'NIT'
    const numeroDoc = tipoDoc === 'NIT' ? (cliente.nit ?? cliente.nrc ?? '') : (cliente.dui ?? '')
    setValue('nombreCompleto', cliente.nombre ?? '')
    setValue('nombreComercial', cliente.giro ?? '')
    setValue('tipoDocCliente', tipoDoc)
    setValue('numeroDocumento', numeroDoc)
    setValue('correo', cliente.email_contacto ?? '')
    setValue('telefono', cliente.telefono ?? '')
    setValue('departamento', cliente.departamento ?? '06')
    setValue('municipio', cliente.municipio ?? '14')
    setValue('direccion', cliente.direccion ?? '')
  }

  /**
   * Al seleccionar un documento en el modal: vincula relación MH, carga cliente e ítems.
   */
  const handleDocumentoSeleccionado = (venta) => {
    if (!venta) return
    setErrorDocumentoRelacionado('')
    setDocumentoRelacionado({
      tipoDte: venta.tipo_venta === 'CF' ? '01' : '03',
      codigoGeneracion: venta.codigo_generacion || venta.codigoGeneracion,
      fechaEmision: venta.fecha_emision || venta.fechaEmision || venta.fecha_hora_emision?.slice(0, 10),
      numeroControl: venta.numero_control || venta.numeroControl,
      nombreReceptor: venta.nombre_receptor || venta.nombreReceptor || venta.cliente?.nombre,
    })

    const cliente = venta.cliente
    if (cliente && typeof cliente === 'object') {
      onClienteSeleccionado(cliente)
    } else {
      const clienteId = venta.cliente_id ?? (typeof venta.cliente === 'object' ? venta.cliente?.id : null)
      setClienteIdSeleccionado(clienteId ?? null)
      setValue('nombreCompleto', venta.nombre_receptor || venta.nombreReceptor || '')
      setValue('nombreComercial', venta.nombre_receptor || '')
      const nit = venta.nit_receptor
      const nrc = venta.nrc_receptor
      const tieneNit = !!nit || !!nrc
      setValue('tipoDocCliente', tieneNit ? 'NIT' : 'DUI')
      setValue('numeroDocumento', tieneNit ? (nit || nrc || '') : (venta.documento_receptor || ''))
      setValue('correo', venta.correo_receptor || venta.correoReceptor || '')
      setValue('telefono', venta.telefono_receptor || venta.telefonoReceptor || '')
      setValue('departamento', venta.departamento_receptor || venta.cliente?.departamento || '06')
      setValue('municipio', venta.municipio_receptor || venta.cliente?.municipio || '14')
      setValue('direccion', venta.direccion_receptor || venta.direccionReceptor || '')
    }

    const detalles = venta.detalles || []
    if (detalles.length > 0) {
      const itemsForm = detalles.map((d) => ({
        cantidad: Number(d.cantidad) || 0,
        descripcion: d.descripcion_libre || d.producto?.descripcion || '',
        precioUnitario: Number(d.precio_unitario) || 0,
      }))
      replace(itemsForm)
    }
    toast.success('Documento, cliente e ítems cargados')
  }

  const handleLimpiarDocumentoRelacionado = () => {
    setDocumentoRelacionado(null)
    setErrorDocumentoRelacionado('')
  }

  const onSubmit = async (data) => {
    if (!empresaId) {
      toast.error('Selecciona una empresa antes de emitir')
      return
    }
    if (requiereDocumentoRelacionado && !documentoRelacionado?.codigoGeneracion) {
      setErrorDocumentoRelacionado('Debes seleccionar el documento que se modificará (factura original)')
      toast.error('Selecciona el documento relacionado')
      return
    }
    setErrorDocumentoRelacionado('')
    setEnviando(true)
    try {
      const payload = {
        tipoDocumento,
        empresaId,
        clienteId: clienteIdSeleccionado,
        documentoRelacionado: requiereDocumentoRelacionado ? documentoRelacionado : null,
        cliente: {
          nombreCompleto: data.nombreCompleto,
          nombreComercial: data.nombreComercial,
          tipoDocCliente: data.tipoDocCliente,
          numeroDocumento: data.numeroDocumento,
          correo: data.correo,
          telefono: data.telefono,
          departamento: data.departamento,
          municipio: data.municipio,
          direccion: data.direccion,
        },
        items: data.items,
        totalGravadas,
        iva: esCreditoFiscal ? iva : 0,
      }
      const respuesta = await crearVenta(payload)
      const estado = respuesta?.estado_dte || respuesta?.estado
      const mensaje = respuesta?.mensaje

      if (estado === 'AceptadoMH' || estado === 'PROCESADO') {
        toast.success(mensaje || '¡Factura enviada a Hacienda correctamente!')
        navigate('/dashboard')
      } else if (estado === 'RechazadoMH' || estado === 'RECHAZADO') {
        toast.error(mensaje || 'Factura rechazada por Hacienda')
      } else {
        toast.success(mensaje || 'Documento guardado')
        navigate('/dashboard')
      }
    } catch (err) {
      const d = err.response?.data
      let msg = d?.error ?? d?.mensaje ?? err.message ?? 'Error al emitir el documento'
      if (typeof d === 'string') msg = d
      else if (d && typeof d === 'object' && !d.error && !d.mensaje) {
        const parts = Object.entries(d).map(([k, v]) => {
          const val = Array.isArray(v) ? v.join(', ') : String(v)
          return `${k}: ${val}`
        })
        if (parts.length) msg = parts.join(' | ')
      }
      toast.error(msg)
    } finally {
      setEnviando(false)
    }
  }

  const titulo = TITULOS_POR_TIPO[tipoDocumento] ?? 'NUEVO DOCUMENTO'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <h1 className="text-xl font-semibold text-gray-800">Nueva Factura</h1>
        <button
          type="button"
          onClick={onChangeTipo}
          className="text-sm text-gray-500 hover:text-gray-700 underline shrink-0"
        >
          Cambiar Tipo
        </button>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Sección 1: Encabezado */}
        <section className={`rounded-xl px-6 py-4 ${requiereDocumentoRelacionado ? 'bg-amber-50 border-2 border-amber-200' : 'bg-slate-100'}`}>
          <h2 className="text-lg font-semibold text-gray-800">{titulo}</h2>
        </section>

        {/* Sección 1b: Documento a Modificar (solo NC/ND) */}
        {requiereDocumentoRelacionado && (
          <section className="bg-white rounded-xl shadow-sm border-2 border-amber-200 p-6">
            <h2 className="text-lg font-medium text-amber-800 mb-3 flex items-center gap-2">
              Documento a Modificar
              <span className="text-sm font-normal text-amber-600">(requerido)</span>
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              Busca la factura original (CF o CCF) ya procesada por Hacienda que deseas anular o corregir.
            </p>
            {documentoRelacionado ? (
              <div className="flex items-center justify-between gap-3 p-4 rounded-xl border-2 border-amber-300 bg-amber-50">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 rounded-lg bg-amber-100">
                    <FileText size={20} className="text-amber-700" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-gray-800">
                      Documento Relacionado: {documentoRelacionado.numeroControl || documentoRelacionado.codigoGeneracion?.slice(0, 8) + '...'}
                    </p>
                    <p className="text-sm text-gray-600">
                      {documentoRelacionado.fechaEmision} · DTE-{documentoRelacionado.tipoDte}
                      {documentoRelacionado.nombreReceptor && ` · ${documentoRelacionado.nombreReceptor}`}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleLimpiarDocumentoRelacionado}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-amber-700 hover:bg-amber-200 transition-colors shrink-0"
                  title="Cambiar / Eliminar documento"
                >
                  <Trash2 size={18} />
                  Cambiar
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setModalDocumentoAbierto(true)}
                className="w-full flex items-center justify-center gap-3 py-4 px-6 rounded-xl border-2 border-amber-300 bg-amber-50 hover:bg-amber-100 hover:border-amber-400 transition-colors text-amber-800 font-medium"
              >
                <Search size={24} />
                Buscar Documento Origen
              </button>
            )}
            {errorDocumentoRelacionado && (
              <p className="mt-2 text-sm text-red-600">{errorDocumentoRelacionado}</p>
            )}
          </section>
        )}

        <BuscarDocumentoModal
          isOpen={modalDocumentoAbierto}
          onClose={() => setModalDocumentoAbierto(false)}
          onSelect={handleDocumentoSeleccionado}
        />

        {/* Sección 2: Cliente */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <h2 className="text-lg font-medium text-gray-800">Datos del Cliente</h2>
            <button
              type="button"
              onClick={() => setModalAbierto(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shrink-0"
            >
              CARGAR CLIENTE
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="sm:col-span-2 lg:col-span-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre Completo / Razón Social
              </label>
              <input
                {...register('nombreCompleto')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Razón social o nombre completo"
              />
              {errors.nombreCompleto && (
                <p className="mt-1 text-sm text-red-600">{errors.nombreCompleto.message}</p>
              )}
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre Comercial <span className="text-gray-400">(Opcional)</span>
              </label>
              <input
                {...register('nombreComercial')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Nombre comercial"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo Documento</label>
              <select
                {...register('tipoDocCliente')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="NIT">NIT</option>
                <option value="DUI">DUI</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Número Documento</label>
              <input
                {...register('numeroDocumento')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="NIT o DUI"
              />
              {errors.numeroDocumento && (
                <p className="mt-1 text-sm text-red-600">{errors.numeroDocumento.message}</p>
              )}
            </div>
            <div className="sm:col-span-2 lg:col-span-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Correo Electrónico</label>
              <input
                type="email"
                {...register('correo')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="correo@ejemplo.com"
              />
              {errors.correo && (
                <p className="mt-1 text-sm text-red-600">{errors.correo.message}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
              <input
                {...register('telefono')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Teléfono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Departamento</label>
              <select
                {...register('departamento')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {DEPARTAMENTOS.map((d) => (
                  <option key={d.codigo} value={d.codigo}>{d.nombre}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Municipio</label>
              <select
                {...register('municipio')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {municipios.map((m) => (
                  <option key={m.codigo} value={m.codigo}>{m.nombre}</option>
                ))}
              </select>
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">Dirección detallada</label>
              <input
                {...register('direccion')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Colonia, calle, número, etc."
              />
            </div>
          </div>
        </section>

        {/* Sección 3: Detalle de Productos */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-medium text-gray-800">Detalle de Productos</h2>
            <button
              type="button"
              onClick={() => append({ cantidad: 1, descripcion: '', precioUnitario: 0 })}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm"
            >
              + Agregar Ítem
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100 text-left text-gray-600">
                  <th className="py-2 px-3 w-24">Cantidad</th>
                  <th className="py-2 px-3">Descripción</th>
                  <th className="py-2 px-3 w-32">Precio Unit.</th>
                  <th className="py-2 px-3 w-36 text-right">Ventas Gravadas</th>
                  <th className="py-2 px-3 w-12"></th>
                </tr>
              </thead>
              <tbody>
                {fields.map((field, index) => {
                  const cant = Number(items?.[index]?.cantidad) || 0
                  const precio = Number(items?.[index]?.precioUnitario) || 0
                  const subtotal = cant * precio
                  return (
                    <tr
                      key={field.id}
                      className={`border-b border-gray-100 ${index % 2 === 1 ? 'bg-gray-50/50' : ''}`}
                    >
                      <td className="py-2 px-3">
                        <input
                          type="number"
                          step="0.01"
                          {...register(`items.${index}.cantidad`)}
                          className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                        />
                      </td>
                      <td className="py-2 px-3">
                        <input
                          {...register(`items.${index}.descripcion`)}
                          className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                          placeholder="Descripción"
                        />
                        {(errors.items?.[index]?.descripcion) && (
                          <p className="text-xs text-red-600 mt-0.5">
                            {errors.items[index].descripcion.message}
                          </p>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        <input
                          type="number"
                          step="0.01"
                          {...register(`items.${index}.precioUnitario`)}
                          className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                        />
                      </td>
                      <td className="py-2 px-3 text-right font-medium">
                        ${subtotal.toFixed(2)}
                      </td>
                      <td className="py-2 px-3">
                        <button
                          type="button"
                          onClick={() => remove(index)}
                          className="p-2 text-red-500 hover:bg-red-50 rounded transition-colors"
                          aria-label="Eliminar"
                        >
                          <Trash2 size={18} />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {(errors.items?.message || errors.items?.root?.message) && (
            <p className="mt-2 text-sm text-red-600">
              {errors.items?.message ?? errors.items?.root?.message}
            </p>
          )}
        </section>

        {/* Sección 4: Resumen y Totales */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="max-w-xs ml-auto space-y-2">
            <div className="flex justify-between text-gray-600">
              <span>Total Gravadas:</span>
              <span>${totalGravadas.toFixed(2)}</span>
            </div>
            {esCreditoFiscal && (
              <div className="flex justify-between text-gray-600">
                <span>IVA (13%):</span>
                <span>${iva.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between text-lg font-bold text-gray-800 pt-2 border-t border-gray-200">
              <span>Total a Pagar:</span>
              <span>${totalPagar.toFixed(2)}</span>
            </div>
          </div>
          <div className="mt-6">
            <button
              type="submit"
              disabled={enviando}
              className="w-full sm:w-auto px-8 py-3 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 disabled:opacity-70 disabled:cursor-not-allowed transition-colors inline-flex items-center justify-center gap-2"
            >
              {enviando && <Loader2 size={20} className="animate-spin" />}
              {enviando ? 'Enviando...' : 'EMITIR DOCUMENTO'}
            </button>
          </div>
        </section>
      </form>

      <ModalBuscadorCliente
        isOpen={modalAbierto}
        onClose={() => setModalAbierto(false)}
        onSelect={onClienteSeleccionado}
      />
    </div>
  )
}
