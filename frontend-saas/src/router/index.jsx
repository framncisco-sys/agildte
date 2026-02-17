import { Outlet, Navigate } from 'react-router-dom'
import { RequireAuth } from './RequireAuth'
import { MainLayout } from '../layouts/MainLayout'
import { AuthLayout } from '../layouts/AuthLayout'
import { LoginPage } from '../features/auth/LoginPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { PlaceholderPage } from '../components/PlaceholderPage'
import { NuevaFactura } from '../features/facturacion/pages/NuevaFactura'
import { ListaFacturas } from '../features/facturacion/pages/ListaFacturas'
import Clientes from '../features/clientes/pages/Clientes'
import LibrosIva from '../features/contabilidad/pages/LibrosIva'
import ConfiguracionPage from '../features/configuracion/pages/ConfiguracionPage'

export const router = {
  routes: [
    {
      path: '/',
      element: (
        <RequireAuth>
          <MainLayout />
        </RequireAuth>
      ),
      children: [
        { index: true, element: <Navigate to="/dashboard" replace /> },
        { path: 'dashboard', element: <DashboardPage /> },
        { path: 'facturacion', element: <Navigate to="/facturacion/nueva" replace /> },
        { path: 'facturacion/nueva', element: <NuevaFactura /> },
        { path: 'facturacion/lista', element: <ListaFacturas /> },
        { path: 'clientes', element: <Clientes /> },
        { path: 'contabilidad', element: <PlaceholderPage title="Contabilidad" /> },
        {
          path: 'configuracion',
          element: (
            <RequireAuth allowedRoles={['ADMIN']}>
              <ConfiguracionPage />
            </RequireAuth>
          ),
        },
        {
          path: 'contabilidad/libros-iva',
          element: (
            <RequireAuth allowedRoles={['ADMIN', 'CONTADOR']}>
              <LibrosIva />
            </RequireAuth>
          ),
        },
      ],
    },
    {
      path: '/login',
      element: (
        <AuthLayout>
          <LoginPage />
        </AuthLayout>
      ),
      children: [],
    },
    {
      path: '/unauthorized',
      element: (
        <div className="min-h-screen flex items-center justify-center bg-slate-100">
          <div className="text-center p-8 bg-white rounded-xl shadow-lg max-w-md">
            <h1 className="text-xl font-semibold text-slate-800 mb-2">Sin permiso</h1>
            <p className="text-slate-600 mb-4">No tiene permisos para acceder a esta sección.</p>
            <a href="/dashboard" className="text-slate-800 underline font-medium">Volver al inicio</a>
          </div>
        </div>
      ),
      children: [],
    },
  ],
}

export { RequireAuth }
