import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Protege rutas que requieren autenticación.
 * Si no hay token, redirige a /login.
 * Si se pasa allowedRoles y el usuario no tiene uno de esos roles, redirige a /unauthorized o Dashboard.
 * El PosAgil no se abre solo al cargar el portal: usar «Abrir Pos Agil» en la barra superior (SSO con JWT).
 */
export function RequireAuth({ children, allowedRoles }) {
  const { isAuthenticated, role } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Si se especifican roles permitidos, verificar que el usuario tenga uno válido.
  // role=null también se considera no autorizado cuando hay restricción de roles.
  if (allowedRoles?.length) {
    if (!role || !allowedRoles.includes(role)) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  return children
}
