/**
 * Roles devueltos por el backend (JWT /auth/login, /auth/me).
 * Deben coincidir con ROLE_* en backend/api/permissions.py
 */
export const ROLE_AGILDTE_ADMIN = 'AGILDTE_ADMIN'
export const ROLE_AGILDTE_CONTADOR = 'AGILDTE_CONTADOR'
export const ROLE_AGILDTE_VENDEDOR = 'AGILDTE_VENDEDOR'
export const ROLE_POSAGIL_ADMIN = 'POSAGIL_ADMIN'
export const ROLE_POSAGIL_VENDEDOR = 'POSAGIL_VENDEDOR'

/** Rutas que exigen administración (configuración). */
export const ROLES_CONFIG_ADMIN = [ROLE_AGILDTE_ADMIN, ROLE_POSAGIL_ADMIN]

/** Libros de IVA y similares. */
export const ROLES_LIBROS_IVA = [ROLE_AGILDTE_ADMIN, ROLE_POSAGIL_ADMIN, ROLE_AGILDTE_CONTADOR]

/**
 * Vendedor solo PosAgil (redirigir a /pos/).
 * Incluye el nombre antiguo POS_VENDEDOR por si el backend o localStorage aún no migraron.
 */
export function isPosagilVendedorRole(role) {
  if (!role || typeof role !== 'string') return false
  return role === ROLE_POSAGIL_VENDEDOR || role === 'POS_VENDEDOR'
}

/**
 * Solo personal de caja PosAgil con permiso explícito en PerfilUsuario (acceso_posagil).
 * Evita redirigir al POS por grupo mal asignado o rol por defecto.
 */
export function shouldRedirectFromAgildteToPos(user) {
  if (!user || !isPosagilVendedorRole(user.role)) return false
  return user.acceso_posagil === true
}
