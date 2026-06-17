import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { RoleGuard } from '@/components/RoleGuard'
import { AdminLayout } from '@/components/AdminLayout'
import { RoleHomePage } from '@/pages/RoleHome/RoleHomePage'

// Auth
import { LoginPage } from '@/pages/Login/LoginPage'

// Onboarding
import { OnboardingPage } from '@/pages/Onboarding/OnboardingPage'

// Mandate
import { MandatesPage } from '@/pages/Mandate/MandatesPage'
import { MandateFormPage } from '@/pages/Mandate/MandateFormPage'
import { MandateSummaryPage } from '@/pages/Mandate/MandateSummaryPage'

// Campaign
import { CampaignsPage } from '@/pages/Admin/Campaigns/CampaignsPage'
import { CampaignDetailPage } from '@/pages/Admin/Campaigns/CampaignDetailPage'
import { ConceptsPage } from '@/pages/Admin/Campaigns/ConceptsPage'
import { PlanPage } from '@/pages/Admin/Campaigns/PlanPage'
import { BudgetPage } from '@/pages/Admin/Campaigns/BudgetPage'
import { CreativesPage } from '@/pages/Admin/Campaigns/CreativesPage'
import { GoLivePage } from '@/pages/Admin/Campaigns/GoLivePage'
import { KpisPage } from '@/pages/Admin/Campaigns/KpisPage'
import { PhysicalLogPage } from '@/pages/Admin/Campaigns/PhysicalLogPage'
import { CIReportPage } from '@/pages/Admin/Campaigns/CIReportPage'

// Creative Studio
import { CreativeStudioPage } from '@/pages/CreativeStudio/CreativeStudioPage'
import { AssetDetailPage } from '@/pages/CreativeStudio/AssetDetailPage'

// Analytics
import { AnalyticsPage } from '@/pages/Admin/Analytics/AnalyticsPage'

// KPI Dashboard
import { KPIDashboardPage } from '@/pages/KPIDashboard/KPIDashboardPage'

// Reports
import { ReportsPage } from '@/pages/Reports/ReportsPage'

// Settings
import { SettingsPage } from '@/pages/Settings/SettingsPage'

// Admin
import { TenantsPage } from '@/pages/Admin/Tenants/TenantsPage'
import { UsersPage } from '@/pages/Admin/Users/UsersPage'
import { RolesPage } from '@/pages/Admin/Roles/RolesPage'
import { AuditLogPage } from '@/pages/Admin/AuditLog/AuditLogPage'
import { HealthPage } from '@/pages/Admin/Health/HealthPage'

const REPORT_ROLES = ['cmo', 'tenant_admin', 'platform_admin']
const MANDATE_ROLES = ['brand_manager', 'cmo', 'tenant_admin', 'platform_admin']
const CAMPAIGN_ROLES = ['campaign_manager', 'brand_manager', 'cmo', 'tenant_admin', 'platform_admin']
const CREATIVE_ROLES = ['creative_lead', 'brand_manager', 'cmo', 'tenant_admin', 'platform_admin']
const KPI_ROLES = ['cmo', 'campaign_manager', 'tenant_admin', 'platform_admin']
const ADMIN_ROLES = ['platform_admin']
const ALL_ROLES = [
  'platform_admin', 'tenant_admin', 'brand_manager',
  'cmo', 'creative_lead', 'campaign_manager', 'viewer',
]

export const router = createBrowserRouter([
  // Smart home redirect
  { path: '/', element: <RoleHomePage /> },

  // Public
  { path: '/login', element: <LoginPage /> },

  // Onboarding — any authenticated user
  {
    element: <ProtectedRoute />,
    children: [
      { path: '/onboarding', element: <OnboardingPage /> },
    ],
  },

  // Mandates
  {
    path: '/mandates',
    element: <RoleGuard allowedRoles={MANDATE_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <MandatesPage /> },
          { path: 'new', element: <MandateFormPage /> },
          { path: ':id/summary', element: <MandateSummaryPage /> },
        ],
      },
    ],
  },

  // Campaigns
  {
    path: '/campaigns',
    element: <RoleGuard allowedRoles={CAMPAIGN_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <CampaignsPage /> },
          {
            path: ':id',
            element: <CampaignDetailPage />,
            children: [
              { path: 'concepts', element: <ConceptsPage /> },
              { path: 'plan', element: <PlanPage /> },
              { path: 'budget', element: <BudgetPage /> },
              { path: 'creatives', element: <CreativesPage /> },
              { path: 'go-live', element: <GoLivePage /> },
              { path: 'kpis', element: <KpisPage /> },
              { path: 'physical-log', element: <PhysicalLogPage /> },
              { path: 'ci-report', element: <CIReportPage /> },
            ],
          },
        ],
      },
    ],
  },

  // Creative Studio
  {
    path: '/creative-studio',
    element: <RoleGuard allowedRoles={CREATIVE_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <CreativeStudioPage /> },
          { path: ':assetId', element: <AssetDetailPage /> },
        ],
      },
    ],
  },

  // Analytics — all authenticated roles
  {
    path: '/analytics',
    element: <RoleGuard allowedRoles={ALL_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <AnalyticsPage /> },
          { path: ':mandateId', element: <AnalyticsPage /> },
        ],
      },
    ],
  },

  // KPI Dashboard
  {
    path: '/kpi-dashboard',
    element: <RoleGuard allowedRoles={KPI_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <KPIDashboardPage /> },
        ],
      },
    ],
  },

  // Reports
  {
    path: '/reports',
    element: <RoleGuard allowedRoles={REPORT_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <ReportsPage /> },
        ],
      },
    ],
  },

  // Settings — all authenticated users
  {
    path: '/settings',
    element: <RoleGuard allowedRoles={ALL_ROLES} />,
    children: [
      {
        element: <AdminLayout />,
        children: [
          { index: true, element: <SettingsPage /> },
        ],
      },
    ],
  },

  // Admin — platform_admin ONLY
  {
    path: '/admin',
    element: <RoleGuard allowedRoles={ADMIN_ROLES} />,
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
        ],
      },
    ],
  },

  // Catch-all
  { path: '*', element: <RoleHomePage /> },
])
