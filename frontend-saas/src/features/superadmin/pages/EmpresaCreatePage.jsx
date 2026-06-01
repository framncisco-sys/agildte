import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import toast from 'react-hot-toast'
import { createEmpresa } from '../../../api/empresas'
import { buildEmpresaPayload } from '../../../api/empresaPayload'
import { EmpresaForm } from '../components/EmpresaForm'

export default function EmpresaCreatePage() {
  const navigate = useNavigate()
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (form) => {
    setSaving(true)
    try {
      const data = await createEmpresa(buildEmpresaPayload(form))
      toast.success('Empresa creada correctamente')
      navigate(`/superadmin/empresas/${data.id}`, { replace: true })
    } catch (err) {
      const d = err.response?.data
      const msg = d?.detail || d?.nombre?.[0] || d?.nrc?.[0] || 'Error al crear empresa'
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <Link
        to="/superadmin/empresas"
        className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline mb-4"
      >
        <ArrowLeft className="h-4 w-4" />
        Volver al listado
      </Link>
      <h2 className="text-lg font-semibold text-slate-800 mb-4">Nueva empresa</h2>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <EmpresaForm onSubmit={handleSubmit} saving={saving} submitLabel="Crear empresa" />
      </div>
    </div>
  )
}
