import { useState, useEffect } from 'react'
import { X, Pencil, Trash2, ChevronUp, ChevronDown, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useEmpresaStore } from '../../../stores/useEmpresaStore'
import {
  listarPlantillas,
  eliminarPlantilla,
  actualizarPlantillaParcial,
} from '../../../api/plantillas'
import { ModalEditarPlantilla } from './ModalEditarPlantilla'

export function ModalControlarPlantillas({ isOpen, onClose, onCambio }) {
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [plantillas, setPlantillas] = useState([])
  const [cargando, setCargando] = useState(false)
  const [editandoId, setEditandoId] = useState(null)
  const [reordenando, setReordenando] = useState(null)

  const cargar = async () => {
    if (!empresaId || !isOpen) return
    setCargando(true)
    try {
      const data = await listarPlantillas({ empresa_id: empresaId })
      setPlantillas(Array.isArray(data) ? data : [])
    } catch (e) {
      toast.error('Error al cargar plantillas')
      setPlantillas([])
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    if (isOpen) cargar()
  }, [isOpen, empresaId])

  const handleEliminar = async (p) => {
    if (!confirm(`¿Eliminar la plantilla "${p.nombre}"?`)) return
    try {
      await eliminarPlantilla(p.id)
      toast.success('Plantilla eliminada')
      await cargar()
      onCambio?.()
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Error al eliminar'
      toast.error(msg)
    }
  }

  const handleMover = async (index, direccion) => {
    if (direccion === 'up' && index <= 0) return
    if (direccion === 'down' && index >= plantillas.length - 1) return
    const otroIdx = direccion === 'up' ? index - 1 : index + 1
    const a = plantillas[index]
    const b = plantillas[otroIdx]
    setReordenando(a.id)
    try {
      await actualizarPlantillaParcial(a.id, { orden: b.orden })
      await actualizarPlantillaParcial(b.id, { orden: a.orden })
      toast.success('Orden actualizado')
      await cargar()
      onCambio?.()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al reordenar')
    } finally {
      setReordenando(null)
    }
  }

  const handleEditado = () => {
    setEditandoId(null)
    cargar()
    onCambio?.()
  }

  if (!isOpen) return null

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
        <div
          className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-800">
              Controlar plantillas rápidas
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
          <div className="flex-1 overflow-y-auto p-4">
            {cargando ? (
              <div className="flex justify-center py-12">
                <Loader2 size={28} className="animate-spin text-blue-600" />
              </div>
            ) : plantillas.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                No hay plantillas. Crea una desde el formulario de Crear Plantilla Rápida.
              </p>
            ) : (
              <ul className="space-y-2">
                {plantillas.map((p, idx) => (
                  <li
                    key={p.id}
                    className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 bg-gray-50/50 hover:bg-gray-50"
                  >
                    <div className="flex flex-col gap-0.5">
                      <button
                        type="button"
                        onClick={() => handleMover(idx, 'up')}
                        disabled={idx === 0 || reordenando === p.id}
                        className="p-1 rounded text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
                        title="Subir"
                      >
                        <ChevronUp size={18} />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleMover(idx, 'down')}
                        disabled={idx === plantillas.length - 1 || reordenando === p.id}
                        className="p-1 rounded text-gray-600 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
                        title="Bajar"
                      >
                        <ChevronDown size={18} />
                      </button>
                    </div>
                    <span className="text-sm font-medium text-gray-500 w-6">
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 truncate">{p.nombre}</p>
                      {p.cliente && (
                        <p className="text-xs text-gray-500 truncate">
                          Cliente: {p.cliente.nombre}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setEditandoId(p.id)}
                        className="p-2 rounded-lg text-blue-600 hover:bg-blue-50"
                        title="Editar"
                      >
                        <Pencil size={18} />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleEliminar(p)}
                        className="p-2 rounded-lg text-red-500 hover:bg-red-50"
                        title="Eliminar"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="p-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="w-full px-4 py-2 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>

      {editandoId && (
        <ModalEditarPlantilla
          plantillaId={editandoId}
          isOpen={!!editandoId}
          onClose={() => setEditandoId(null)}
          onGuardado={handleEditado}
        />
      )}
    </>
  )
}
