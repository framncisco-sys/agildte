import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import toast from 'react-hot-toast'
import { createItem, updateItem } from '../../../api/items'

const TIPO_IMPUESTO_OPTIONS = [
  { value: '20', label: 'Gravado 13% (IVA)' },
  { value: 'exento', label: 'Exento' },
]

const TIPO_ITEM_OPTIONS = [
  { value: 1, label: 'Bien' },
  { value: 2, label: 'Servicio' },
]

export function ItemFormModal({ isOpen, onClose, onSaved, itemEdit = null, empresaId }) {
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState({})
  const [form, setForm] = useState({
    descripcion: '',
    codigo: '',
    precio_unitario: '',
    tipo_impuesto: '20',
    tipo_item: 1,
  })

  useEffect(() => {
    if (!isOpen) return
    setErrors({})
    if (itemEdit) {
      setForm({
        descripcion: itemEdit.descripcion ?? '',
        codigo: itemEdit.codigo ?? '',
        precio_unitario: itemEdit.precio_unitario != null ? String(itemEdit.precio_unitario) : '',
        tipo_impuesto: itemEdit.tipo_impuesto ?? '20',
        tipo_item: itemEdit.tipo_item ?? 1,
      })
    } else {
      setForm({
        descripcion: '',
        codigo: '',
        precio_unitario: '',
        tipo_impuesto: '20',
        tipo_item: 1,
      })
    }
  }, [isOpen, itemEdit])

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: null }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrors({})
    const desc = (form.descripcion || '').trim()
    if (!desc) {
      setErrors({ descripcion: 'La descripción es requerida' })
      return
    }
    const precio = parseFloat(form.precio_unitario)
    if (isNaN(precio) || precio < 0) {
      setErrors({ precio_unitario: 'Precio unitario debe ser un número mayor o igual a 0' })
      return
    }
    setSaving(true)
    try {
      const payload = {
        descripcion: desc,
        codigo: (form.codigo || '').trim() || undefined,
        precio_unitario: precio,
        tipo_impuesto: form.tipo_impuesto,
        tipo_item: form.tipo_item,
      }
      if (itemEdit) {
        await updateItem(itemEdit.id, payload)
        toast.success('Ítem actualizado.')
      } else {
        if (!empresaId) {
          toast.error('Seleccione una empresa.')
          setSaving(false)
          return
        }
        await createItem({ ...payload, empresa_id: empresaId })
        toast.success('Ítem creado.')
      }
      onSaved()
      onClose()
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object' && !data.detail) {
        setErrors(data)
      } else {
        toast.error(data?.detail ?? err.message ?? 'Error al guardar')
      }
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" aria-modal="true">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">
            {itemEdit ? 'Editar Ítem' : 'Nuevo Ítem'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100"
            aria-label="Cerrar"
          >
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descripción / Nombre *</label>
            <input
              type="text"
              value={form.descripcion}
              onChange={(e) => handleChange('descripcion', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Ej: Servicio de consultoría"
            />
            {errors.descripcion && (
              <p className="mt-1 text-sm text-red-600">{errors.descripcion}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Código <span className="text-gray-400">(opcional)</span></label>
            <input
              type="text"
              value={form.codigo}
              onChange={(e) => handleChange('codigo', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Ej: PROD-001"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Precio unitario *</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={form.precio_unitario}
              onChange={(e) => handleChange('precio_unitario', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="0.00"
            />
            {errors.precio_unitario && (
              <p className="mt-1 text-sm text-red-600">{errors.precio_unitario}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de impuesto</label>
            <select
              value={form.tipo_impuesto}
              onChange={(e) => handleChange('tipo_impuesto', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {TIPO_IMPUESTO_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de ítem</label>
            <select
              value={form.tipo_item}
              onChange={(e) => handleChange('tipo_item', Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {TIPO_ITEM_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60"
            >
              {saving ? 'Guardando...' : (itemEdit ? 'Actualizar' : 'Crear')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
