import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import toast from 'react-hot-toast'
import { createCliente, updateCliente } from '../../../api/clientes'
import { DEPARTAMENTOS, MUNICIPIOS_POR_DEPARTAMENTO } from '../../../data/departamentos-municipios'
import { BuscadorActividad } from '../../../components/BuscadorActividad'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'

const TIPO_DOCUMENTO_OPTIONS = [
  { value: 'NIT', label: 'NIT' },
  { value: 'DUI', label: 'DUI' },
  { value: 'Pasaporte', label: 'Pasaporte' },
]

const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/

export function ClienteFormModal({ isOpen, onClose, onSaved, clienteEdit = null }) {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState({})
  const [form, setForm] = useState({
    nombre: '',
    tipo_documento: 'NIT',
    documento_identidad: '',
    nrc: '',
    actividad_economica: '',
    actividad_economica_display: '',
    correo: '',
    telefono: '',
    direccion_departamento: '06',
    direccion_municipio: '14',
    direccion_complemento: '',
  })

  const municipiosOpciones = form.direccion_departamento
    ? (MUNICIPIOS_POR_DEPARTAMENTO[form.direccion_departamento] || [])
    : []

  useEffect(() => {
    if (!isOpen) return
    setErrors({})
    if (clienteEdit) {
      const codAct = clienteEdit.actividad_economica ?? clienteEdit.cod_actividad ?? ''
      const descAct = clienteEdit.desc_actividad ?? ''
      const displayAct = codAct && descAct ? `${codAct} - ${descAct}` : codAct
      setForm({
        nombre: clienteEdit.nombre ?? '',
        tipo_documento: clienteEdit.tipo_documento ?? 'NIT',
        documento_identidad: clienteEdit.documento_identidad ?? clienteEdit.nit ?? clienteEdit.dui ?? '',
        nrc: clienteEdit.nrc ?? '',
        actividad_economica: codAct,
        actividad_economica_display: displayAct,
        correo: clienteEdit.correo ?? clienteEdit.email_contacto ?? '',
        telefono: clienteEdit.telefono ?? '',
        direccion_departamento: clienteEdit.direccion_departamento ?? clienteEdit.departamento ?? '06',
        direccion_municipio: clienteEdit.direccion_municipio ?? clienteEdit.municipio ?? '14',
        direccion_complemento: clienteEdit.direccion_complemento ?? clienteEdit.direccion ?? '',
      })
    } else {
      setForm({
        nombre: '',
        tipo_documento: 'NIT',
        documento_identidad: '',
        nrc: '',
        actividad_economica: '',
        actividad_economica_display: '',
        correo: '',
        telefono: '',
        direccion_departamento: '06',
        direccion_municipio: '14',
        direccion_complemento: '',
      })
    }
  }, [isOpen, clienteEdit])

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: null }))
    if (field === 'direccion_departamento') {
      const munis = MUNICIPIOS_POR_DEPARTAMENTO[value] || []
      const firstCod = munis.length ? munis[0].codigo : ''
      setForm((prev) => ({
        ...prev,
        direccion_departamento: value,
        direccion_municipio: firstCod,
      }))
    }
  }

  const validate = () => {
    const next = {}
    if (!form.nombre?.trim()) next.nombre = 'El nombre es obligatorio.'
    if (form.correo && !EMAIL_REGEX.test(form.correo)) {
      next.correo = 'El correo no tiene un formato válido.'
    }
    if (form.nrc?.trim() && !form.actividad_economica?.trim()) {
      next.actividad_economica = 'Si ingresa NRC, el campo Actividad Económica es obligatorio (requisito para DTE-03).'
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const buildPayload = () => ({
    nombre: form.nombre.trim(),
    tipo_documento: form.tipo_documento,
    documento_identidad: form.documento_identidad?.trim() || null,
    nrc: form.nrc?.trim() || null,
    actividad_economica: form.actividad_economica?.trim() || null,
    correo: form.correo?.trim() || null,
    telefono: form.telefono?.trim() || null,
    direccion_departamento: form.direccion_departamento || '06',
    direccion_municipio: form.direccion_municipio || '14',
    direccion_complemento: form.direccion_complemento?.trim() || null,
    empresa_id: empresaId,
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return
    if (!empresaId) {
      toast.error('Selecciona una empresa antes de crear un cliente.')
      return
    }
    setSaving(true)
    setErrors({})
    try {
      const payload = buildPayload()
      if (clienteEdit?.id) {
        await updateCliente(clienteEdit.id, payload)
        toast.success('Cliente actualizado correctamente.')
      } else {
        await createCliente(payload)
        toast.success('Cliente creado correctamente.')
      }
      onSaved?.()
      onClose()
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object' && !data.detail && !data.error) {
        // Normalizar: cada valor puede ser string o array
        const normalized = {}
        let firstMsg = ''
        for (const [key, val] of Object.entries(data)) {
          const msg = Array.isArray(val) ? val[0] : String(val)
          normalized[key] = msg
          if (!firstMsg) firstMsg = msg
        }
        setErrors(normalized)
        toast.error(firstMsg || 'Revisa los campos marcados.')
      } else {
        const msg = data?.detail ?? data?.error ?? data?.documento_identidad?.[0] ?? data?.nrc?.[0] ?? err.message ?? 'Error al guardar.'
        toast.error(msg)
      }
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-cliente-title"
    >
      <div
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white">
          <h2 id="modal-cliente-title" className="text-lg font-semibold text-gray-800">
            {clienteEdit ? 'Editar Cliente' : 'Nuevo Cliente'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
            aria-label="Cerrar"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nombre (Razón Social o Nombre Completo) *</label>
            <input
              type="text"
              value={form.nombre}
              onChange={(e) => handleChange('nombre', e.target.value)}
              placeholder="Nombre o razón social"
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${errors.nombre ? 'border-red-500' : 'border-gray-300'}`}
            />
            {errors.nombre && <p className="mt-1 text-sm text-red-600">{errors.nombre}</p>}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de documento</label>
              <select
                value={form.tipo_documento}
                onChange={(e) => handleChange('tipo_documento', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {TIPO_DOCUMENTO_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Documento (NIT / DUI / Pasaporte)</label>
              <input
                type="text"
                value={form.documento_identidad}
                onChange={(e) => handleChange('documento_identidad', e.target.value)}
                placeholder="NIT, DUI o Pasaporte"
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${errors.documento_identidad ? 'border-red-500' : 'border-gray-300'}`}
              />
              {errors.documento_identidad && <p className="mt-1 text-sm text-red-600">{errors.documento_identidad}</p>}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">NRC (opcional, solo para CCF)</label>
              <input
                type="text"
                value={form.nrc}
                onChange={(e) => handleChange('nrc', e.target.value)}
                placeholder="Número de Registro de Contribuyente"
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${errors.nrc ? 'border-red-500' : 'border-gray-300'}`}
              />
              {errors.nrc && <p className="mt-1 text-sm text-red-600">{Array.isArray(errors.nrc) ? errors.nrc[0] : errors.nrc}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Actividad económica (obligatorio si tiene NRC)</label>
              <BuscadorActividad
                value={form.actividad_economica}
                displayValue={form.actividad_economica_display}
                onChange={(codigo) => handleChange('actividad_economica', codigo)}
                onDisplayChange={(display) => setForm((prev) => ({ ...prev, actividad_economica_display: display }))}
                placeholder="Buscar por código o descripción (mín. 2 caracteres)"
                error={!!errors.actividad_economica}
              />
              {errors.actividad_economica && <p className="mt-1 text-sm text-red-600">{Array.isArray(errors.actividad_economica) ? errors.actividad_economica[0] : errors.actividad_economica}</p>}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Correo * (para enviar DTE)</label>
              <input
                type="email"
                value={form.correo}
                onChange={(e) => handleChange('correo', e.target.value)}
                placeholder="correo@ejemplo.com"
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${errors.correo ? 'border-red-500' : 'border-gray-300'}`}
              />
              {errors.correo && <p className="mt-1 text-sm text-red-600">{Array.isArray(errors.correo) ? errors.correo[0] : errors.correo}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono (opcional)</label>
              <input
                type="text"
                value={form.telefono}
                onChange={(e) => handleChange('telefono', e.target.value)}
                placeholder="Teléfono"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Departamento (código MH)</label>
              <select
                value={form.direccion_departamento}
                onChange={(e) => handleChange('direccion_departamento', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {DEPARTAMENTOS.map((d) => (
                  <option key={d.codigo} value={d.codigo}>{d.nombre}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Municipio (código MH)</label>
              <select
                value={form.direccion_municipio}
                onChange={(e) => handleChange('direccion_municipio', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {municipiosOpciones.map((m) => (
                  <option key={m.codigo} value={m.codigo}>{m.nombre}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Dirección (complemento)</label>
            <input
              type="text"
              value={form.direccion_complemento}
              onChange={(e) => handleChange('direccion_complemento', e.target.value)}
              placeholder="Dirección exacta"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? 'Guardando...' : (clienteEdit ? 'Actualizar' : 'Crear')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
