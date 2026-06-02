import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/store/useAuthStore'
import { login as loginApi, register as registerApi } from '@/api/admin'

// ── Email identity parsing ────────────────────────────────────────────────────

const EMAIL_ROLE_MAP: Record<string, string> = {
  admin:    'Platform Admin',
  platform: 'Platform Admin',
  tenant:   'Tenant Admin',
  brand:    'Brand Manager',
  cmo:      'CMO',
  creative: 'Creative Lead',
  campaign: 'Campaign Manager',
  viewer:   'Viewer',
}

function parseEmailIdentity(email: string): { role: string; tenant: string } | null {
  if (!email.includes('@')) return null
  const [local, domain] = email.toLowerCase().split('@')
  if (!domain || !domain.includes('.')) return null
  const prefix = local.split('.')[0]
  const tenant = domain.split('.')[0]
  if (!tenant) return null
  const role = EMAIL_ROLE_MAP[prefix] ?? 'Brand Manager'
  return { role, tenant }
}

// ── Schemas ───────────────────────────────────────────────────────────────────

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})

const registerSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
})

type LoginFormValues = z.infer<typeof loginSchema>
type RegisterFormValues = z.infer<typeof registerSchema>

// ── Login Form ────────────────────────────────────────────────────────────────

function LoginForm({ onSwitch }: { onSwitch: () => void }) {
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
      navigate('/admin/onboarding')
    } catch {
      setError('Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="e.g. tenant@yourcompany.com" {...field} />
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
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </Button>
        <p className="text-center text-sm text-muted-foreground">
          Don't have an account?{' '}
          <button
            type="button"
            onClick={onSwitch}
            className="text-primary font-medium hover:underline"
          >
            Register
          </button>
        </p>
      </form>
    </Form>
  )
}

// ── Register Form ─────────────────────────────────────────────────────────────

function RegisterForm({ onSwitch }: { onSwitch: () => void }) {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: '', password: '', confirmPassword: '' },
  })

  const emailValue = useWatch({ control: form.control, name: 'email' })
  const identity = parseEmailIdentity(emailValue ?? '')

  const onSubmit = async (data: RegisterFormValues) => {
    setError(null)
    setLoading(true)
    try {
      const result = await registerApi(data.email, data.password)
      login(result.token, result.user)
      navigate('/admin/onboarding')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      if (detail === 'User already exists') {
        setError('An account with this email already exists. Please sign in instead.')
      } else {
        setError('Registration failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="e.g. tenant@yourcompany.com" {...field} />
              </FormControl>
              {identity && (
                <p className="text-xs text-muted-foreground mt-1">
                  <span className="font-medium text-foreground">Role:</span> {identity.role}
                  {' · '}
                  <span className="font-medium text-foreground">Tenant:</span> {identity.tenant}
                </p>
              )}
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
        <FormField
          control={form.control}
          name="confirmPassword"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Confirm Password</FormLabel>
              <FormControl>
                <Input type="password" placeholder="••••••••" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Creating account…' : 'Create account'}
        </Button>
        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <button
            type="button"
            onClick={onSwitch}
            className="text-primary font-medium hover:underline"
          >
            Sign in
          </button>
        </p>
      </form>
    </Form>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">NTM</CardTitle>
          <p className="text-sm text-muted-foreground">
            {mode === 'login' ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </CardHeader>
        <CardContent>
          {mode === 'login'
            ? <LoginForm onSwitch={() => setMode('register')} />
            : <RegisterForm onSwitch={() => setMode('login')} />
          }
        </CardContent>
      </Card>
    </div>
  )
}
