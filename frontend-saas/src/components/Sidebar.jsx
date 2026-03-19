import { useEffect, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { ChevronDown, ChevronRight, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useEmpresaStore } from '../stores/useEmpresaStore'
import { listarPlantillas } from '../api/plantillas'
import { ModalControlarPlantillas } from '../features/facturacion/components/ModalControlarPlantillas'

const allNavItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/clientes', label: 'Cartera de Clientes' },
  { to: '/facturacion/nueva', label: 'Facturación' },
  { to: '/facturacion/lista', label: 'Lista Facturas' },
  { to: '/facturacion/carga-masiva', label: 'Carga Masiva' },
  { to: '/contabilidad/libros-iva', label: 'Libros de IVA', roles: ['ADMIN', 'CONTADOR'] },
  { to: '/configuracion', label: 'Configuración', roles: ['ADMIN'] },
  { to: '/items', label: 'Administración de ítems' },
]

export function Sidebar({ open = false, onClose }) {
  const { user, role } = useAuth()
  const navigate = useNavigate()
  const empresaId = useEmpresaStore((s) => s.empresaId)
  const [plantillas, setPlantillas] = useState([])
  const [loadingPlantillas, setLoadingPlantillas] = useState(false)
  const [showFacturacionRapida, setShowFacturacionRapida] = useState(true)
  const [modalControlarAbierto, setModalControlarAbierto] = useState(false)

  const navItems = allNavItems.filter((item) => {
    if (!item.roles) return true
    return role && item.roles.includes(role)
  })

  const cargarPlantillas = () => {
    if (!empresaId) {
      setPlantillas([])
      return
    }
    setLoadingPlantillas(true)
    listarPlantillas({ empresa_id: empresaId })
      .then((data) => setPlantillas(Array.isArray(data) ? data : []))
      .catch(() => setPlantillas([]))
      .finally(() => setLoadingPlantillas(false))
  }

  useEffect(() => {
    cargarPlantillas()
  }, [empresaId])

  useEffect(() => {
    const handler = () => cargarPlantillas()
    window.addEventListener('plantillas-actualizadas', handler)
    return () => window.removeEventListener('plantillas-actualizadas', handler)
  }, [empresaId])

  const navLinkClass = ({ isActive }) =>
    `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive ? 'bg-white/20 text-white' : 'text-white/80 hover:bg-white/10 hover:text-white'
    }`

  const sidebarBase = 'bg-agil-primary text-white flex-col shrink-0'
  const sidebarBorder = 'border-white/20'

  return (
    <>
      {/* Desktop: sidebar con primary-blue corporativo */}
      <aside className={`hidden md:flex w-64 ${sidebarBase}`}>
        <div className={`p-4 border-b ${sidebarBorder} flex flex-col gap-2`}>
          <img src="/agildte-logo.png" alt="AgilDTE" className="h-16 w-auto object-contain drop-shadow-sm" />
          {user?.email && (
            <p className="text-sm text-white/70 truncate">{user.email}</p>
          )}
        </div>
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map(({ to, label }) => (
            <NavLink key={to} to={to} className={navLinkClass} end={to === '/dashboard'}>
              {label}
            </NavLink>
          ))}

          {/* Sección Facturación Rápida (desktop) */}
          <div className="mt-4 pt-3 border-t border-white/15">
            <button
              type="button"
              onClick={() => setShowFacturacionRapida((v) => !v)}
              className="w-full flex items-center justify-between px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-white/80 hover:text-white"
            >
              <span>Facturación Rápida</span>
              {showFacturacionRapida ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
            {showFacturacionRapida && (
              <div className="mt-1 space-y-1">
                {loadingPlantillas && (
                  <p className="text-[11px] text-white/60 px-2">Cargando plantillas...</p>
                )}
                {!loadingPlantillas && plantillas.length === 0 && (
                  <p className="text-[11px] text-white/60 px-2">
                    Sin plantillas. Crea tu primera.
                  </p>
                )}
                {plantillas.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => navigate(`/facturacion/nueva?plantillaId=${p.id}`)}
                    className="w-full text-left px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/15 text-xs text-white/90 truncate"
                    title={p.nombre}
                  >
                    {p.nombre}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setModalControlarAbierto(true)}
                  className="w-full mt-1 text-left px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-medium text-white/90 border border-white/20"
                >
                  Controlar plantillas rápidas
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/facturacion/plantillas/nueva')}
                  className="w-full mt-1 text-left px-3 py-1.5 rounded-lg bg-emerald-500/90 hover:bg-emerald-400 text-xs font-semibold text-white"
                >
                  + Crear Plantilla Rápida
                </button>
              </div>
            )}
          </div>
        </nav>
      </aside>

      {/* Móvil: drawer */}
      <aside
        className={`md:hidden fixed top-0 left-0 z-40 h-full w-64 max-w-[85vw] ${sidebarBase} shadow-xl transition-transform duration-200 ease-out ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-hidden={!open}
      >
        <div className={`p-4 border-b ${sidebarBorder} flex items-center justify-between`}>
          <img src="/agildte-logo.png" alt="AgilDTE" className="h-14 w-auto object-contain drop-shadow-sm" />
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-white/80 hover:bg-white/10 hover:text-white transition-colors"
            aria-label="Cerrar menú"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        {user?.email && (
          <p className={`px-4 py-2 text-sm text-white/70 truncate border-b ${sidebarBorder}`}>{user.email}</p>
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

          {/* Sección Facturación Rápida (móvil) */}
          <div className="mt-4 pt-3 border-t border-white/15">
            <button
              type="button"
              onClick={() => setShowFacturacionRapida((v) => !v)}
              className="w-full flex items-center justify-between px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-white/80 hover:text-white"
            >
              <span>Facturación Rápida</span>
              {showFacturacionRapida ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
            {showFacturacionRapida && (
              <div className="mt-1 space-y-1">
                {loadingPlantillas && (
                  <p className="text-[11px] text-white/60 px-2">Cargando plantillas...</p>
                )}
                {!loadingPlantillas && plantillas.length === 0 && (
                  <p className="text-[11px] text-white/60 px-2">
                    Sin plantillas. Crea tu primera.
                  </p>
                )}
                {plantillas.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => {
                      navigate(`/facturacion/nueva?plantillaId=${p.id}`)
                      onClose?.()
                    }}
                    className="w-full text-left px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/15 text-xs text-white/90 truncate"
                    title={p.nombre}
                  >
                    {p.nombre}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => {
                    setModalControlarAbierto(true)
                    onClose?.()
                  }}
                  className="w-full mt-1 text-left px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-medium text-white/90 border border-white/20"
                >
                  Controlar plantillas rápidas
                </button>
                <button
                  type="button"
                  onClick={() => {
                    navigate('/facturacion/plantillas/nueva')
                    onClose?.()
                  }}
                  className="w-full mt-1 text-left px-3 py-1.5 rounded-lg bg-emerald-500/90 hover:bg-emerald-400 text-xs font-semibold text-white"
                >
                  + Crear Plantilla Rápida
                </button>
              </div>
            )}
          </div>
        </nav>
      </aside>

      <ModalControlarPlantillas
        isOpen={modalControlarAbierto}
        onClose={() => setModalControlarAbierto(false)}
        onCambio={cargarPlantillas}
      />
    </>
  )
}
