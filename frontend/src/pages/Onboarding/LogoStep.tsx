import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface Props {
  onNext: (file: File) => void
  onBack: () => void
}

export function LogoStep({ onNext, onBack }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    if (f.size > 5 * 1024 * 1024) {
      setError('File must be under 5 MB')
      return
    }
    setError('')
    setFile(f)
  }

  const handleNext = () => {
    if (!file) {
      setError('Logo is required')
      return
    }
    onNext(file)
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Company Logo</h2>
      <div className="space-y-2">
        <Label htmlFor="logo-input">Logo (image, max 5 MB)</Label>
        <Input id="logo-input" type="file" accept="image/*" onChange={handleChange} />
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={onBack} className="flex-1">← Back</Button>
        <Button onClick={handleNext} className="flex-1">Next →</Button>
      </div>
    </div>
  )
}
