import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const allNavItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/clientes', label: 'Cartera de Clientes' },
  { to: '/facturacion/nueva', label: 'Facturación' },
  { to: '/facturacion/lista', label: 'Lista Facturas' },
  { to: '/contabilidad/libros-iva', label: 'Libros de IVA', roles: ['ADMIN', 'CONTADOR'] },
  { to: '/configuracion', label: 'Configuración', roles: ['ADMIN'] },
]

export function Sidebar() {
  const { user, role } = useAuth()

  const navItems = allNavItems.filter((item) => {
    if (!item.roles) return true
    return role && item.roles.includes(role)
  })

  return (
    <aside className="w-64 bg-slate-800 text-white flex flex-col shrink-0">
      <div className="p-4 border-b border-slate-700">
        <h1 className="font-semibold text-lg">Facturación SaaS</h1>
        {user?.email && (
          <p className="text-sm text-slate-400 truncate">{user.email}</p>
        )}
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `block px-3 py-2 rounded-md text-sm transition-colors ${
                isActive ? 'bg-slate-700 text-white' : 'text-slate-300 hover:bg-slate-700/50'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
