import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface Entry {
  id: string
  val: string
}

interface Props {
  defaultValues: string[]
  onNext: (competitors: string[]) => void
  onBack: () => void
}

function makeEntry(val = ''): Entry {
  return { id: crypto.randomUUID(), val }
}

export function CompetitorsStep({ defaultValues, onNext, onBack }: Props) {
  const [entries, setEntries] = useState<Entry[]>(
    defaultValues.length ? defaultValues.map(makeEntry) : [makeEntry()]
  )
  const [error, setError] = useState('')

  const update = (id: string, val: string) =>
    setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, val } : e)))

  const add = () => setEntries((prev) => [...prev, makeEntry()])

  const remove = (id: string) =>
    setEntries((prev) => prev.filter((e) => e.id !== id))

  const handleNext = () => {
    const valid = entries.map((e) => e.val.trim()).filter(Boolean)
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
        {entries.map((e, i) => (
          <div key={e.id} className="flex gap-2">
            <Input
              value={e.val}
              onChange={(ev) => update(e.id, ev.target.value)}
              placeholder={`Competitor ${i + 1}`}
            />
            {entries.length > 1 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => remove(e.id)}
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
        <Button variant="outline" onClick={onBack} type="button" className="flex-1">← Back</Button>
        <Button onClick={handleNext} type="button" className="flex-1">Next →</Button>
      </div>
    </div>
  )
}
