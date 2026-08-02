import { useEffect, useMemo, useState } from 'react'
import { Save, Loader2, Search, Upload, FileKey, MessageCircle, Monitor } from 'lucide-react'
import { ModalBuscadorActividad } from '../../facturacion/components/ModalBuscadorActividad'
import { UbicacionMHFields } from '../../../components/UbicacionMHFields'
import { distritoDefault } from '../../../data/distritos-cat008'

const AMBIENTES = [
  { value: '01', label: 'Pruebas (AgilDTE)' },
  { value: '00', label: 'Producción (AgilDTE)' },
]

const TIPOS_SISTEMA = [
  { value: 'AGILDTE', label: 'AgilDTE — Facturación nativa SaaS' },
  { value: 'POSAGIL', label: 'PosAgil — Punto de venta' },
  { value: 'MIXTO', label: 'Mixto — PosAgil + AgilDTE' },
]

const PDF_TEMAS = [
  { value: 'ocean', label: 'Océano', primary: '#0B3A5C', accent: '#0D9488' },
  { value: 'emerald', label: 'Esmeralda', primary: '#064E3B', accent: '#059669' },
  { value: 'amber', label: 'Ámbar', primary: '#78350F', accent: '#D97706' },
]

const EMPTY = {
  nombre: '',
  nrc: '',
  nit: '',
  direccion: '',
  departamento: '06',
  municipio: '23',
  distrito: '14',
  telefono: '',
  correo: '',
  cod_establecimiento: 'M001',
  cod_punto_venta: 'P001',
  ambiente: '01',
  cod_actividad: '',
  desc_actividad: '',
  tipo_sistema: 'AGILDTE',
  pdf_tema_color: 'ocean',
  user_api_mh: '',
  clave_api_mh: '',
  clave_certificado: '',
  whatsapp_premium_enabled: false,
  dashboard_compras_premium_enabled: false,
  whatsapp_phone_number_id: '',
  whatsapp_access_token: '',
  whatsapp_business_account_id: '',
}

function certificadoNombreDesdeUrl(url) {
  if (!url || typeof url !== 'string') return null
  try {
    const part = url.split('/').pop()
    return part ? decodeURIComponent(part.split('?')[0]) : null
  } catch {
    return null
  }
}

/**
 * Formulario completo de empresa para certificación MH y operación SaaS.
 */
