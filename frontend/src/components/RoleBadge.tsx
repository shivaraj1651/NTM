import { cn } from '@/lib/utils'

interface Props {
  role?: string
  className?: string
}

export function RoleBadge({ className }: Props) {
  return (
    <span
      data-role="admin"
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium bg-red-100 text-red-800 border-red-200',
        className
      )}
    >
      Admin
    </span>
  )
}
