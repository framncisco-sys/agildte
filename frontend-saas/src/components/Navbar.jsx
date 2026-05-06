import { useNavigate } from 'react-router-dom'
import { Menu } from 'lucide-react'
import { useAuthStore } from '../stores/useAuthStore'
import { useEmpresaStore } from '../stores/useEmpresaStore'
import { useAuth } from '../context/AuthContext'
import { ROLE_AGILDTE_ADMIN, ROLE_POSAGIL_ADMIN } from '../constants/roles'
import { getPosAgilSsoUrl } from '../utils/posAgilUrl'

export function Navbar({ onMenuClick }) {
  const navigate = useNavigate()
  const { user, role } = useAuth()
  const logout = useAuthStore((s) => s.logout)
  const isSuperuser = useAuthStore((s) => s.user?.is_superuser) ?? false
  // Superusuario Django: siempre puede abrir PosAgil por SSO (sin depender del flag en PerfilUsuario).
  const mostrarAbrirPos =
    Boolean(user?.is_superuser) ||
    (user?.acceso_posagil === true &&
      (role === ROLE_AGILDTE_ADMIN || role === ROLE_POSAGIL_ADMIN))
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
      <div className="flex items-center gap-3 shrink-0">
        {mostrarAbrirPos && (
          <button
            type="button"
            onClick={() => {
              const t = useAuthStore.getState().token
              window.location.href = getPosAgilSsoUrl(t)
            }}
            className="text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 px-3 py-1.5 rounded-lg transition-colors"
          >
            Abrir Pos Agil
          </button>
        )}
        <button
          onClick={handleLogout}
          className="text-sm text-agil-text-secondary hover:text-red-600 transition-colors"
        >
          Cerrar sesión
        </button>
      </div>
    </header>
  )
}
