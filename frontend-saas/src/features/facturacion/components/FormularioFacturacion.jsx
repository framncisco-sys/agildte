import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm, useFieldArray } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Trash2, Loader2, Search, FileText, UserPlus } from 'lucide-react'
import toast from 'react-hot-toast'
import { ModalBuscadorCliente } from './ModalBuscadorCliente'
import { BuscarDocumentoModal } from './BuscarDocumentoModal'
import { ItemDescripcionCombobox } from './ItemDescripcionCombobox'
import { ModalCatalogoItems } from './ModalCatalogoItems'
import { BuscadorActividad } from '../../../components/BuscadorActividad'
import { DEPARTAMENTOS, MUNICIPIOS_POR_DEPARTAMENTO } from '../../../data/departamentos-municipios'
import { crearVenta } from '../../../api/facturas'
import { createCliente } from '../../../api/clientes'
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
  nrc: z.string().optional(),
  codActividad: z.string().optional(),
  descActividad: z.string().optional(),
  correo: z.union([z.string().email('Correo inválido'), z.literal('')]),
  telefono: z.string().optional(),
  departamento: z.string().optional(),
  municipio: z.string().optional(),
  direccion: z.string().optional(),
  condicionOperacion: z.enum(['1', '2', '3']).default('1'),
  plazoPago: z.string().optional(),
  periodoPago: z.string().optional(),
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
  nrc: '',
  codActividad: '',
  descActividad: '',
  correo: '',
  telefono: '',
  departamento: '06',
  municipio: '20',
  direccion: '',
  condicionOperacion: '1',
  plazoPago: '03',
  periodoPago: '30',
  items: [{ cantidad: 1, descripcion: '', precioUnitario: 0 }],
}

