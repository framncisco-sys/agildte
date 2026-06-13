import { ShoppingBag, ExternalLink } from 'lucide-react'
import { useAuthStore } from '../stores/useAuthStore'
import { openPosAgilSso } from '../utils/posAgilUrl'

/** Botón portal AgilDTE → PosAgil (SSO). Estilos en index.css (.btn-abrir-pos-agil). */
export function PosAgilOpenButton() {
  return (
    <button
      type="button"
      className="btn-abrir-pos-agil"
      onClick={() => openPosAgilSso(useAuthStore.getState().token)}
      title="Abrir punto de venta PosAgil"
      aria-label="Abrir PosAgil"
    >
      <span className="btn-abrir-pos-agil__icon" aria-hidden>
        <ShoppingBag size={15} strokeWidth={2.25} />
      </span>
      <span className="btn-abrir-pos-agil__text">Abrir PosAgil</span>
      <ExternalLink className="btn-abrir-pos-agil__arrow" size={14} strokeWidth={2.25} aria-hidden />
    </button>
  )
}
