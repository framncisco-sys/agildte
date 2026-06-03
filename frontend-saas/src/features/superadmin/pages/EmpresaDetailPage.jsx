import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, Building2, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { getEmpresa, updateEmpresa } from '../../../api/empresa'
import { deleteEmpresa } from '../../../api/empresas'
import { buildEmpresaPayload } from '../../../api/empresaPayload'
import { EmpresaForm } from '../components/EmpresaForm'
import { MHCertificacionPanel } from '../components/MHCertificacionPanel'
import { ModoOperacionPanel } from '../components/ModoOperacionPanel'
import { StressTestPanel } from '../components/StressTestPanel'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'

export default function EmpresaDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const selectEmpresa = useEmpresaStore((s) => s.selectEmpresa)
  const [empresa, setEmpresa] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!id) return
    selectEmpresa(Number(id))
    let cancelled = false
    setLoading(true)
    getEmpresa(id)
      .then((data) => {
        if (!cancelled) setEmpresa(data)
      })
      .catch((err) => {
        if (!cancelled) toast.error(err.response?.data?.detail ?? 'Error al cargar empresa')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [id, selectEmpresa])

  const handleDelete = async () => {
    if (!empresa) return
    if (!window.confirm(`¿Eliminar la empresa «${empresa.nombre}»? Esta acción no se puede deshacer.`)) return
    setDeleting(true)
    try {
      await deleteEmpresa(empresa.id)
      toast.success('Empresa eliminada')
      navigate('/superadmin/empresas')
    } catch (err) {
      toast.error(err.response?.data?.detail ?? 'No se pudo eliminar la empresa')
    } finally {
      setDeleting(false)
    }
  }

  const handleSubmit = async (form) => {
    setSaving(true)
    try {
      const data = await updateEmpresa(id, buildEmpresaPayload(form))
      setEmpresa(data)
      toast.success('Empresa actualizada')
    } catch (err) {
      const d = err.response?.data
      const msg = d?.detail || d?.nombre?.[0] || d?.nrc?.[0] || 'Error al guardar'
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  if (!empresa) {
    return (
      <div className="text-center py-16 text-slate-500">
        Empresa no encontrada.{' '}
        <Link to="/superadmin/empresas" className="text-indigo-600 underline">Volver</Link>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <Link
          to="/superadmin/empresas"
          className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver al listado
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-100">
              <Building2 className="h-5 w-5 text-indigo-700" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800">{empresa.nombre}</h2>
              <p className="text-sm text-slate-500 font-mono">NRC {empresa.nrc} · ID {empresa.id}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-200 text-red-700 hover:bg-red-50 text-sm font-medium disabled:opacity-50"
          >
            {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            Eliminar empresa
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="font-semibold text-slate-800 mb-4">Datos de la empresa</h3>
        <EmpresaForm
          initial={empresa}
          onSubmit={handleSubmit}
          saving={saving}
          submitLabel="Guardar cambios"
        />
      </div>

      <ModoOperacionPanel
        empresaId={Number(id)}
        empresa={empresa}
        onUpdated={(data) => setEmpresa(data)}
      />

      <MHCertificacionPanel empresa={empresa} />

      <StressTestPanel empresaId={Number(id)} empresa={empresa} />
    </div>
  )
}
