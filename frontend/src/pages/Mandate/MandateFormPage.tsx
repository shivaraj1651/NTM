import { useEffect, useMemo } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '@/components/PageHeader'
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { REGIONS } from '@/lib/geography'
import { useCreateMandate, useUpdateMandate } from '@/hooks/useMandates'
import { getMandateSummaryCard } from '@/api/admin'

const OBJECTIVE_VALUES = [
  'awareness', 'consideration', 'conversion', 'loyalty', 'engagement',
] as const

const CURRENCY_VALUES = ['USD', 'EUR', 'GBP', 'INR', 'AED'] as const

// Returns today as YYYY-MM-DD in local time
const todayISO = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// Returns the day after a YYYY-MM-DD string
const nextDayISO = (iso: string) => {
  if (!iso) return todayISO()
  const d = new Date(iso + 'T00:00:00')
  d.setDate(d.getDate() + 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const schema = z
  .object({
    name: z.string().min(3, 'Must be at least 3 characters'),
    objective: z.enum(OBJECTIVE_VALUES),
    region: z.string().min(1, 'Region is required'),
    countries: z.array(z.string()).min(1, 'Select at least one country'),
    total_budget: z.number().min(10000, 'Budget must be at least 10,000'),
    currency: z.enum(CURRENCY_VALUES),
    start_date: z.string()
      .min(1, 'Start date is required')
      .refine((v) => !v || v >= todayISO(), { message: 'Start date cannot be in the past' }),
    end_date: z.string().min(1, 'End date is required'),
  })
  .refine((d) => !d.start_date || !d.end_date || d.end_date > d.start_date, {
    message: 'End date must be after start date',
    path: ['end_date'],
  })

type FormValues = z.infer<typeof schema>

export function MandateFormPage() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const isEdit = !!id
  const clientId = (location.state as { client_id?: string } | null)?.client_id

  const { data: existingMandate } = useQuery({
    queryKey: ['mandate-summary', id],
    queryFn: () => getMandateSummaryCard(id!),
    enabled: isEdit,
  })

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      objective: 'awareness',
      region: '',
      countries: [],
      total_budget: 50000,
      currency: 'USD',
      start_date: '',
      end_date: '',
    },
  })

  useEffect(() => {
    if (existingMandate) {
      form.reset({
        name: existingMandate.name,
        objective: existingMandate.objective,
        region: existingMandate.region,
        countries: existingMandate.countries,
        total_budget: existingMandate.budget.total_budget,
        currency: existingMandate.budget.currency as typeof CURRENCY_VALUES[number],
        start_date: existingMandate.start_date,
        end_date: existingMandate.end_date,
      })
    }
  }, [existingMandate, form])

  const createMandate = useCreateMandate()
  const updateMandate = useUpdateMandate(id ?? '')
  const isPending = createMandate.isPending || updateMandate.isPending

  const watchRegion = form.watch('region')
  const watchCurrency = form.watch('currency')
  const watchStartDate = form.watch('start_date')
  const today = useMemo(() => todayISO(), [])
  const minEndDate = useMemo(() => nextDayISO(watchStartDate), [watchStartDate])

  const onSubmit = async (values: FormValues) => {
    try {
      if (isEdit) {
        await updateMandate.mutateAsync(values)
        navigate(`/mandates/${id}/summary`)
      } else {
        if (!clientId) return
        const mandate = await createMandate.mutateAsync({ ...values, client_id: clientId })
        navigate(`/mandates/${mandate.id}/summary`)
      }
    } catch {
      // mutation error handled via React Query's isError state
    }
  }

  return (
    <div>
      <PageHeader
        title={isEdit ? 'Edit Mandate' : 'New Mandate'}
        description={isEdit ? 'Update mandate details.' : 'Fill in the mandate details.'}
      />
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 max-w-2xl">
          {/* Name */}
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Mandate Name</FormLabel>
                <FormControl>
                  <Input placeholder="Q3 Brand Awareness" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Objective */}
          <FormField
            control={form.control}
            name="objective"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Objective</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select objective…" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {OBJECTIVE_VALUES.map((obj) => (
                      <SelectItem key={obj} value={obj} className="capitalize">
                        {obj}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Region */}
          <FormField
            control={form.control}
            name="region"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Region</FormLabel>
                <Select
                  onValueChange={(val) => {
                    field.onChange(val)
                    form.setValue('countries', [])
                  }}
                  value={field.value}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select region…" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {Object.keys(REGIONS).map((r) => (
                      <SelectItem key={r} value={r}>{r}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Countries */}
          {watchRegion && (
            <FormField
              control={form.control}
              name="countries"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Countries</FormLabel>
                  <div className="grid grid-cols-2 gap-2">
                    {REGIONS[watchRegion as keyof typeof REGIONS]?.map((country) => (
                      <label
                        key={country}
                        className="flex items-center gap-2 cursor-pointer text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={field.value.includes(country)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              field.onChange([...field.value, country])
                            } else {
                              field.onChange(field.value.filter((c) => c !== country))
                            }
                          }}
                          className="h-4 w-4 rounded border-gray-300"
                        />
                        {country}
                      </label>
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
          )}

          {/* Budget slider */}
          <FormField
            control={form.control}
            name="total_budget"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Total Budget</FormLabel>
                <div className="space-y-3">
                  <Slider
                    min={10000}
                    max={10000000}
                    step={10000}
                    value={[field.value]}
                    onValueChange={([v]) => field.onChange(v)}
                  />
                  <div className="flex items-center gap-2">
                    <FormControl>
                      <Input
                        type="number"
                        min={10000}
                        max={10000000}
                        step={10000}
                        value={field.value}
                        onChange={(e) => field.onChange(Number(e.target.value))}
                        className="w-40"
                      />
                    </FormControl>
                    <span className="text-sm text-muted-foreground">{watchCurrency}</span>
                  </div>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Currency */}
          <FormField
            control={form.control}
            name="currency"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Currency</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select currency…" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {CURRENCY_VALUES.map((c) => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="start_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Start Date</FormLabel>
                  <FormControl>
                    <Input
                      type="date"
                      min={today}
                      {...field}
                      onChange={(e) => {
                        field.onChange(e)
                        // Reset end_date if it's now invalid
                        const current = form.getValues('end_date')
                        if (current && current <= e.target.value) {
                          form.setValue('end_date', '', { shouldValidate: true })
                        }
                      }}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="end_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>End Date</FormLabel>
                  <FormControl>
                    <Input
                      type="date"
                      min={minEndDate}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <Button type="submit" disabled={isPending}>
            {isPending ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Mandate'}
          </Button>
        </form>
      </Form>
    </div>
  )
}
