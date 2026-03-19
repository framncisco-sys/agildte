import { useState, useEffect } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { X, Trash2, Search, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'
import { obtenerPlantilla, actualizarPlantilla } from '../../../api/plantillas'
import { ModalBuscadorCliente } from './ModalBuscadorCliente'
import { ItemDescripcionCombobox } from './ItemDescripcionCombobox'
import { ModalCatalogoItems } from './ModalCatalogoItems'

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

export function ModalEditarPlantilla({ plantillaId, isOpen, onClose, onGuardado }) {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [clienteSeleccionado, setClienteSeleccionado] = useState(null)
  const [modalClienteAbierto, setModalClienteAbierto] = useState(false)
  const [catalogRowIndex, setCatalogRowIndex] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [enviando, setEnviando] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    control,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      nombrePlantilla: '',
      tipoDte: '01',
      items: [{ cantidad: 1, descripcion: '', precioUnitario: 0 }],
    },
  })

  const { fields, append, remove, replace } = useFieldArray({ control, name: 'items' })
  const items = watch('items')

  useEffect(() => {
    if (!isOpen || !plantillaId || !empresaId) return
    setCargando(true)
    obtenerPlantilla(plantillaId)
      .then((p) => {
        const cliente = p.cliente
          ? { id: p.cliente.id, nombre: p.cliente.nombre }
          : null
        setClienteSeleccionado(cliente)
        const itemsForm = (p.items || []).map((it) => ({
          cantidad: Number(it.cantidad) || 1,
          descripcion: it.descripcion_libre || it.producto?.descripcion || '',
          precioUnitario: Number(it.precio_unitario) || 0,
        }))
        if (itemsForm.length === 0) itemsForm.push({ cantidad: 1, descripcion: '', precioUnitario: 0 })
        reset({
          nombrePlantilla: p.nombre || '',
          tipoDte: p.tipo_dte || '01',
          items: itemsForm,
        })
      })
      .catch((e) => {
        toast.error(e.response?.data?.detail || 'Error al cargar plantilla')
        onClose?.()
      })
      .finally(() => setCargando(false))
  }, [isOpen, plantillaId, empresaId, reset, onClose])

  const onSubmit = async (data) => {
    if (!empresaId || !plantillaId) return
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
      await actualizarPlantilla(plantillaId, payload)
      toast.success('Plantilla actualizada correctamente.')
      onGuardado?.()
    } catch (err) {
      const d = err.response?.data
      const msg =
        d?.detail || d?.error || (typeof d === 'string' ? d : null) || err.message || 'Error al actualizar.'
      toast.error(msg)
    } finally {
      setEnviando(false)
    }
  }

  if (!isOpen) return null

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-[70] flex items-center justify-center p-4 overflow-y-auto">
        <div
          className="bg-white rounded-xl shadow-xl max-w-3xl w-full my-8 max-h-[95vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-800">Editar plantilla</h2>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-lg text-gray-500 hover:bg-gray-100"
              aria-label="Cerrar"
            >
              <X size={20} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {cargando ? (
              <div className="flex justify-center py-12">
                <Loader2 size={28} className="animate-spin text-blue-600" />
              </div>
            ) : (
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nombre de la plantilla <span className="text-red-500">*</span>
                    </label>
                    <input
                      {...register('nombrePlantilla')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Ej: Alquiler Mensual"
                    />
                    {errors.nombrePlantilla && (
                      <p className="mt-1 text-sm text-red-600">{errors.nombrePlantilla.message}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Tipo de documento
                    </label>
                    <select
                      {...register('tipoDte')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="01">Factura Consumidor Final (01)</option>
                      <option value="03">Crédito Fiscal (03)</option>
                    </select>
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
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="font-medium text-gray-800">Ítems</h3>
                    <button
                      type="button"
                      onClick={() => append({ cantidad: 1, descripcion: '', precioUnitario: 0 })}
                      className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-sm"
                    >
                      + Agregar Ítem
                    </button>
                  </div>
                  <div className="overflow-x-auto -mx-1">
                    <table className="w-full text-sm min-w-[320px]">
                      <thead>
                        <tr className="bg-gray-100 text-left text-gray-600">
                          <th className="py-2 px-3 w-20">Cant.</th>
                          <th className="py-2 px-3 min-w-[140px]">Descripción</th>
                          <th className="py-2 px-3 w-24">P. Unit.</th>
                          <th className="py-2 px-3 w-28 text-right">Subtotal</th>
                          <th className="py-2 px-3 w-10"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {fields.map((field, index) => {
                          const cant = Number(items?.[index]?.cantidad) || 0
                          const precio = Number(items?.[index]?.precioUnitario) || 0
                          const subtotal = cant * precio
                          return (
                            <tr key={field.id} className="border-b border-gray-100">
                              <td className="py-2 px-3">
                                <input
                                  type="number"
                                  step="0.01"
                                  {...register(`items.${index}.cantidad`)}
                                  className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                                />
                              </td>
                              <td className="py-2 px-3 min-w-0">
                                <div className="flex items-center gap-1">
                                  <div className="flex-1 min-w-0">
                                    <ItemDescripcionCombobox
                                      value={items?.[index]?.descripcion ?? ''}
                                      onChange={(val) => setValue(`items.${index}.descripcion`, val)}
                                      onSelectItem={({ descripcion, precio_unitario }) => {
                                        setValue(`items.${index}.descripcion`, descripcion)
                                        setValue(`items.${index}.precioUnitario`, precio_unitario)
                                      }}
                                      empresaId={empresaId}
                                      placeholder="Buscar ítem..."
                                      error={errors.items?.[index]?.descripcion?.message}
                                    />
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => setCatalogRowIndex(index)}
                                    className="p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700"
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
                                  className="p-2 text-red-500 hover:bg-red-50 rounded"
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
                </div>

                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={enviando}
                    className="px-6 py-2 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 disabled:opacity-70 inline-flex items-center gap-2"
                  >
                    {enviando && <Loader2 size={18} className="animate-spin" />}
                    {enviando ? 'Guardando...' : 'Guardar cambios'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>

      <ModalBuscadorCliente
        isOpen={modalClienteAbierto}
        onClose={() => setModalClienteAbierto(false)}
        onSelect={(cliente) => {
          setClienteSeleccionado(cliente ? { id: cliente.id, nombre: cliente.nombre } : null)
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
    </>
  )
}
