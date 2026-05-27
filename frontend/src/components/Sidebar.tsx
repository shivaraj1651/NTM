import { NavLink, useNavigate } from 'react-router-dom'
import {
  Building2, Users, Shield, ClipboardList, Activity,
  BarChart2, Megaphone, FileText, LogOut, Target,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useAuthStore } from '@/store/useAuthStore'

const NAV_ITEMS = [
  { label: 'Tenants',       to: '/admin/tenants',      icon: Building2  },
  { label: 'Users',         to: '/admin/users',         icon: Users      },
  { label: 'Roles',         to: '/admin/roles',         icon: Shield     },
  { label: 'Audit Log',     to: '/admin/audit',         icon: ClipboardList },
  { label: 'Health',        to: '/admin/health',        icon: Activity   },
  { label: 'Analytics',     to: '/admin/analytics',     icon: BarChart2  },
  { label: 'Mandates',      to: '/admin/mandates',      icon: FileText   },
  { label: 'Campaigns',     to: '/admin/campaigns',     icon: Megaphone  },
  { label: 'KPI Dashboard', to: '/admin/kpi-dashboard', icon: Target     },
]

export function Sidebar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-60 shrink-0 flex flex-col border-r bg-card">
      <div className="px-4 py-5">
        <h2 className="text-lg font-bold tracking-tight">NTM Admin</h2>
      </div>
      <Separator />
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
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
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium bg-red-100 text-red-800 border-red-200">
          Admin
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
