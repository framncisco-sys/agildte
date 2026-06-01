import { NavLink } from 'react-router-dom'
import { Building2, Users, BookOpen, Shield } from 'lucide-react'
import {
  RUTA_SUPERADMIN_EMPRESAS,
  RUTA_SUPERADMIN_CLIENTES,
  RUTA_SUPERADMIN_CATALOGOS,
} from '../../../constants/routes'

const tabs = [
  { to: RUTA_SUPERADMIN_EMPRESAS, label: 'Empresas', icon: Building2 },
  { to: RUTA_SUPERADMIN_CLIENTES, label: 'Clientes', icon: Users },
  { to: RUTA_SUPERADMIN_CATALOGOS, label: 'Catálogos MH', icon: BookOpen },
]

export function SuperAdminNav() {
  const linkClass = ({ isActive }) =>
    `inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-indigo-600 text-white shadow-sm'
        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
    }`

  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 rounded-xl bg-indigo-100">
          <Shield className="h-6 w-6 text-indigo-700" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Panel Super Usuario</h1>
          <p className="text-sm text-slate-500">Administración global del SaaS AgilDTE</p>
        </div>
      </div>
      <nav className="flex flex-wrap gap-2 p-1 bg-white rounded-xl border border-slate-200 shadow-sm">
        {tabs.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={false} className={linkClass}>
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
