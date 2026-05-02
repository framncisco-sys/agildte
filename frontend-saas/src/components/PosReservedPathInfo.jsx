import { useEffect, useState } from 'react'
import { getPosAgilRedirectLeavingSpa } from '../utils/posAgilUrl'

/**
 * Esta SPA no es el POS. Redirige al Flask real o muestra ayuda si no hay URL posible.
 */
export function PosReservedPathInfo() {
  const [showManual, setShowManual] = useState(false)

  useEffect(() => {
    const target = getPosAgilRedirectLeavingSpa()
    if (target) {
      window.location.replace(target)
      return
    }
    setShowManual(true)
  }, [])

  if (!showManual) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-agil-bg-main px-4 text-center text-agil-text-secondary text-sm">
        <p className="mb-2">Abriendo Punto de Venta (PosAgil)…</p>
      </div>
    )
  }

  const suggested = `${window.location.protocol}//${window.location.hostname}:5001/`

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-agil-bg-main px-4 py-10 text-center">
      <p className="text-agil-text-primary font-semibold text-lg mb-2">Punto de venta (PosAgil)</p>
      <p className="text-agil-text-secondary text-sm max-w-lg mb-4">
        En producción, Nginx debe servir el POS en <code className="bg-agil-bg-white px-1 rounded">/pos/</code>{' '}
        sin pasar por esta app. Para desarrollo, define{' '}
        <code className="bg-agil-bg-white px-1 rounded">VITE_POSAGIL_PUBLIC_URL=http://localhost:5001/</code> o
        levanta el contenedor del POS en el puerto 5001.
      </p>
      <a href={suggested} className="text-agil-primary font-medium underline mb-4">
        Probar abrir {suggested}
      </a>
      <a href="/login" className="text-agil-text-secondary text-sm underline">
        Volver al inicio de sesión AgilDTE
      </a>
    </div>
  )
}
