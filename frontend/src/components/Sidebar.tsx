import { NavLink, useNavigate } from 'react-router-dom'
import { Building2, Users, Shield, ClipboardList, Activity, LogOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { useAuthStore } from '@/store/useAuthStore'

const navItems = [
  { label: 'Tenants',   to: '/admin/tenants', icon: Building2 },
  { label: 'Users',     to: '/admin/users',   icon: Users },
  { label: 'Roles',     to: '/admin/roles',   icon: Shield },
  { label: 'Audit Log', to: '/admin/audit',   icon: ClipboardList },
  { label: 'Health',    to: '/admin/health',  icon: Activity },
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
        {navItems.map(({ label, to, icon: Icon }) => (
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
        <Badge variant="secondary" className="text-xs">{user?.role}</Badge>
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