export function FormularioFacturacion({ tipoDocumento, onChangeTipo }) {
  const navigate = useNavigate()
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [guardandoCliente, setGuardandoCliente] = useState(false)
  const [clienteIdSeleccionado, setClienteIdSeleccionado] = useState(null)
  const [documentoRelacionado, setDocumentoRelacionado] = useState(null)
  const [errorDocumentoRelacionado, setErrorDocumentoRelacionado] = useState('')
  const [modalDocumentoAbierto, setModalDocumentoAbierto] = useState(false)
  const [catalogRowIndex, setCatalogRowIndex] = useState(null)
  const [actividadDisplay, setActividadDisplay] = useState('')
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
  const condicionOperacionWatch = watch('condicionOperacion')
  const esCredito = condicionOperacionWatch === '2'
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
    const numeroDoc = tipoDoc === 'NIT' ? (cliente.nit ?? cliente.documento_identidad ?? '') : (cliente.dui ?? cliente.documento_identidad ?? '')
    setValue('nombreCompleto', cliente.nombre ?? '')
    setValue('nombreComercial', cliente.giro ?? '')
    setValue('tipoDocCliente', tipoDoc)
    setValue('numeroDocumento', numeroDoc)
    setValue('nrc', cliente.nrc ?? '')
    setValue('codActividad', cliente.cod_actividad ?? cliente.actividad_economica ?? '')
    setValue('descActividad', cliente.desc_actividad ?? '')
    const codAct = cliente.cod_actividad ?? cliente.actividad_economica ?? ''
    const descAct = cliente.desc_actividad ?? ''
    setActividadDisplay(codAct && descAct ? `${codAct} - ${descAct}` : codAct)
    setValue('correo', cliente.email_contacto ?? cliente.correo ?? '')
    setValue('telefono', cliente.telefono ?? '')
    setValue('departamento', cliente.departamento ?? '06')
    setValue('municipio', cliente.municipio ?? '20')
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

  const handleGuardarCliente = async () => {
    const data = watch()
    if (!data.nombreCompleto?.trim()) {
      toast.error('Ingresa el nombre del cliente antes de guardar.')
      return
    }
    if (!empresaId) {
      toast.error('Selecciona una empresa primero.')
      return
    }
    setGuardandoCliente(true)
    try {
      const payload = {
        nombre: data.nombreCompleto.trim(),
        tipo_documento: data.tipoDocCliente ?? 'NIT',
        documento_identidad: data.numeroDocumento?.trim() || null,
        nrc: data.nrc?.trim() || null,
        actividad_economica: data.codActividad?.trim() || null,
        correo: data.correo?.trim() || null,
        telefono: data.telefono?.trim() || null,
        direccion_departamento: data.departamento || '06',
        direccion_municipio: data.municipio || '20',
        direccion_complemento: data.direccion?.trim() || null,
        empresa_id: empresaId,
      }
      const nuevo = await createCliente(payload)
      setClienteIdSeleccionado(nuevo.id)
      toast.success(`Cliente "${data.nombreCompleto.trim()}" guardado correctamente.`)
    } catch (err) {
      const d = err.response?.data
      const msg = d?.nrc?.[0] ?? d?.documento_identidad?.[0] ?? d?.error ?? d?.detail ?? err.message ?? 'Error al guardar cliente.'
      toast.error(msg)
    } finally {
      setGuardandoCliente(false)
    }
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

    // FSE: validar que el número de documento del proveedor sea DUI (9 dígitos) o NIT (14 dígitos)
    if (tipoDocumento === '14') {
      const docLimpio = (data.numeroDocumento || '').replace(/\D/g, '')
      if (docLimpio.length !== 9 && docLimpio.length !== 14) {
        toast.error('Para Sujeto Excluido ingresa el DUI (9 dígitos) o NIT (14 dígitos) del proveedor')
        return
      }
    }
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
          nrc: data.nrc,
          codActividad: data.codActividad,
          descActividad: data.descActividad,
          correo: data.correo,
          telefono: data.telefono,
          departamento: data.departamento,
          municipio: data.municipio,
          direccion: data.direccion,
          condicionOperacion: data.condicionOperacion,
        },
        items: data.items,
        totalGravadas,
        iva: esCreditoFiscal ? iva : 0,
        condicionOperacion: Number(data.condicionOperacion ?? 1),
        // plazo_pago → código de unidad MH: "01"=Días, "02"=Semanas, "03"=Meses
        plazoPago: data.condicionOperacion === '2' ? (data.plazoPago || '03') : null,
        // periodo_pago → cantidad numérica (ej: 30)
        periodoPago: data.condicionOperacion === '2' ? (Number(data.periodoPago) || 30) : null,
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

        {/* Sección 2: Datos del Receptor / Proveedor (FSE) */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          {/* Encabezado de sección */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5 pb-4 border-b border-gray-100">
            <div>
              <h2 className="text-base font-semibold text-blue-800 uppercase tracking-wide">
                {tipoDocumento === '14' ? 'Información del Proveedor (Sujeto Excluido)' : 'Información del Receptor'}
              </h2>
              {tipoDocumento === '14' && (
                <p className="text-xs text-amber-600 mt-0.5">Datos de quien te vendió sin emitir DTE</p>
              )}
            </div>
            {tipoDocumento !== '14' && (
              <button
                type="button"
                onClick={() => setModalAbierto(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium shrink-0"
              >
                <Search size={16} />
                CARGAR CLIENTE
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Nombre completo — fila completa */}
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre completo / Razón Social <span className="text-red-500">*</span>
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

            {/* Nombre comercial — fila completa */}
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre Comercial <span className="text-gray-400 font-normal">(Opcional)</span>
              </label>
              <input
                {...register('nombreComercial')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Nombre comercial"
              />
            </div>

            {/* NIT */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                NIT {tipoDocumento === '14' && <span className="text-red-500">*</span>}
              </label>
              <input
                {...register('numeroDocumento')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder={tipoDocumento === '14' ? 'DUI (9 dígitos) o NIT (14 dígitos)' : 'NIT del receptor'}
              />
              {errors.numeroDocumento && (
                <p className="mt-1 text-sm text-red-600">{errors.numeroDocumento.message}</p>
              )}
            </div>

            {/* NRC (solo para CCF y similares) */}
            {tipoDocumento !== '14' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">NRC</label>
                <input
                  {...register('nrc')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Número de Registro de Contribuyente"
                />
              </div>
            )}

            {/* Descripción Actividad */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Descripción Act.</label>
              <input
                {...register('descActividad')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Descripción de la actividad económica"
              />
            </div>

            {/* Código Actividad Económica con buscador */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Código Act. Ec.</label>
              <BuscadorActividad
                value={watch('codActividad') ?? ''}
                displayValue={actividadDisplay}
                onChange={(codigo) => setValue('codActividad', codigo)}
                onDisplayChange={(display) => {
                  setActividadDisplay(display)
                  const desc = display.includes(' - ') ? display.split(' - ').slice(1).join(' - ') : display
                  setValue('descActividad', desc)
                }}
                placeholder="Buscar actividad (mín. 2 caracteres)"
              />
            </div>

            {/* Departamento */}
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

            {/* Municipio */}
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

            {/* Dirección — fila completa */}
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Dirección</label>
              <input
                {...register('direccion')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Colonia, calle, número, etc."
              />
            </div>

            {/* Condición de la Operación */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Condición de la Operación</label>
              <select
                {...register('condicionOperacion')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="1">Contado</option>
                <option value="2">A Crédito</option>
                <option value="3">Otro</option>
              </select>
            </div>

            {/* Campos de crédito (solo visibles cuando condición = A Crédito) */}
            {esCredito && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Unidad de tiempo <span className="text-red-500">*</span>
                  </label>
                  <select
                    {...register('plazoPago')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="01">Días</option>
                    <option value="02">Semanas</option>
                    <option value="03">Meses</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500">Tipo de período del crédito</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cantidad <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    {...register('periodoPago')}
                    placeholder="Ej: 30"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">Número de días/semanas/meses (ej: 30)</p>
                </div>
              </>
            )}

            {/* Correo Electrónico */}
            <div>
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

            {/* Teléfono */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
              <input
                {...register('telefono')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Teléfono de contacto"
              />
            </div>
          </div>

          {/* Botón Guardar Cliente */}
          {tipoDocumento !== '14' && (
            <div className="mt-5 pt-4 border-t border-gray-100 flex items-center justify-between gap-3">
              <p className="text-xs text-gray-500">
                Guarda estos datos en la cartera de clientes para usarlos en futuras facturas.
              </p>
              <button
                type="button"
                onClick={handleGuardarCliente}
                disabled={guardandoCliente}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors text-sm font-medium shrink-0"
              >
                {guardandoCliente
                  ? <Loader2 size={16} className="animate-spin" />
                  : <UserPlus size={16} />
                }
                {guardandoCliente ? 'Guardando...' : 'Guardar Cliente (Clientes nuevos)'}
              </button>
            </div>
          )}
        </section>

        {/* Sección 3: Detalle de Productos */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6 min-w-0">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4">
            <h2 className="text-base sm:text-lg font-medium text-gray-800">Detalle de Productos</h2>
            <button
              type="button"
              onClick={() => append({ cantidad: 1, descripcion: '', precioUnitario: 0 })}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm"
            >
              + Agregar Ítem
            </button>
          </div>
          <div className="overflow-x-auto -mx-1 px-1">
            <table className="w-full text-sm min-w-[320px]">
              <thead>
                <tr className="bg-gray-100 text-left text-gray-600">
                  <th className="py-2 px-2 sm:px-3 w-20 sm:w-24">Cant.</th>
                  <th className="py-2 px-2 sm:px-3 min-w-[140px]">Descripción</th>
                  <th className="py-2 px-2 sm:px-3 w-24 sm:w-32">P. Unit.</th>
                  <th className="py-2 px-2 sm:px-3 w-28 sm:w-36 text-right">V. Gravadas</th>
                  <th className="py-2 px-2 sm:px-3 w-10"></th>
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
                      <td className="py-2 px-2 sm:px-3 min-w-0">
                        <div className="flex items-center gap-1 w-full min-w-0">
                          <div className="flex-1 min-w-0">
                            <ItemDescripcionCombobox
                              value={items?.[index]?.descripcion ?? ''}
                              onChange={(val) => setValue(`items.${index}.descripcion`, val)}
                              onSelectItem={({ descripcion, precio_unitario }) => {
                                setValue(`items.${index}.descripcion`, descripcion)
                                setValue(`items.${index}.precioUnitario`, precio_unitario)
                              }}
                              empresaId={empresaId}
                              placeholder="Buscar ítem o escribir..."
                              error={errors.items?.[index]?.descripcion?.message}
                            />
                          </div>
                          <button
                            type="button"
                            onClick={() => setCatalogRowIndex(index)}
                            className="flex-shrink-0 p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-400 touch-manipulation inline-flex items-center justify-center"
                            aria-label="Buscar en catálogo"
                            title="Buscar en catálogo"
                          >
                            <Search size={18} />
                          </button>
                        </div>
                      </td>
                      <td className="py-2 px-3">
                        <input
                          type="number"
                          step="0.01"
                          {...register(`items.${index}.precioUnitario`)}
                          className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 min-w-[4rem]"
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

      <ModalCatalogoItems
        isOpen={catalogRowIndex !== null}
        onClose={() => setCatalogRowIndex(null)}
        onSelect={(item) => {
          if (catalogRowIndex !== null) {
            setValue(`items.${catalogRowIndex}.descripcion`, item.descripcion)
            setValue(`items.${catalogRowIndex}.precioUnitario`, item.precio_unitario)
          }
          setCatalogRowIndex(null)
        }}
        empresaId={empresaId}
      />
    </div>
  )
}
