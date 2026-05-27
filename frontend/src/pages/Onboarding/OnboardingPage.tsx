import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OrgInfoStep, type OrgInfoValues } from './OrgInfoStep'
import { LogoStep } from './LogoStep'
import { BrandGuidelinesStep } from './BrandGuidelinesStep'
import { CompetitorsStep } from './CompetitorsStep'
import { ReviewStep } from './ReviewStep'
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
  const [submitError, setSubmitError] = useState<string | null>(null)
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

  const handleLogo = (file: File) => {
    setData((d) => ({ ...d, logo: file }))
    setStep(2)
  }

  const handleBrandGuidelines = (file: File) => {
    setData((d) => ({ ...d, brand_guidelines: file }))
    setStep(3)
  }

  const handleCompetitors = (competitors: string[]) => {
    setData((d) => ({ ...d, competitors }))
    setStep(4)
  }

  const handleSubmit = async () => {
    setSubmitError(null)
    try {
      const formData = new FormData()
      formData.append('org_name', data.org_name)
      formData.append('industry', data.industry)
      if (data.logo) formData.append('logo', data.logo)
      if (data.brand_guidelines) formData.append('brand_guidelines', data.brand_guidelines)
      formData.append('competitors', JSON.stringify(data.competitors))
      const client = await createClient.mutateAsync(formData)
      navigate('/mandates/new', { state: { client_id: client.id } })
    } catch {
      setSubmitError('Failed to create client. Please try again.')
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background">
      <div className="w-full max-w-xl px-4">
        {/* Step progress bar */}
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
        {step === 1 && <LogoStep onNext={handleLogo} onBack={() => setStep(0)} />}
        {step === 2 && <BrandGuidelinesStep onNext={handleBrandGuidelines} onBack={() => setStep(1)} />}
        {step === 3 && (
          <CompetitorsStep
            defaultValues={data.competitors}
            onNext={handleCompetitors}
            onBack={() => setStep(2)}
          />
        )}
        {step === 4 && (
          <ReviewStep
            data={data}
            onSubmit={handleSubmit}
            onBack={() => setStep(3)}
            isPending={createClient.isPending}
            submitError={submitError}
          />
        )}
      </div>
    </div>
  )
}
