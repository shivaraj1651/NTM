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
import { CampaignsPage } from '@/pages/Admin/Campaigns/CampaignsPage'
import { CampaignDetailPage } from '@/pages/Admin/Campaigns/CampaignDetailPage'
import { ConceptsPage } from '@/pages/Admin/Campaigns/ConceptsPage'
import { PlanPage } from '@/pages/Admin/Campaigns/PlanPage'
import { BudgetPage } from '@/pages/Admin/Campaigns/BudgetPage'
import { CreativesPage } from '@/pages/Admin/Campaigns/CreativesPage'
import { GoLivePage } from '@/pages/Admin/Campaigns/GoLivePage'
import { KpisPage } from '@/pages/Admin/Campaigns/KpisPage'
import { OnboardingPage } from '@/pages/Onboarding/OnboardingPage'
import { MandatesPage } from '@/pages/Mandate/MandatesPage'
import { MandateFormPage } from '@/pages/Mandate/MandateFormPage'
import { MandateSummaryPage } from '@/pages/Mandate/MandateSummaryPage'

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/admin/tenants" replace /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/onboarding', element: <OnboardingPage /> },
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
          { path: 'mandates', element: <MandatesPage /> },
          { path: 'mandates/new', element: <MandateFormPage /> },
          { path: 'mandates/:id/edit', element: <MandateFormPage /> },
          { path: 'mandates/:id/summary', element: <MandateSummaryPage /> },
          { path: 'campaigns', element: <CampaignsPage /> },
          {
            path: 'campaigns/:id',
            element: <CampaignDetailPage />,
            children: [
              { path: 'concepts', element: <ConceptsPage /> },
              { path: 'plan', element: <PlanPage /> },
              { path: 'budget', element: <BudgetPage /> },
              { path: 'creatives', element: <CreativesPage /> },
              { path: 'golive', element: <GoLivePage /> },
              { path: 'kpis', element: <KpisPage /> },
            ],
          },
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
