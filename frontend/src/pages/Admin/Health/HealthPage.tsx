import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useHealth } from '@/hooks/useHealth'
import type { HealthStatus } from '@/types/admin'

type ServiceStatus = HealthStatus['api']

const statusVariant = (s: ServiceStatus): 'default' | 'secondary' | 'destructive' => {
  if (s === 'ok') return 'default'
  if (s === 'degraded') return 'secondary'
  return 'destructive'
}

interface LatencyPoint { time: string; ms: number }

export function HealthPage() {
  const { data, dataUpdatedAt } = useHealth()
  const [latencyHistory, setLatencyHistory] = useState<LatencyPoint[]>([])

  useEffect(() => {
    if (!data) return
    const point: LatencyPoint = {
      time: new Date(dataUpdatedAt).toLocaleTimeString(),
      ms: data.latency_ms,
    }
    setLatencyHistory((prev) => [...prev.slice(-9), point])
  }, [data, dataUpdatedAt])

  const services: { label: string; key: keyof Pick<HealthStatus, 'api' | 'db' | 'celery'> }[] = [
    { label: 'API',           key: 'api' },
    { label: 'PostgreSQL',    key: 'db' },
    { label: 'Celery Worker', key: 'celery' },
  ]

  return (
    <div>
      <PageHeader
        title="System Health"
        description="Auto-refreshes every 30 seconds."
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {services.map(({ label, key }) => (
          <Card key={key}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data ? (
                <div className="space-y-1">
                  <Badge variant={statusVariant(data[key])} className="capitalize">
                    {data[key]}
                  </Badge>
                  <p className="text-xs text-muted-foreground">
                    Last checked: {new Date(dataUpdatedAt).toLocaleTimeString()}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">Fetching…</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">API Latency (ms) — last 10 polls</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={latencyHistory}>
              <XAxis dataKey="time" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="ms"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
