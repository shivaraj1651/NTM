import { useRef, useState } from 'react'
import { UploadCloud, FileText, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'

interface Props {
  onNext: (file: File) => void
  onBack: () => void
}

export function BrandGuidelinesStep({ onNext, onBack }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    if (f.size > 20 * 1024 * 1024) {
      setError('File must be under 20 MB')
      return
    }
    setError('')
    setFile(f)
  }

  const handleClear = () => {
    setFile(null)
    setError('')
    if (inputRef.current) inputRef.current.value = ''
  }

  const handleNext = () => {
    if (!file) {
      setError('Brand guidelines PDF is required')
      return
    }
    onNext(file)
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Brand Guidelines</h2>

      <div className="space-y-2">
        <Label>Brand Guidelines PDF (max 20 MB)</Label>

        {/* Hidden native input */}
        <input
          ref={inputRef}
          id="brand-input"
          type="file"
          accept="application/pdf"
          className="sr-only"
          onChange={handleChange}
        />

        {/* Upload zone */}
        <div
          className={[
            'flex flex-col items-center gap-3 rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors',
            file
              ? 'border-primary/50 bg-primary/5'
              : 'border-muted-foreground/25 bg-muted/20 hover:border-primary/40 hover:bg-muted/30',
          ].join(' ')}
        >
          {file ? (
            <>
              <FileText className="h-10 w-10 text-primary" />
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <span>{file.name}</span>
                <button
                  type="button"
                  onClick={handleClear}
                  className="rounded-full p-0.5 text-muted-foreground hover:text-destructive"
                  aria-label="remove file"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <span className="text-xs text-muted-foreground">
                {(file.size / (1024 * 1024)).toFixed(2)} MB
              </span>
            </>
          ) : (
            <>
              <UploadCloud className="h-10 w-10 text-muted-foreground/60" />
              <p className="text-sm text-muted-foreground">
                Drag and drop or click to upload
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => inputRef.current?.click()}
              >
                Browse File
              </Button>
            </>
          )}
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>

      <div className="flex gap-2">
        <Button variant="outline" onClick={onBack} className="flex-1">
          ← Back
        </Button>
        <Button onClick={handleNext} className="flex-1">
          Next →
        </Button>
      </div>
    </div>
  )
}
