import { useNavigate, useParams } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { PageHeader } from '@/components/PageHeader'

const MOCK_CI_REPORT = {
  generated_at: '2026-05-21T06:00:00Z',
  competitors: [
    {
      name: 'Competitor Alpha',
      channels: 'Digital, OOH, TV',
      key_message: 'Premium quality at scale',
      threat_level: 'high' as const,
    },
    {
      name: 'Competitor Beta',
      channels: 'Social, Search',
      key_message: 'Fast delivery, best price',
      threat_level: 'medium' as const,
    },
    {
      name: 'Competitor Gamma',
      channels: 'Print, Radio',
      key_message: 'Trusted by millions',
      threat_level: 'low' as const,
    },
  ],
  whitespace: [
    'No competitor owns LinkedIn for B2B decision-makers in Tier-2 cities',
    'Radio in regional languages (Kannada, Telugu) is uncontested',
    'Influencer marketing in the micro-tier (10k–100k followers) is underutilised',
    'Morning commute OOH slots at metro stations are unclaimed in Pune and Hyderabad',
  ],
  differentiation_vectors: [
    'Lead with regional-language creative to capture Tier-2 audiences competitors ignore',
    'Invest in LinkedIn Sponsored Content targeting senior decision-makers',
    'Partner with micro-influencers for authentic, cost-efficient reach',
    'Use radio for brand recall in markets where competitors rely only on digital',
  ],
}

const threatBadge = (level: 'high' | 'medium' | 'low') => {
  const map = {
    high: 'destructive',
    medium: 'secondary',
    low: 'outline',
  } as const
  return <Badge variant={map[level]}>{level.toUpperCase()}</Badge>
}

export function CIReportPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Competitive Intelligence Report"
        description="Approval Gate 2 — Review research before proceeding to campaign strategy."
      />

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>Generated:</span>
        <span>{new Date(MOCK_CI_REPORT.generated_at).toLocaleString()}</span>
      </div>

      {/* Competitor Matrix */}
      <Card>
        <CardHeader>
          <CardTitle>Competitor Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Competitor</TableHead>
                <TableHead>Active Channels</TableHead>
                <TableHead>Key Message</TableHead>
                <TableHead>Threat Level</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {MOCK_CI_REPORT.competitors.map((c) => (
                <TableRow key={c.name}>
                  <TableCell className="font-medium">{c.name}</TableCell>
                  <TableCell>{c.channels}</TableCell>
                  <TableCell>{c.key_message}</TableCell>
                  <TableCell>{threatBadge(c.threat_level)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Whitespace */}
      <Card>
        <CardHeader>
          <CardTitle>Whitespace Opportunities</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {MOCK_CI_REPORT.whitespace.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-green-500" />
                {item}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* Differentiation Vectors */}
      <Card>
        <CardHeader>
          <CardTitle>Recommended Differentiation Vectors</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {MOCK_CI_REPORT.differentiation_vectors.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="mt-0.5 shrink-0 text-blue-500 font-bold">{i + 1}.</span>
                {item}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* Approval Gate 2 Actions */}
      <div className="flex gap-3 pt-2">
        <Button
          className="flex-1"
          onClick={() => navigate(`/campaigns/${id}/concepts`)}
        >
          Approve & Proceed to Campaign Strategy
        </Button>
        <Button variant="outline" onClick={() => alert('Research request submitted.')}>
          Request More Research
        </Button>
      </div>
    </div>
  )
}
