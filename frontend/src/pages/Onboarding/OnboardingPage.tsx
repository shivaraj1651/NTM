import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OrgInfoStep, type OrgInfoValues } from './OrgInfoStep'
import { useCreateClient } from '@/hooks/useMandates'

const STEP_LABELS = ['Organisation', 'Logo', 'Brand Guidelines', 'Competitors', 'Review'] as const

export interface WizardData {
  org_name: string
  industry: string
  logo: File | null
  brand_guidelines: File | null
  competitors: string[]
}

export function OnboardingPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [data, setData] = useState<WizardData>({
    org_name: '',
    industry: '',
    logo: null,
    brand_guidelines: null,
    competitors: [],
  })
  const createClient = useCreateClient()

  const handleOrgInfo = (values: OrgInfoValues) => {
    setData((d) => ({ ...d, ...values }))
    setStep(1)
  }

  const handleSubmit = async () => {
    const formData = new FormData()
    formData.append('org_name', data.org_name)
    formData.append('industry', data.industry)
    if (data.logo) formData.append('logo', data.logo)
    if (data.brand_guidelines) formData.append('brand_guidelines', data.brand_guidelines)
    formData.append('competitors', JSON.stringify(data.competitors))
    const client = await createClient.mutateAsync(formData)
    navigate('/admin/mandates/new', { state: { client_id: client.id } })
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background">
      <div className="w-full max-w-xl px-4">
        <div className="flex items-center justify-between mb-8">
          {STEP_LABELS.map((label, i) => (
            <div key={i} className="flex flex-col items-center gap-1">
              <div
                className={[
                  'h-8 w-8 rounded-full flex items-center justify-center text-sm font-medium',
                  i < step
                    ? 'bg-primary text-primary-foreground'
                    : i === step
                    ? 'border-2 border-primary text-primary'
                    : 'border-2 border-muted text-muted-foreground',
                ].join(' ')}
              >
                {i < step ? '✓' : i + 1}
              </div>
              <span className="text-xs text-muted-foreground hidden sm:block">{label}</span>
            </div>
          ))}
        </div>

        {step === 0 && (
          <OrgInfoStep
            defaultValues={{ org_name: data.org_name, industry: data.industry }}
            onNext={handleOrgInfo}
          />
        )}
        {/* Steps 1-4 added in subsequent tasks */}
      </div>
    </div>
  )
}
