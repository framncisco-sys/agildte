import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { RUTA_INICIO_SOLO_POS } from '../constants/routes'

/**
 * Oculta rutas de facturación nativa cuando el perfil indica facturación solo vía PosAgil.
 */
export function RequireFacturacionNativa({ children }) {
  const { user } = useAuth()
  if (user?.facturacion_solo_pos) {
    return <Navigate to={RUTA_INICIO_SOLO_POS} replace />
  }
  return children
}
