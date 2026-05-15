import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/store/useAuthStore'
import { login as loginApi } from '@/api/admin'

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})
type LoginFormValues = z.infer<typeof loginSchema>

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const onSubmit = async (data: LoginFormValues) => {
    setError(null)
    setLoading(true)
    try {
      const result = await loginApi(data.email, data.password)
      login(result.token, result.user)
      navigate('/admin/tenants')
    } catch {
      setError('Invalid email or password. Try any email/password in mock mode.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">NTM Admin</CardTitle>
          <p className="text-sm text-muted-foreground">Sign in to your account</p>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" placeholder="admin@ntm.com" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input type="password" placeholder="••••••••" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {error && (
                <p className="text-sm text-destructive">{error}</p>
              )}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Signing in…' : 'Sign in'}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}
