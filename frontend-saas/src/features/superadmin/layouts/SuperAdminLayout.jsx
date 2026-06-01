import { Outlet } from 'react-router-dom'
import { SuperAdminNav } from '../components/SuperAdminNav'

export function SuperAdminLayout() {
  return (
    <div className="max-w-6xl mx-auto">
      <SuperAdminNav />
      <Outlet />
    </div>
  )
}
