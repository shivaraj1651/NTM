import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'

/**
 * Guards all /admin/* routes.
 * - Not logged in → /login
 * - Any authenticated role → allowed (page-level access is handled by the sidebar)
 */
export function ProtectedRoute() {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}
