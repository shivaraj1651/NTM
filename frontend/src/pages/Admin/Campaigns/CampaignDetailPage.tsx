import { useEffect } from 'react'
import { useParams, useNavigate, useLocation, Outlet, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useCampaign } from '@/hooks/useCampaigns'
import type { CampaignStatus } from '@/types/admin'
import { cn } from '@/lib/utils'

const STEPS = ['Create', 'Concepts', 'Confirmed', 'Plan', 'Budget', 'Approved']

const STATUS_TO_STEP: Record<CampaignStatus, number> = {
  pending: 0,
  concepts_ready: 1,
  confirmed: 2,
  planned: 3,
  budget_proposed: 4,
  approved: 5,
}

const STEP_PATHS = [null, 'concepts', 'plan', 'plan', 'budget', 'budget']

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { data: campaign, isLoading } = useCampaign(id!)

  useEffect(() => {
    if (!campaign) return
    const base = `/admin/campaigns/${id}`
    if (location.pathname !== base && location.pathname !== `${base}/`) return
    const { status } = campaign
    if (status === 'concepts_ready') navigate(`${base}/concepts`, { replace: true })
    else if (status === 'confirmed' || status === 'planned') navigate(`${base}/plan`, { replace: true })
    else if (status === 'budget_proposed' || status === 'approved') navigate(`${base}/budget`, { replace: true })
  }, [campaign, id, navigate, location.pathname])

  if (isLoading) return <p className="text-muted-foreground text-sm">Loading…</p>
  if (!campaign) return null

  const currentStep = STATUS_TO_STEP[campaign.status]
  const base = `/admin/campaigns/${id}`

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <Button variant="outline" size="sm" onClick={() => navigate('/admin/campaigns')}>
          ← Back
        </Button>
        <h1 className="text-xl font-semibold">Campaign {id}</h1>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-0 mb-8 overflow-x-auto">
        {STEPS.map((label, i) => {
          const isCompleted = i < currentStep
          const isCurrent = i === currentStep
          const path = STEP_PATHS[i]
          const to = path ? `${base}/${path}` : null

          const circle = (
            <div
              className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium shrink-0',
                isCompleted && 'bg-primary text-primary-foreground',
                isCurrent && 'border-2 border-primary text-primary',
                !isCompleted && !isCurrent && 'border-2 border-muted text-muted-foreground'
              )}
            >
              {isCompleted ? '✓' : i + 1}
            </div>
          )

          return (
            <div key={label} className="flex items-center">
              <div className="flex flex-col items-center gap-1">
                {isCompleted && to ? (
                  <Link to={to}>{circle}</Link>
                ) : (
                  circle
                )}
                <span
                  className={cn(
                    'text-xs whitespace-nowrap',
                    isCurrent && 'text-primary font-medium',
                    !isCompleted && !isCurrent && 'text-muted-foreground'
                  )}
                >
                  {label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    'h-0.5 w-12 mx-1 mb-4',
                    i < currentStep ? 'bg-primary' : 'bg-muted'
                  )}
                />
              )}
            </div>
          )
        })}
      </div>

      {campaign.status === 'pending' ? (
        <p className="text-muted-foreground text-sm">Generating concepts…</p>
      ) : (
        <Outlet />
      )}
    </div>
  )
}
