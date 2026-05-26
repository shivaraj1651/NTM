import { cn } from '@/lib/utils'

const ROLE_STYLES: Record<string, string> = {
  platform_admin:   'bg-red-100 text-red-800 border-red-200',
  tenant_admin:     'bg-blue-100 text-blue-800 border-blue-200',
  brand_manager:    'bg-purple-100 text-purple-800 border-purple-200',
  cmo:              'bg-amber-100 text-amber-800 border-amber-200',
  creative_lead:    'bg-green-100 text-green-800 border-green-200',
  campaign_manager: 'bg-cyan-100 text-cyan-800 border-cyan-200',
  viewer:           'bg-gray-100 text-gray-600 border-gray-200',
}

const DEFAULT_STYLE = 'bg-gray-100 text-gray-600 border-gray-200'

interface Props {
  role: string
  className?: string
}

export function RoleBadge({ role, className }: Props) {
  const style = ROLE_STYLES[role] ?? DEFAULT_STYLE
  return (
    <span
      data-role={role}
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        style,
        className
      )}
    >
      {role}
    </span>
  )
}
