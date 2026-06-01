import { Outlet, Navigate } from 'react-router-dom'
import { RequireAuth } from './RequireAuth'
import { RequireSuperuser } from './RequireSuperuser'
import { RequireFacturacionNativa } from './RequireFacturacionNativa'
import { ROLES_CONFIG_ADMIN, ROLES_LIBROS_IVA } from '../constants/roles'
import { RUTA_INICIO_APP } from '../constants/routes'
import { MainLayout } from '../layouts/MainLayout'
import { AuthLayout } from '../layouts/AuthLayout'
import { LoginPage } from '../features/auth/LoginPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { PlaceholderPage } from '../components/PlaceholderPage'
import { NuevaFactura } from '../features/facturacion/pages/NuevaFactura'
import { ListaFacturas } from '../features/facturacion/pages/ListaFacturas'
import { PlantillasRapidasPage } from '../features/facturacion/pages/PlantillasRapidas'
import { CargaMasiva } from '../features/facturacion/pages/CargaMasiva'
import Clientes from '../features/clientes/pages/Clientes'
import LibrosIva from '../features/contabilidad/pages/LibrosIva'
import ConfiguracionPage from '../features/configuracion/pages/ConfiguracionPage'
import ActividadesCatalogoPage from '../features/configuracion/pages/ActividadesCatalogoPage'
import ItemsPage from '../features/items/pages/ItemsPage'
import { SuperAdminLayout } from '../features/superadmin/layouts/SuperAdminLayout'
import EmpresasListPage from '../features/superadmin/pages/EmpresasListPage'
import EmpresaCreatePage from '../features/superadmin/pages/EmpresaCreatePage'
import EmpresaDetailPage from '../features/superadmin/pages/EmpresaDetailPage'
import ClientesGlobalPage from '../features/superadmin/pages/ClientesGlobalPage'
import CatalogosMHPage from '../features/superadmin/pages/CatalogosMHPage'

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
        { index: true, element: <Navigate to={RUTA_INICIO_APP} replace /> },
        { path: 'dashboard', element: <DashboardPage /> },
        { path: 'facturacion', element: <Navigate to="/facturacion/nueva" replace /> },
        {
          path: 'facturacion/nueva',
          element: (
            <RequireFacturacionNativa>
              <NuevaFactura />
            </RequireFacturacionNativa>
          ),
        },
        {
          path: 'facturacion/lista',
          element: (
            <RequireFacturacionNativa>
              <ListaFacturas />
            </RequireFacturacionNativa>
          ),
        },
        {
          path: 'facturacion/plantillas/nueva',
          element: (
            <RequireFacturacionNativa>
              <PlantillasRapidasPage />
            </RequireFacturacionNativa>
          ),
        },
        {
          path: 'facturacion/carga-masiva',
          element: (
            <RequireFacturacionNativa>
              <CargaMasiva />
            </RequireFacturacionNativa>
          ),
        },
        { path: 'clientes', element: <Clientes /> },
        { path: 'contabilidad', element: <PlaceholderPage title="Contabilidad" /> },
        {
          path: 'configuracion',
          element: (
            <RequireAuth allowedRoles={ROLES_CONFIG_ADMIN}>
              <ConfiguracionPage />
            </RequireAuth>
          ),
        },
        {
          path: 'configuracion/catalogo-actividades',
          element: (
            <RequireAuth allowedRoles={ROLES_CONFIG_ADMIN}>
              <ActividadesCatalogoPage />
            </RequireAuth>
          ),
        },
        { path: 'items', element: <ItemsPage /> },
        {
          path: 'contabilidad/libros-iva',
          element: (
            <RequireAuth allowedRoles={ROLES_LIBROS_IVA}>
              <LibrosIva />
            </RequireAuth>
          ),
        },
        {
          path: 'superadmin',
          element: (
            <RequireSuperuser>
              <SuperAdminLayout />
            </RequireSuperuser>
          ),
          children: [
            { index: true, element: <Navigate to="empresas" replace /> },
            { path: 'empresas', element: <EmpresasListPage /> },
            { path: 'empresas/nueva', element: <EmpresaCreatePage /> },
            { path: 'empresas/:id', element: <EmpresaDetailPage /> },
            { path: 'clientes', element: <ClientesGlobalPage /> },
            { path: 'catalogos', element: <CatalogosMHPage /> },
          ],
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
        <div className="min-h-screen flex items-center justify-center bg-agil-bg-main">
          <div className="text-center p-8 bg-white rounded-xl shadow-lg max-w-md">
            <h1 className="text-xl font-semibold text-slate-800 mb-2">Sin permiso</h1>
            <p className="text-slate-600 mb-4">No tiene permisos para acceder a esta sección.</p>
            <a href={RUTA_INICIO_APP} className="text-slate-800 underline font-medium">Volver al inicio</a>
          </div>
        </div>
      ),
      children: [],
    },
  ],
}

export { RequireAuth }
