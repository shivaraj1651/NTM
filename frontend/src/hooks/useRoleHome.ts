import { useAuthStore } from '@/store/useAuthStore'

/** Maps each role to its home route after login. */
export const ROLE_HOME: Record<string, string> = {
  platform_admin: '/admin/tenants',
  tenant_admin: '/mandates',
  brand_manager: '/mandates',
  cmo: '/mandates',
  creative_lead: '/creative-studio',
  campaign_manager: '/campaigns',
  viewer: '/analytics',
}

/**
 * Returns the home route for the currently authenticated user's role.
 * Falls back to '/mandates' for unknown roles.
 * Returns '/login' when not authenticated.
 */
export function useRoleHome(): string {
  const user = useAuthStore((s) => s.user)
  if (!user) return '/login'
  return ROLE_HOME[user.role] ?? '/mandates'
}
