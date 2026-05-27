import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import { useRoleHome } from '@/hooks/useRoleHome'

interface RoleGuardProps {
  /** Role names allowed to access the wrapped routes. */
  allowedRoles: string[]
}

/**
 * Wraps a route group with role-based access control.
 *
 * - Not authenticated → redirect to /login
 * - Authenticated but wrong role → redirect to user's role home
 * - Correct role → render Outlet (children)
 */
export function RoleGuard({ allowedRoles }: RoleGuardProps) {
  const user = useAuthStore((s) => s.user)
  const roleHome = useRoleHome()

  if (!user) return <Navigate to="/login" replace />
  if (!allowedRoles.includes(user.role)) return <Navigate to={roleHome} replace />
  return <Outlet />
}
