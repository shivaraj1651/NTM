import { NavLink, useNavigate } from 'react-router-dom'
import {
  Building2, Users, Shield, ClipboardList, Activity,
  BarChart2, Megaphone, FileText, LogOut, Target, Palette,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useAuthStore } from '@/store/useAuthStore'

interface NavItem {
  label: string
  to: string
  icon: React.ElementType
  allowedRoles: string[]
}

const ALL_ROLES = [
  'platform_admin', 'tenant_admin', 'brand_manager',
  'cmo', 'creative_lead', 'campaign_manager', 'viewer',
]

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Mandates',
    to: '/mandates',
    icon: FileText,
    allowedRoles: ['brand_manager', 'cmo', 'tenant_admin', 'platform_admin'],
  },
  {
    label: 'Campaigns',
    to: '/campaigns',
    icon: Megaphone,
    allowedRoles: ['campaign_manager', 'brand_manager', 'cmo', 'tenant_admin', 'platform_admin'],
  },
  {
    label: 'Creative Studio',
    to: '/creative-studio',
    icon: Palette,
    allowedRoles: ['creative_lead', 'brand_manager', 'cmo', 'tenant_admin', 'platform_admin'],
  },
  {
    label: 'Analytics',
    to: '/analytics',
    icon: BarChart2,
    allowedRoles: ALL_ROLES,
  },
  {
    label: 'KPI Dashboard',
    to: '/kpi-dashboard',
    icon: Target,
    allowedRoles: ['cmo', 'campaign_manager', 'tenant_admin', 'platform_admin'],
  },
  {
    label: 'Tenants',
    to: '/admin/tenants',
    icon: Building2,
    allowedRoles: ['platform_admin'],
  },
  {
    label: 'Users',
    to: '/admin/users',
    icon: Users,
    allowedRoles: ['platform_admin'],
  },
  {
    label: 'Roles',
    to: '/admin/roles',
    icon: Shield,
    allowedRoles: ['platform_admin'],
  },
  {
    label: 'Audit Log',
    to: '/admin/audit',
    icon: ClipboardList,
    allowedRoles: ['platform_admin'],
  },
  {
    label: 'Health',
    to: '/admin/health',
    icon: Activity,
    allowedRoles: ['platform_admin'],
  },
]

export function Sidebar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const visibleItems = NAV_ITEMS.filter(item =>
    item.allowedRoles.includes(user?.role ?? '')
  )

  return (
    <aside className="w-60 shrink-0 flex flex-col border-r bg-card">
      <div className="px-4 py-5">
        <h2 className="text-lg font-bold tracking-tight">NTM Admin</h2>
      </div>
      <Separator />
      <nav className="flex-1 px-2 py-4 space-y-1">
        {visibleItems.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <Separator />
      <div className="px-4 py-4 space-y-2">
        <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 border-blue-200 capitalize">
          {user?.role?.replace(/_/g, ' ') ?? 'Unknown'}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 text-muted-foreground"
          onClick={handleLogout}
        >
          <LogOut className="h-4 w-4" />
          Logout
        </Button>
      </div>
    </aside>
  )
}
