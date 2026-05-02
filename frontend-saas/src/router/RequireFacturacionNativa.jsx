import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Oculta rutas de facturación nativa cuando el perfil indica facturación solo vía PosAgil.
 */
export function RequireFacturacionNativa({ children }) {
  const { user } = useAuth()
  if (user?.facturacion_solo_pos) {
    return <Navigate to="/dashboard" replace />
  }
  return children
}
