import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Protege rutas que requieren autenticación.
 * Si no hay token, redirige a /login.
 * Si se pasa allowedRoles (ej. ['ADMIN', 'CONTADOR']) y el usuario no tiene uno de esos roles, redirige a /unauthorized o Dashboard.
 */
export function RequireAuth({ children, allowedRoles }) {
  const { isAuthenticated, role } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles?.length && role && !allowedRoles.includes(role)) {
    return <Navigate to="/unauthorized" replace />
  }

  return children
}
