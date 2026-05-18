import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface Props {
  defaultValues: string[]
  onNext: (competitors: string[]) => void
  onBack: () => void
}

export function CompetitorsStep({ defaultValues, onNext, onBack }: Props) {
  const [competitors, setCompetitors] = useState<string[]>(
    defaultValues.length ? defaultValues : ['']
  )
  const [error, setError] = useState('')

  const update = (i: number, val: string) =>
    setCompetitors((prev) => prev.map((c, j) => (j === i ? val : c)))

  const add = () => setCompetitors((prev) => [...prev, ''])

  const remove = (i: number) =>
    setCompetitors((prev) => prev.filter((_, j) => j !== i))

  const handleNext = () => {
    const valid = competitors.filter((c) => c.trim())
    if (!valid.length) {
      setError('At least one competitor is required')
      return
    }
    setError('')
    onNext(valid)
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Competitors</h2>
      <div className="space-y-2">
        <Label>Add competitor names</Label>
        {competitors.map((c, i) => (
          <div key={i} className="flex gap-2">
            <Input
              value={c}
              onChange={(e) => update(i, e.target.value)}
              placeholder={`Competitor ${i + 1}`}
            />
            {competitors.length > 1 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => remove(i)}
                type="button"
                aria-label="remove"
              >
                ✕
              </Button>
            )}
          </div>
        ))}
        <Button variant="outline" size="sm" onClick={add} type="button">
          + Add another
        </Button>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={onBack} className="flex-1">← Back</Button>
        <Button onClick={handleNext} className="flex-1">Next →</Button>
      </div>
    </div>
  )
}
