import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

const INDUSTRIES = [
  'FMCG', 'Retail', 'Finance', 'Healthcare',
  'Technology', 'Automotive', 'Entertainment', 'Telecom',
] as const

const schema = z.object({
  org_name: z.string().min(2, 'Must be at least 2 characters'),
  industry: z.string().min(1, 'Industry is required'),
})

export type OrgInfoValues = z.infer<typeof schema>

interface Props {
  defaultValues: OrgInfoValues
  onNext: (values: OrgInfoValues) => void
}

export function OrgInfoStep({ defaultValues, onNext }: Props) {
  const form = useForm<OrgInfoValues>({
    resolver: zodResolver(schema),
    defaultValues,
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onNext)} className="space-y-4">
        <h2 className="text-xl font-semibold">Organisation Info</h2>
        <FormField
          control={form.control}
          name="org_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Organisation Name</FormLabel>
              <FormControl>
                <Input placeholder="Acme Corp" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="industry"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Industry</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select industry…" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {INDUSTRIES.map((ind) => (
                    <SelectItem key={ind} value={ind}>{ind}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" className="w-full">Next →</Button>
      </form>
    </Form>
  )
}
