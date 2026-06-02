import { cn } from '@/lib/utils'

interface Props {
  role?: string
  className?: string
}

const ROLE_STYLES: Record<string, string> = {
  platform_admin:  'bg-red-100 text-red-800 border-red-200',
  tenant_admin:    'bg-orange-100 text-orange-800 border-orange-200',
  campaign_manager:'bg-blue-100 text-blue-800 border-blue-200',
  brand_manager:   'bg-purple-100 text-purple-800 border-purple-200',
  cmo:             'bg-indigo-100 text-indigo-800 border-indigo-200',
  creative_lead:   'bg-pink-100 text-pink-800 border-pink-200',
  viewer:          'bg-gray-100 text-gray-800 border-gray-200',
}

export function RoleBadge({ role = 'viewer', className }: Props) {
  const styles = ROLE_STYLES[role] ?? 'bg-gray-100 text-gray-800 border-gray-200'
  return (
    <span
      data-role={role}
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        styles,
        className
      )}
    >
      {role}
    </span>
  )
}
