import { Button } from '@/components/ui/button'
import type { WizardData } from './OnboardingPage'

interface Props {
  data: WizardData
  onSubmit: () => void
  onBack: () => void
  isPending: boolean
}

export function ReviewStep({ data, onSubmit, onBack, isPending }: Props) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Review & Submit</h2>
      <div className="rounded-md border p-4 space-y-3 text-sm">
        <div><span className="font-medium">Organisation:</span> {data.org_name}</div>
        <div><span className="font-medium">Industry:</span> {data.industry}</div>
        <div><span className="font-medium">Logo:</span> {data.logo?.name ?? '—'}</div>
        <div>
          <span className="font-medium">Brand Guidelines:</span>{' '}
          {data.brand_guidelines?.name ?? '—'}
        </div>
        <div>
          <span className="font-medium">Competitors:</span>{' '}
          {data.competitors.length ? data.competitors.join(', ') : '—'}
        </div>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={onBack} className="flex-1" disabled={isPending}>
          ← Back
        </Button>
        <Button onClick={onSubmit} className="flex-1" disabled={isPending}>
          {isPending ? 'Submitting…' : 'Submit →'}
        </Button>
      </div>
    </div>
  )
}
