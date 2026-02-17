import { Routes, Route, Navigate } from 'react-router-dom'
import { router } from './router'

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
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App
