import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './context/AuthContext'
import { applyPortalLogoutFromUrl } from './utils/portalLogout'
import './index.css'
import App from './App.jsx'

// PosAgil → https://agildte.com/login?logout=1 (misma pestaña): limpiar JWT antes del router.
applyPortalLogoutFromUrl()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
        <Toaster position="top-center" />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
