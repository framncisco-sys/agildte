import { Routes, Route, Navigate } from 'react-router-dom'
import { router } from './router'
import { PosReservedPathInfo } from './components/PosReservedPathInfo'

/** Renderiza rutas anidadas (p. ej. /superadmin/empresas). */
function renderNestedRoutes(routes) {
  if (!routes?.length) return null
  return routes.map((route, i) => {
    const key = route.path ?? (route.index ? `index-${i}` : i)
    if (route.index) {
      return <Route key={key} index element={route.element} />
    }
    return (
      <Route key={key} path={route.path} element={route.element}>
        {renderNestedRoutes(route.children)}
      </Route>
    )
  })
}

function App() {
  return (
    <Routes>
      {router.routes.map(({ path, element, children }) => (
        <Route key={path} path={path} element={element}>
          {renderNestedRoutes(children)}
        </Route>
      ))}
      {/*
        Reservado ANTES del *: si el catch-all redirige /pos a /login y LoginPage manda otra vez a /pos,
        se produce un bucle infinito. /pos/* no debe caer en Navigate → /login.
      */}
      <Route path="/pos/*" element={<PosReservedPathInfo />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App
