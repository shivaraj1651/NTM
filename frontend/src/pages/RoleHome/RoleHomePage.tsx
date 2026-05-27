import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import { useRoleHome } from '@/hooks/useRoleHome'

/**
 * Smart redirect at "/".
 * Unauthenticated → /login
 * Authenticated → role-specific home (e.g. /mandates, /campaigns)
 */
export function RoleHomePage() {
  const user = useAuthStore((s) => s.user)
  const roleHome = useRoleHome()

  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={roleHome} replace />
}
