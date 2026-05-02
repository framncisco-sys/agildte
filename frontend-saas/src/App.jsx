import { Routes, Route, Navigate } from 'react-router-dom'
import { router } from './router'
import { PosReservedPathInfo } from './components/PosReservedPathInfo'

function App() {
  return (
    <Routes>
      {router.routes.map(({ path, element, children }) => (
        <Route key={path} path={path} element={element}>
          {children?.map((child, i) =>
            child.index ? (
              <Route key={i} index element={child.element} />
            ) : (
              <Route key={child.path} path={child.path} element={child.element} />
            )
          )}
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
