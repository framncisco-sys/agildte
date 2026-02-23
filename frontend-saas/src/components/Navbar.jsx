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
    <header className="h-14 bg-agil-bg-white border-b border-agil-border-subtle flex items-center justify-between px-4 shrink-0 shadow-sm">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onMenuClick}
          className="md:hidden p-2 -ml-2 rounded-lg text-agil-text-secondary hover:bg-agil-bg-main transition-colors"
          aria-label="Abrir menú"
        >
          <Menu className="w-6 h-6" />
        </button>
        <div className="flex items-center gap-4 min-w-0">
        {isSuperuser && empresas.length > 0 ? (
          <select
            value={empresaId ?? ''}
            onChange={(e) => selectEmpresa(e.target.value || null)}
            className="text-sm border border-agil-border-subtle rounded-lg px-3 py-2 text-agil-text-primary bg-agil-bg-white focus:ring-2 focus:ring-agil-primary focus:border-agil-primary transition-colors"
          >
            <option value="">Seleccionar empresa</option>
            {empresas.map((e) => (
              <option key={e.id} value={e.id}>
                {e.nombre || e.name || e.id}
              </option>
            ))}
          </select>
        ) : empresaNombre ? (
          <span className="text-sm text-agil-text-primary font-medium truncate hidden sm:inline">
            Empresa: {empresaNombre}
          </span>
        ) : null}
        </div>
      </div>
      <button
        onClick={handleLogout}
        className="text-sm text-agil-text-secondary hover:text-red-600 transition-colors"
      >
        Cerrar sesión
      </button>
    </header>
  )
}
