import { Navigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { RUTA_INICIO_APP } from '../constants/routes'

/**
 * Solo superusuarios Django (is_superuser).
 */
export function RequireSuperuser({ children }) {
  const { user, isAuthenticated } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Evita parpadeo: esperar rehidratación de user antes de redirigir fuera del panel.
  if (!user) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  if (!user.is_superuser) {
    return <Navigate to={RUTA_INICIO_APP} replace />
  }

  return children
}
