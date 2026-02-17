import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

/**
 * Página de login: logo, card con inputs Usuario y Contraseña (iconos),
 * botón Ingresar, mensaje de error en rojo.
 * Usa login() que llama a /api/token/ y luego /api/auth/me/.
 */
export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, isAuthenticated } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const from = location.state?.from?.pathname || '/dashboard'

  useEffect(() => {
    if (isAuthenticated) navigate(from, { replace: true })
  }, [isAuthenticated, navigate, from])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!username.trim() || !password) {
      setError('Usuario y contraseña son requeridos')
      return
    }
    setLoading(true)
    try {
      await login({
        username: username.trim(),
        password,
      })
      navigate(from, { replace: true })
    } catch (err) {
      const msg =
        err.response?.data?.detail ??
        err.response?.data?.mensaje ??
        (typeof err.response?.data === 'object' && err.response?.data !== null
          ? JSON.stringify(err.response.data)
          : null) ??
        err.message ??
        'Credenciales incorrectas'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 px-4">
      <div className="w-full max-w-md">
        {/* Logo oficial AgilDTE */}
        <div className="flex justify-center mb-6">
          <img src="/agildte-logo.png" alt="AgilDTE" className="h-14 w-auto object-contain drop-shadow-sm" />
        </div>

        {/* Card blanca con shadow-lg */}
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden">
          <div className="px-8 py-6 border-b border-slate-100">
            <h1 className="text-xl font-bold text-slate-800 text-center">AgilDTE</h1>
            <p className="text-slate-500 text-sm text-center mt-1">Inicie sesión en su cuenta</p>
          </div>
          <form onSubmit={handleSubmit} className="p-8 space-y-5">
            <div>
              <label htmlFor="login-username" className="block text-sm font-medium text-slate-700 mb-1.5">
                Usuario
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </span>
                <input
                  id="login-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg pl-10 pr-4 py-2.5 text-slate-800 placeholder-slate-400 focus:ring-2 focus:ring-slate-600 focus:border-slate-500 transition-colors"
                  placeholder="Usuario"
                  autoComplete="username"
                />
              </div>
            </div>
            <div>
              <label htmlFor="login-password" className="block text-sm font-medium text-slate-700 mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </span>
                <input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg pl-10 pr-4 py-2.5 text-slate-800 placeholder-slate-400 focus:ring-2 focus:ring-slate-600 focus:border-slate-500 transition-colors"
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
              </div>
            </div>
            {error && (
              <p className="text-red-600 text-sm" role="alert">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-slate-800 text-white py-3 rounded-lg font-medium hover:bg-slate-700 focus:ring-2 focus:ring-offset-2 focus:ring-slate-600 disabled:opacity-60 transition-colors"
            >
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </form>
        </div>
        <p className="text-center text-slate-500 text-sm mt-6">
          Solo usuarios autorizados
        </p>
      </div>
    </div>
  )
}
