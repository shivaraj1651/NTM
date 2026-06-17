import { useState } from 'react'
import { User, Bell, Shield, Save, Check } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/store/useAuthStore'

const SETTINGS_KEY = 'ntm:settings'

interface AppSettings {
  emailNotifications: boolean
  campaignAlerts: boolean
  weeklyDigest: boolean
  dateFormat: 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD'
  currency: string
}

const DEFAULTS: AppSettings = {
  emailNotifications: true,
  campaignAlerts: true,
  weeklyDigest: false,
  dateFormat: 'DD/MM/YYYY',
  currency: 'USD',
}

function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS
  } catch {
    return DEFAULTS
  }
}

function saveSettings(s: AppSettings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s))
}

function Toggle({
  checked,
  onChange,
  id,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  id: string
}) {
  return (
    <button
      id={id}
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        checked ? 'bg-primary' : 'bg-input'
      }`}
    >
      <span
        className={`pointer-events-none block h-4 w-4 rounded-full bg-background shadow-lg ring-0 transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

function Section({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: React.ElementType
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  )
}

function Row({ label, htmlFor, children }: { label: string; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <Label htmlFor={htmlFor} className="text-sm font-normal leading-snug">
        {label}
      </Label>
      {children}
    </div>
  )
}

export function SettingsPage() {
  const { user } = useAuthStore()
  const [settings, setSettings] = useState<AppSettings>(loadSettings)
  const [saved, setSaved] = useState(false)

  // Password change state
  const [pwForm, setPwForm] = useState({ current: '', next: '', confirm: '' })
  const [pwMsg, setPwMsg] = useState<{ type: 'error' | 'info'; text: string } | null>(null)

  const update = <K extends keyof AppSettings>(key: K, val: AppSettings[K]) =>
    setSettings((prev) => ({ ...prev, [key]: val }))

  const handleSavePreferences = () => {
    saveSettings(settings)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleChangePassword = () => {
    if (!pwForm.current) {
      setPwMsg({ type: 'error', text: 'Enter your current password.' })
      return
    }
    if (pwForm.next.length < 8) {
      setPwMsg({ type: 'error', text: 'New password must be at least 8 characters.' })
      return
    }
    if (pwForm.next !== pwForm.confirm) {
      setPwMsg({ type: 'error', text: 'New passwords do not match.' })
      return
    }
    // Backend endpoint not yet implemented — show informational message
    setPwMsg({
      type: 'info',
      text: 'Password change endpoint is not yet available. Contact your administrator.',
    })
    setPwForm({ current: '', next: '', confirm: '' })
  }

  const roleLabel = (user?.role ?? 'Unknown').replace(/_/g, ' ')

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader title="Settings" description="Manage your profile, notifications, and preferences." />

      {/* Profile */}
      <Section icon={User} title="Profile" description="Your account details.">
        <Row label="Email">
          <span className="text-sm text-muted-foreground">{user?.email ?? '—'}</span>
        </Row>
        <Separator />
        <Row label="Role">
          <Badge variant="secondary" className="capitalize">
            {roleLabel}
          </Badge>
        </Row>
        <Separator />
        <Row label="Tenant ID">
          <span className="font-mono text-xs text-muted-foreground">
            {user?.tenant_id ?? '—'}
          </span>
        </Row>
        <p className="text-xs text-muted-foreground pt-1">
          Profile details are managed by your platform administrator.
        </p>
      </Section>

      {/* Notifications */}
      <Section
        icon={Bell}
        title="Notifications"
        description="Control which alerts are sent to you."
      >
        <Row label="Email notifications" htmlFor="toggle-email">
          <Toggle
            id="toggle-email"
            checked={settings.emailNotifications}
            onChange={(v) => update('emailNotifications', v)}
          />
        </Row>
        <Separator />
        <Row label="Campaign alerts (red KPI threshold breaches)" htmlFor="toggle-alerts">
          <Toggle
            id="toggle-alerts"
            checked={settings.campaignAlerts}
            onChange={(v) => update('campaignAlerts', v)}
          />
        </Row>
        <Separator />
        <Row label="Weekly performance digest" htmlFor="toggle-digest">
          <Toggle
            id="toggle-digest"
            checked={settings.weeklyDigest}
            onChange={(v) => update('weeklyDigest', v)}
          />
        </Row>
      </Section>

      {/* Preferences */}
      <Section
        icon={Save}
        title="Display Preferences"
        description="Formatting and localisation options."
      >
        <Row label="Date format" htmlFor="date-format">
          <select
            id="date-format"
            value={settings.dateFormat}
            onChange={(e) => update('dateFormat', e.target.value as AppSettings['dateFormat'])}
            className="h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="DD/MM/YYYY">DD/MM/YYYY</option>
            <option value="MM/DD/YYYY">MM/DD/YYYY</option>
            <option value="YYYY-MM-DD">YYYY-MM-DD</option>
          </select>
        </Row>
        <Separator />
        <Row label="Currency" htmlFor="currency">
          <select
            id="currency"
            value={settings.currency}
            onChange={(e) => update('currency', e.target.value)}
            className="h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="USD">USD — US Dollar</option>
            <option value="EUR">EUR — Euro</option>
            <option value="GBP">GBP — British Pound</option>
            <option value="INR">INR — Indian Rupee</option>
            <option value="AED">AED — UAE Dirham</option>
          </select>
        </Row>
        <div className="pt-2">
          <Button size="sm" onClick={handleSavePreferences}>
            {saved ? (
              <>
                <Check className="h-4 w-4 mr-2" />
                Saved
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save preferences
              </>
            )}
          </Button>
        </div>
      </Section>

      {/* Security */}
      <Section icon={Shield} title="Security" description="Change your login password.">
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="pw-current">Current password</Label>
            <Input
              id="pw-current"
              type="password"
              autoComplete="current-password"
              value={pwForm.current}
              onChange={(e) => setPwForm((p) => ({ ...p, current: e.target.value }))}
              className="max-w-sm"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="pw-new">New password</Label>
            <Input
              id="pw-new"
              type="password"
              autoComplete="new-password"
              value={pwForm.next}
              onChange={(e) => setPwForm((p) => ({ ...p, next: e.target.value }))}
              className="max-w-sm"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="pw-confirm">Confirm new password</Label>
            <Input
              id="pw-confirm"
              type="password"
              autoComplete="new-password"
              value={pwForm.confirm}
              onChange={(e) => setPwForm((p) => ({ ...p, confirm: e.target.value }))}
              className="max-w-sm"
            />
          </div>

          {pwMsg && (
            <p
              className={`text-xs ${
                pwMsg.type === 'error' ? 'text-red-600' : 'text-muted-foreground'
              }`}
            >
              {pwMsg.text}
            </p>
          )}

          <Button size="sm" variant="outline" onClick={handleChangePassword}>
            <Shield className="h-4 w-4 mr-2" />
            Update password
          </Button>
        </div>
      </Section>
    </div>
  )
}
