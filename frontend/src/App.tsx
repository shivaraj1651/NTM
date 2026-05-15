import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AdminLayout } from '@/components/AdminLayout'
import { LoginPage } from '@/pages/Login/LoginPage'
import { TenantsPage } from '@/pages/Admin/Tenants/TenantsPage'
import { UsersPage } from '@/pages/Admin/Users/UsersPage'
import { RolesPage } from '@/pages/Admin/Roles/RolesPage'
import { AuditLogPage } from '@/pages/Admin/AuditLog/AuditLogPage'
import { HealthPage } from '@/pages/Admin/Health/HealthPage'
import { AnalyticsPage } from '@/pages/Admin/Analytics/AnalyticsPage'

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/admin/tenants" replace /> },
  { path: '/login', element: <LoginPage /> },
  {
    path: '/admin',
    element: <ProtectedRoute />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <Navigate to="/admin/tenants" replace /> },
          { path: 'tenants', element: <TenantsPage /> },
          { path: 'users', element: <UsersPage /> },
          { path: 'roles', element: <RolesPage /> },
          { path: 'audit', element: <AuditLogPage /> },
          { path: 'health', element: <HealthPage /> },
          { path: 'analytics', element: <AnalyticsPage /> },
        ],
      },
    ],
  },
  {
    path: '/403',
    element: (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold">Access Denied</h1>
          <p className="text-muted-foreground mt-2">
            You don't have permission to view this page.
          </p>
        </div>
      </div>
    ),
  },
])
