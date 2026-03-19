import { useState } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from 'react-router-dom'
import { Trash2, Search, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'
import { crearPlantilla } from '../../../api/plantillas'
import { ModalBuscadorCliente } from '../components/ModalBuscadorCliente'
import { ItemDescripcionCombobox } from '../components/ItemDescripcionCombobox'
import { ModalCatalogoItems } from '../components/ModalCatalogoItems'
import { ModalControlarPlantillas } from '../components/ModalControlarPlantillas'

const schema = z.object({
  nombrePlantilla: z.string().min(1, 'El nombre de la plantilla es obligatorio'),
  tipoDte: z.enum(['01', '03']).default('01'),
  items: z.array(
    z.object({
      cantidad: z.coerce.number().min(0.01, 'Cantidad requerida'),
      descripcion: z.string().min(1, 'Descripción requerida'),
      precioUnitario: z.coerce.number().min(0, 'Precio requerido'),
    })
  ).min(1, 'Debe agregar al menos un ítem'),
})

const defaultValues = {
  nombrePlantilla: '',
  tipoDte: '01',
  items: [{ cantidad: 1, descripcion: '', precioUnitario: 0 }],
}

export function PlantillasRapidasPage() {
  const navigate = useNavigate()
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [clienteSeleccionado, setClienteSeleccionado] = useState(null)
  const [modalClienteAbierto, setModalClienteAbierto] = useState(false)
  const [catalogRowIndex, setCatalogRowIndex] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [modalControlarAbierto, setModalControlarAbierto] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    control,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues,
  })

  const { fields, append, remove, replace } = useFieldArray({ control, name: 'items' })
  const items = watch('items')
  const tipoDte = watch('tipoDte')

  const onClienteSeleccionado = (cliente) => {
    setClienteSeleccionado(cliente ? { id: cliente.id, nombre: cliente.nombre } : null)
  }

  const onSubmit = async (data) => {
    if (!empresaId) {
      toast.error('Selecciona una empresa antes de crear una plantilla.')
      return
    }
    setEnviando(true)
    try {
      const payload = {
        nombre: data.nombrePlantilla.trim(),
        empresa_id: empresaId,
        tipo_dte: data.tipoDte,
        cliente_id: clienteSeleccionado?.id ?? null,
        items: (items || []).map((it, idx) => ({
          cantidad: Number(it.cantidad) || 0,
          descripcion_libre: it.descripcion || '',
          precio_unitario: Number(it.precioUnitario) || 0,
          numero_item: idx + 1,
        })),
      }
      const creada = await crearPlantilla(payload)
      toast.success('Plantilla creada correctamente.')
      // Redirigir directamente a Nueva Factura usando la plantilla recién creada
      navigate(`/facturacion/nueva?plantillaId=${creada.id}`)
    } catch (err) {
      const d = err.response?.data
      const msg =
        d?.detail ||
        d?.error ||
        (typeof d === 'string' ? d : null) ||
        err.message ||
        'Error al crear la plantilla.'
      toast.error(msg)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-800">Crear Plantilla Rápida</h1>
          <p className="text-sm text-gray-600">
            Guarda un modelo de factura frecuente para reutilizarlo con un solo clic.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Nombre y tipo de documento */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre de la plantilla <span className="text-red-500">*</span>
              </label>
              <input
                {...register('nombrePlantilla')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ej: Alquiler Mensual, Servicios de Mantenimiento, etc."
              />
              {errors.nombrePlantilla && (
                <p className="mt-1 text-sm text-red-600">{errors.nombrePlantilla.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de documento por defecto
              </label>
              <select
                {...register('tipoDte')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="01">Factura Consumidor Final (01)</option>
                <option value="03">Crédito Fiscal (03)</option>
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Esto define el tipo de factura cuando uses la plantilla.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cliente predeterminado
              </label>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value={clienteSeleccionado?.nombre || ''}
                  placeholder="Sin cliente asignado"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                />
                <button
                  type="button"
                  onClick={() => setModalClienteAbierto(true)}
                  className="inline-flex items-center gap-1 px-3 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700"
                >
                  <Search size={16} />
                  Buscar
                </button>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Opcional. Podrás cambiar el cliente al usar la plantilla.
              </p>
            </div>
          </div>
        </section>

        {/* Ítems de la plantilla */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6 min-w-0">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4">
            <h2 className="text-base sm:text-lg font-medium text-gray-800">
              Ítems predeterminados
            </h2>
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
                  <th className="py-2 px-2 sm:px-3 w-28 sm:w-36 text-right">Subtotal</th>
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
                          step="0.00000001"
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

        <section className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => setModalControlarAbierto(true)}
            className="px-6 py-3 bg-gray-600 text-white font-medium rounded-lg hover:bg-gray-700 transition-colors"
          >
            Controlar plantillas rápidas
          </button>
          <button
            type="submit"
            disabled={enviando}
            className="px-8 py-3 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 disabled:opacity-70 disabled:cursor-not-allowed transition-colors inline-flex items-center justify-center gap-2"
          >
            {enviando && <Loader2 size={18} className="animate-spin" />}
            {enviando ? 'Guardando...' : 'Guardar Plantilla'}
          </button>
        </section>
      </form>

      <ModalBuscadorCliente
        isOpen={modalClienteAbierto}
        onClose={() => setModalClienteAbierto(false)}
        onSelect={(cliente) => {
          onClienteSeleccionado(cliente)
          setModalClienteAbierto(false)
        }}
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

      <ModalControlarPlantillas
        isOpen={modalControlarAbierto}
        onClose={() => setModalControlarAbierto(false)}
        onCambio={() => window.dispatchEvent(new CustomEvent('plantillas-actualizadas'))}
      />
    </div>
  )
}

