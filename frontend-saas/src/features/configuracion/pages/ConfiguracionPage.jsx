import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'
import { getEmpresa, updateEmpresa } from '../../../api/empresa'
import { changePassword } from '../../../api/auth'
import { ImagePlus, Save, Building2, Lock } from 'lucide-react'

const AMBIENTES = [
  { value: '01', label: 'Pruebas (MH)' },
  { value: '00', label: 'Producción (MH)' },
]

export default function ConfiguracionPage() {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const empresas = useEmpresaStore((s) => s.empresas)

  const [empresa, setEmpresa] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    nombre: '',
    nrc: '',
    nit: '',
    direccion: '',
    telefono: '',
    correo: '',
    cod_establecimiento: '',
    cod_punto_venta: '',
    ambiente: '01',
    desc_actividad: '',
  })
  const [logoFile, setLogoFile] = useState(null)
  const [logoPreview, setLogoPreview] = useState(null)
  const [passwordOld, setPasswordOld] = useState('')
  const [passwordNew, setPasswordNew] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [savingPassword, setSavingPassword] = useState(false)

  useEffect(() => {
    if (!empresaId) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    getEmpresa(empresaId)
      .then((data) => {
        if (!cancelled) {
          setEmpresa(data)
          setForm({
            nombre: data.nombre ?? '',
            nrc: data.nrc ?? '',
            nit: data.nit ?? '',
            direccion: data.direccion ?? '',
            telefono: data.telefono ?? '',
            correo: data.correo ?? '',
            cod_establecimiento: data.cod_establecimiento ?? 'M001',
            cod_punto_venta: data.cod_punto_venta ?? 'P001',
            ambiente: data.ambiente ?? '01',
            desc_actividad: data.desc_actividad ?? '',
          })
          setLogoPreview(data.logo_url ?? null)
        }
      })
      .catch((err) => {
        if (!cancelled) toast.error(err.response?.data?.detail ?? 'Error al cargar la empresa')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [empresaId])

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    if (!passwordOld || !passwordNew || !passwordConfirm) {
      toast.error('Complete los tres campos de contraseña')
      return
    }
    if (passwordNew !== passwordConfirm) {
      toast.error('La nueva contraseña y la confirmación no coinciden')
      return
    }
    if (passwordNew.length < 8) {
      toast.error('La nueva contraseña debe tener al menos 8 caracteres')
      return
    }
    setSavingPassword(true)
    try {
      await changePassword({ old_password: passwordOld, new_password: passwordNew })
      setPasswordOld('')
      setPasswordNew('')
      setPasswordConfirm('')
      toast.success('Contraseña actualizada. Use la nueva contraseña en el próximo inicio de sesión.')
    } catch (err) {
      toast.error(err.response?.data?.detail ?? 'Error al cambiar la contraseña')
    } finally {
      setSavingPassword(false)
    }
  }

  const handleLogoChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      toast.error('Seleccione una imagen (PNG, JPG, etc.)')
      return
    }
    setLogoFile(file)
    const url = URL.createObjectURL(file)
    setLogoPreview(url)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!empresaId) {
      toast.error('Seleccione una empresa')
      return
    }
    if (!form.nombre?.trim()) {
      toast.error('El nombre de la empresa es obligatorio')
      return
    }
    if (!form.nrc?.trim()) {
      toast.error('El NRC es obligatorio')
      return
    }
    setSaving(true)
    try {
      const payload = { ...form }
      if (logoFile) payload.logo = logoFile
      const updated = await updateEmpresa(empresaId, payload)
      setEmpresa(updated)
      if (updated.logo_url) setLogoPreview(updated.logo_url)
      setLogoFile(null)
      useEmpresaStore.getState().setEmpresa({ id: updated.id, nombre: updated.nombre })
      toast.success('Datos guardados correctamente')
    } catch (err) {
      const msg =
        err.response?.data?.nombre?.[0] ??
        err.response?.data?.nrc?.[0] ??
        err.response?.data?.detail ??
        'Error al guardar'
      toast.error(typeof msg === 'string' ? msg : 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-2 border-slate-600 border-t-transparent" />
      </div>
    )
  }

  if (!empresaId) {
    return (
      <div className="p-6 max-w-2xl">
        <h1 className="text-2xl font-bold text-slate-800 mb-4">Configuración</h1>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-amber-800">
          <p className="font-medium">Seleccione una empresa</p>
          <p className="text-sm mt-1">Use el selector del encabezado para elegir la empresa a configurar.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-slate-100">
          <Building2 className="h-6 w-6 text-slate-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Configuración de la empresa</h1>
          <p className="text-sm text-slate-500">Corrija nombres, datos fiscales y logo</p>
        </div>
      </div>

      {empresas.length > 1 && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-1">Empresa a configurar</label>
          <select
            value={empresaId ?? ''}
            onChange={(e) => useEmpresaStore.getState().selectEmpresa(e.target.value || null)}
            className="w-full max-w-xs border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
          >
            {empresas.map((e) => (
              <option key={e.id} value={e.id}>{e.nombre}</option>
            ))}
          </select>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-200 bg-slate-50">
            <h2 className="font-semibold text-slate-800">Datos generales</h2>
          </div>
          <div className="p-5 space-y-4">
            <div className="flex flex-wrap gap-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-28 h-28 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 flex items-center justify-center overflow-hidden">
                    {logoPreview ? (
                      <img src={logoPreview} alt="Logo" className="w-full h-full object-contain" />
                    ) : (
                      <ImagePlus className="h-10 w-10 text-slate-400" />
                    )}
                  </div>
                  <label className="text-xs font-medium text-slate-600 cursor-pointer hover:text-slate-800">
                    Cambiar logo
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleLogoChange}
                    />
                  </label>
                </div>
                <div className="flex-1 min-w-0 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Nombre de la empresa *</label>
                    <input
                      type="text"
                      name="nombre"
                      value={form.nombre}
                      onChange={handleChange}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                      placeholder="Razón social"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">NRC *</label>
                      <input
                        type="text"
                        name="nrc"
                        value={form.nrc}
                        onChange={handleChange}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                        placeholder="Ej: 123456-7"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">NIT</label>
                      <input
                        type="text"
                        name="nit"
                        value={form.nit}
                        onChange={handleChange}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                        placeholder="Opcional"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Dirección</label>
                    <textarea
                      name="direccion"
                      value={form.direccion}
                      onChange={handleChange}
                      rows={2}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                      placeholder="Dirección fiscal"
                    />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Teléfono</label>
                      <input
                        type="text"
                        name="telefono"
                        value={form.telefono}
                        onChange={handleChange}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                        placeholder="Opcional"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Correo de contacto</label>
                      <input
                        type="email"
                        name="correo"
                        value={form.correo}
                        onChange={handleChange}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                        placeholder="contacto@empresa.com"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-200 bg-slate-50">
            <h2 className="font-semibold text-slate-800">Facturación electrónica (MH)</h2>
          </div>
          <div className="p-5 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Ambiente</label>
                <select
                  name="ambiente"
                  value={form.ambiente}
                  onChange={handleChange}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                >
                  {AMBIENTES.map((a) => (
                    <option key={a.value} value={a.value}>{a.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Actividad económica (descripción)</label>
                <input
                  type="text"
                  name="desc_actividad"
                  value={form.desc_actividad}
                  onChange={handleChange}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                  placeholder="Ej: Venta al por menor"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Código establecimiento</label>
                <input
                  type="text"
                  name="cod_establecimiento"
                  value={form.cod_establecimiento}
                  onChange={handleChange}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                  placeholder="M001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Código punto de venta</label>
                <input
                  type="text"
                  name="cod_punto_venta"
                  value={form.cod_punto_venta}
                  onChange={handleChange}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                  placeholder="P001"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center gap-2">
            <Lock className="h-5 w-5 text-slate-600" />
            <h2 className="font-semibold text-slate-800">Cambiar contraseña</h2>
          </div>
          <form onSubmit={handleChangePassword} className="p-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Contraseña actual</label>
              <input
                type="password"
                value={passwordOld}
                onChange={(e) => setPasswordOld(e.target.value)}
                className="w-full max-w-xs border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nueva contraseña</label>
              <input
                type="password"
                value={passwordNew}
                onChange={(e) => setPasswordNew(e.target.value)}
                className="w-full max-w-xs border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                placeholder="Mínimo 8 caracteres"
                autoComplete="new-password"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Confirmar nueva contraseña</label>
              <input
                type="password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                className="w-full max-w-xs border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
                placeholder="Repita la nueva contraseña"
                autoComplete="new-password"
              />
            </div>
            <button
              type="submit"
              disabled={savingPassword}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600 disabled:opacity-60"
            >
              {savingPassword ? 'Guardando...' : 'Cambiar contraseña'}
            </button>
          </form>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Guardando...' : 'Guardar cambios'}
          </button>
        </div>
      </form>
    </div>
  )
}
