import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'

export function ProtectedRoute() {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'platform_admin') return <Navigate to="/403" replace />
  return <Outlet />
}