export function EmpresaForm({ initial = EMPTY, onSubmit, saving = false, submitLabel = 'Guardar' }) {
  const [form, setForm] = useState({ ...EMPTY, ...initial })
  const [certificadoFile, setCertificadoFile] = useState(null)
  const [modalActividadAbierto, setModalActividadAbierto] = useState(false)

  useEffect(() => {
    const depto = initial?.departamento ?? '06'
    const muni = initial?.municipio ?? '23'
    setForm({
      ...EMPTY,
      ...initial,
      departamento: depto,
      municipio: muni,
      distrito: initial?.distrito ?? distritoDefault(depto, muni) ?? '14',
    })
    setCertificadoFile(null)
  }, [initial?.id])

  const certificadoActual = useMemo(
    () => certificadoNombreDesdeUrl(initial?.archivo_certificado),
    [initial?.archivo_certificado]
  )

  const actividadDisplay = form.cod_actividad
    ? `${form.cod_actividad}${form.desc_actividad ? ` — ${form.desc_actividad}` : ''}`
    : ''

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleCertificadoChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const nombre = (file.name || '').toLowerCase()
    if (!nombre.endsWith('.crt') && !nombre.endsWith('.pem') && !nombre.endsWith('.cer')) {
      window.alert('Seleccione un certificado digital (.crt, .cer o .pem)')
      e.target.value = ''
      return
    }
    setCertificadoFile(file)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit?.({
      ...form,
      archivo_certificado: certificadoFile || undefined,
    })
  }

  const field = (name, label, opts = {}) => (
    <div key={name}>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <input
        type={opts.type || 'text'}
        name={name}
        value={form[name] ?? ''}
        onChange={handleChange}
        required={opts.required}
        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
        placeholder={opts.placeholder}
      />
    </div>
  )

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-8">
        <section>
          <h3 className="text-sm font-semibold text-slate-800 mb-3">Datos generales</h3>
          <div className="grid sm:grid-cols-2 gap-4">
            {field('nombre', 'Nombre comercial', { required: true })}
            {field('nrc', 'NRC', { required: true })}
            {field('nit', 'NIT')}
            {field('correo', 'Correo', { type: 'email' })}
            {field('telefono', 'Teléfono')}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Ambiente AgilDTE</label>
              <select
                name="ambiente"
                value={form.ambiente}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              >
                {AMBIENTES.map((a) => (
                  <option key={a.value} value={a.value}>{a.label}</option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">
                Use <strong>Pruebas</strong> hasta completar la certificación MH; luego cambie a Producción.
              </p>
            </div>
            {field('cod_establecimiento', 'Código establecimiento')}
            {field('cod_punto_venta', 'Código punto de venta')}
          </div>
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-slate-800 mb-2">Ubicación fiscal (MH V2)</h4>
            <UbicacionMHFields
              departamento={form.departamento}
              municipio={form.municipio}
              distrito={form.distrito}
              complemento={form.direccion}
              onChange={(patch) => {
                setForm((f) => ({
                  ...f,
                  ...(patch.departamento != null ? { departamento: patch.departamento } : {}),
                  ...(patch.municipio != null ? { municipio: patch.municipio } : {}),
                  ...(patch.distrito != null ? { distrito: patch.distrito } : {}),
                  ...(patch.complemento != null ? { direccion: patch.complemento } : {}),
                }))
              }}
              required
            />
          </div>
          <div className="mt-4">
            <p className="block text-sm font-medium text-slate-700 mb-2">Color de factura PDF</p>
            <div className="flex flex-wrap gap-3">
              {PDF_TEMAS.map((tema) => {
                const selected = (form.pdf_tema_color || 'ocean') === tema.value
                return (
                  <button
                    key={tema.value}
                    type="button"
                    title={tema.label}
                    aria-pressed={selected}
                    onClick={() => setForm((f) => ({ ...f, pdf_tema_color: tema.value }))}
                    className={`flex items-center gap-2 rounded-lg px-3 py-2 border text-sm transition ${
                      selected
                        ? 'border-indigo-600 ring-2 ring-indigo-200 bg-white'
                        : 'border-slate-200 hover:border-slate-400 bg-slate-50'
                    }`}
                  >
                    <span className="w-7 h-7 rounded-md overflow-hidden flex shadow-sm" aria-hidden>
                      <span className="w-1/2 h-full" style={{ backgroundColor: tema.primary }} />
                      <span className="w-1/2 h-full" style={{ backgroundColor: tema.accent }} />
                    </span>
                    {tema.label}
                  </button>
                )
              })}
            </div>
            <p className="text-xs text-slate-500 mt-1">Aplica a la versión legible PDF de las facturas de esta empresa.</p>
          </div>
        </section>

        <section className="border-t border-slate-200 pt-6">
          <h3 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
            <Monitor className="h-4 w-4 text-indigo-600" />
            Tipo de sistema
          </h3>
          <p className="text-xs text-slate-500 mb-3">Indique qué plataforma usa esta empresa para operar.</p>
          <select
            name="tipo_sistema"
            value={form.tipo_sistema || 'AGILDTE'}
            onChange={handleChange}
            className="w-full max-w-md px-3 py-2 border border-slate-300 rounded-lg text-sm"
          >
            {TIPOS_SISTEMA.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </section>

        <section className="border-t border-slate-200 pt-6">
          <h3 className="text-sm font-semibold text-slate-800 mb-3">Actividad económica (emisor)</h3>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Descripción Act.</label>
              <input
                type="text"
                name="desc_actividad"
                value={form.desc_actividad ?? ''}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                placeholder="Descripción de la actividad económica"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Código Act. Ec.</label>
              <div className="flex items-center gap-1">
                <input
                  type="text"
                  readOnly
                  value={actividadDisplay}
                  placeholder="Seleccione una actividad desde el catálogo"
                  className="flex-1 px-3 py-2 border border-slate-300 rounded-lg bg-slate-50 text-slate-700 text-sm"
                />
                <button
                  type="button"
                  onClick={() => setModalActividadAbierto(true)}
                  className="flex-shrink-0 p-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700"
                  title="Buscar actividad económica"
                >
                  <Search className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-slate-200 pt-6">
          <h3 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <FileKey className="h-4 w-4 text-indigo-600" />
            Credenciales Ministerio de Hacienda
          </h3>
          <div className="grid sm:grid-cols-2 gap-4">
            {field('user_api_mh', 'Usuario API MH')}
            {field('clave_api_mh', 'Clave API MH', { type: 'password' })}
            {field('clave_certificado', 'Clave del certificado', { type: 'password' })}
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Certificado digital (.crt / .cer / .pem)
            </label>
            <label className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-dashed border-slate-300 bg-slate-50 hover:bg-slate-100 cursor-pointer text-sm text-slate-700">
              <Upload className="h-4 w-4" />
              {certificadoFile ? certificadoFile.name : 'Seleccionar archivo de certificado'}
              <input
                type="file"
                accept=".crt,.cer,.pem"
                className="hidden"
                onChange={handleCertificadoChange}
              />
            </label>
            {certificadoActual && !certificadoFile && (
              <p className="text-xs text-emerald-700 mt-2">
                Certificado cargado: <strong>{certificadoActual}</strong>
              </p>
            )}
            {certificadoFile && (
              <p className="text-xs text-indigo-700 mt-2">
                Nuevo certificado pendiente de guardar: <strong>{certificadoFile.name}</strong>
              </p>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Deje las claves en blanco al editar si no desea cambiarlas.
          </p>
        </section>

        <section className="border-t border-slate-200 pt-6">
          <h3 className="text-sm font-semibold text-slate-800 mb-3">Dashboard AgilDTE</h3>
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              name="dashboard_compras_premium_enabled"
              checked={Boolean(form.dashboard_compras_premium_enabled)}
              onChange={handleChange}
              className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm text-slate-700">
              Mostrar cuadro «Compras del mes» en el dashboard (premium)
            </span>
          </label>
        </section>

        <section className="border-t border-slate-200 pt-6">
          <h3 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <MessageCircle className="h-4 w-4 text-emerald-600" />
            WhatsApp (módulo premium)
          </h3>
          <label className="inline-flex items-center gap-2 mb-2 cursor-pointer">
            <input
              type="checkbox"
              name="whatsapp_premium_enabled"
              checked={Boolean(form.whatsapp_premium_enabled)}
              onChange={handleChange}
              className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
            />
            <span className="text-sm text-slate-700">Activar envío de facturas por WhatsApp</span>
          </label>
          <p className="text-xs text-slate-500">
            Los mensajes salen del número único centralizado de AgilDTE. No se requieren credenciales Meta por empresa.
          </p>
        </section>

        <div className="flex justify-end border-t border-slate-200 pt-4">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 text-white font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {saving ? 'Guardando…' : submitLabel}
          </button>
        </div>
      </form>

      <ModalBuscadorActividad
        isOpen={modalActividadAbierto}
        onClose={() => setModalActividadAbierto(false)}
        onSelect={({ codigo, descripcion }) => {
          setForm((f) => ({
            ...f,
            cod_actividad: codigo,
            desc_actividad: descripcion,
          }))
          setModalActividadAbierto(false)
        }}
      />
    </>
  )
}
