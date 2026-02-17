import { useNavigate } from 'react-router-dom'
import { Menu } from 'lucide-react'
import { useAuthStore } from '../stores/useAuthStore'
import { useEmpresaStore } from '../stores/useEmpresaStore'

export function Navbar({ onMenuClick }) {
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)
  const isSuperuser = useAuthStore((s) => s.user?.is_superuser) ?? false
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const empresaNombre = useEmpresaStore((s) => s.empresaNombre)
  const empresas = useEmpresaStore((s) => s.empresas)
  const selectEmpresa = useEmpresaStore((s) => s.selectEmpresa)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onMenuClick}
          className="md:hidden p-2 -ml-2 rounded-lg text-gray-600 hover:bg-gray-100"
          aria-label="Abrir menú"
        >
          <Menu className="w-6 h-6" />
        </button>
        <div className="flex items-center gap-4 min-w-0">
        {isSuperuser && empresas.length > 0 ? (
          <select
            value={empresaId ?? ''}
            onChange={(e) => selectEmpresa(e.target.value || null)}
            className="text-sm border border-gray-300 rounded-md px-3 py-1.5"
          >
            <option value="">Seleccionar empresa</option>
            {empresas.map((e) => (
              <option key={e.id} value={e.id}>
                {e.nombre || e.name || e.id}
              </option>
            ))}
          </select>
        ) : empresaNombre ? (
          <span className="text-sm text-gray-700 font-medium truncate hidden sm:inline">
            Empresa: {empresaNombre}
          </span>
        ) : null}
        </div>
      </div>
      <button
        onClick={handleLogout}
        className="text-sm text-red-600 hover:text-red-700"
      >
        Cerrar sesión
      </button>
    </header>
  )
}
