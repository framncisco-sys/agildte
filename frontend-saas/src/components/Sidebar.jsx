import { NavLink } from 'react-router-dom'
import { X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const allNavItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/clientes', label: 'Cartera de Clientes' },
  { to: '/facturacion/nueva', label: 'Facturación' },
  { to: '/facturacion/lista', label: 'Lista Facturas' },
  { to: '/contabilidad/libros-iva', label: 'Libros de IVA', roles: ['ADMIN', 'CONTADOR'] },
  { to: '/configuracion', label: 'Configuración', roles: ['ADMIN'] },
  { to: '/items', label: 'Administración de Ítems' },
]

export function Sidebar({ open = false, onClose }) {
  const { user, role } = useAuth()

  const navItems = allNavItems.filter((item) => {
    if (!item.roles) return true
    return role && item.roles.includes(role)
  })

  const navLinkClass = ({ isActive }) =>
    `block px-3 py-2 rounded-md text-sm transition-colors ${
      isActive ? 'bg-slate-700 text-white' : 'text-slate-300 hover:bg-slate-700/50'
    }`

  return (
    <>
      {/* Desktop: sidebar fijo */}
      <aside className="hidden md:flex w-64 bg-slate-800 text-white flex-col shrink-0">
        <div className="p-4 border-b border-slate-700 flex flex-col gap-2">
          <img src="/agildte-logo.png" alt="AgilDTE" className="h-8 w-auto object-contain" />
          {user?.email && (
            <p className="text-sm text-slate-400 truncate">{user.email}</p>
          )}
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, label }) => (
            <NavLink key={to} to={to} className={navLinkClass} end={to === '/dashboard'}>
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Móvil: drawer que se abre con hamburguesa */}
      <aside
        className={`md:hidden fixed top-0 left-0 z-40 h-full w-64 max-w-[85vw] bg-slate-800 text-white flex flex-col shadow-xl transition-transform duration-200 ease-out ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-hidden={!open}
      >
        <div className="p-4 border-b border-slate-700 flex items-center justify-between">
          <img src="/agildte-logo.png" alt="AgilDTE" className="h-7 w-auto object-contain" />
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:bg-slate-700 hover:text-white"
            aria-label="Cerrar menú"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        {user?.email && (
          <p className="px-4 py-2 text-sm text-slate-400 truncate border-b border-slate-700">{user.email}</p>
        )}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={navLinkClass}
              end={to === '/dashboard'}
              onClick={onClose}
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  )
}
