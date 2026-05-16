import type { AnalyticsSummary, TrendPoint } from '@/types/admin'

const TODAY = new Date().toISOString().split('T')[0]

export const analyticsSummaries: AnalyticsSummary[] = [
  {
    mandate_id: 'm-001',
    date: TODAY,
    summary_generated_at: new Date().toISOString(),
    activations: [
      {
        activation_id: 'act-001-ga',
        campaign_id: 'camp-001',
        channel: 'google_ads',
        sub_channel: 'Google Search',
        status: 'green',
        kpi_results: [{ kpi_name: 'conversion_rate', target: 3.0, actual: 3.5, achievement_percent: 16.7, threshold_unit: 'percent', status: 'green' }],
        metrics: { impressions: 12000, clicks: 600, conversions: 21, spend: 900 },
      },
      {
        activation_id: 'act-001-ma',
        campaign_id: 'camp-001',
        channel: 'meta_ads',
        status: 'amber',
        kpi_results: [{ kpi_name: 'roas', target: 3.0, actual: 2.7, achievement_percent: -10.0, threshold_unit: 'ratio', status: 'amber' }],
        metrics: { impressions: 8000, clicks: 400, conversions: 12, spend: 600 },
      },
      {
        activation_id: 'act-001-li',
        campaign_id: 'camp-001',
        channel: 'linkedin_ads',
        status: 'green',
        kpi_results: [{ kpi_name: 'ctr', target: 0.03, actual: 0.04, achievement_percent: 33.3, threshold_unit: 'percent', status: 'green' }],
        metrics: { impressions: 5000, clicks: 200, conversions: 5, spend: 400 },
      },
    ],
    red_alerts: [],
    summary_by_channel: {
      google_ads: { total: 1, red: 0, amber: 0, green: 1 },
      meta_ads: { total: 1, red: 0, amber: 1, green: 0 },
      linkedin_ads: { total: 1, red: 0, amber: 0, green: 1 },
    },
  },
  {
    mandate_id: 'm-002',
    date: TODAY,
    summary_generated_at: new Date().toISOString(),
    activations: [
      {
        activation_id: 'act-002-ga',
        campaign_id: 'camp-002',
        channel: 'google_ads',
        sub_channel: 'Google Display',
        status: 'red',
        kpi_results: [{ kpi_name: 'conversion_rate', target: 3.0, actual: 2.0, achievement_percent: -33.3, threshold_unit: 'percent', status: 'red' }],
        metrics: { impressions: 15000, clicks: 300, conversions: 6, spend: 1200 },
      },
      {
        activation_id: 'act-002-ma',
        campaign_id: 'camp-002',
        channel: 'meta_ads',
        status: 'green',
        kpi_results: [{ kpi_name: 'roas', target: 2.0, actual: 2.5, achievement_percent: 25.0, threshold_unit: 'ratio', status: 'green' }],
        metrics: { impressions: 9000, clicks: 450, conversions: 18, spend: 700 },
      },
      {
        activation_id: 'act-002-li',
        campaign_id: 'camp-002',
        channel: 'linkedin_ads',
        status: 'amber',
        kpi_results: [{ kpi_name: 'ctr', target: 0.05, actual: 0.045, achievement_percent: -10.0, threshold_unit: 'percent', status: 'amber' }],
        metrics: { impressions: 4000, clicks: 180, conversions: 4, spend: 350 },
      },
    ],
    red_alerts: [
      { activation_id: 'act-002-ga', campaign_id: 'camp-002', channel: 'google_ads', failed_kpi: 'conversion_rate', severity: 'red' },
    ],
    summary_by_channel: {
      google_ads: { total: 1, red: 1, amber: 0, green: 0 },
      meta_ads: { total: 1, red: 0, amber: 0, green: 1 },
      linkedin_ads: { total: 1, red: 0, amber: 1, green: 0 },
    },
  },
  {
    mandate_id: 'm-003',
    date: TODAY,
    summary_generated_at: new Date().toISOString(),
    activations: [
      {
        activation_id: 'act-003-ga',
        campaign_id: 'camp-003',
        channel: 'google_ads',
        status: 'amber',
        kpi_results: [{ kpi_name: 'cpc', target: 1.50, actual: 1.65, achievement_percent: -10.0, threshold_unit: 'currency', status: 'amber' }],
        metrics: { impressions: 10000, clicks: 500, conversions: 15, spend: 825 },
      },
      {
        activation_id: 'act-003-ma',
        campaign_id: 'camp-003',
        channel: 'meta_ads',
        status: 'red',
        kpi_results: [{ kpi_name: 'roas', target: 3.0, actual: 1.5, achievement_percent: -50.0, threshold_unit: 'ratio', status: 'red' }],
        metrics: { impressions: 6000, clicks: 300, conversions: 5, spend: 800 },
      },
      {
        activation_id: 'act-003-li',
        campaign_id: 'camp-003',
        channel: 'linkedin_ads',
        status: 'green',
        kpi_results: [{ kpi_name: 'engagement_rate', target: 0.05, actual: 0.06, achievement_percent: 20.0, threshold_unit: 'percent', status: 'green' }],
        metrics: { impressions: 3500, clicks: 210, conversions: 8, spend: 280 },
      },
    ],
    red_alerts: [
      { activation_id: 'act-003-ma', campaign_id: 'camp-003', channel: 'meta_ads', failed_kpi: 'roas', severity: 'red' },
    ],
    summary_by_channel: {
      google_ads: { total: 1, red: 0, amber: 1, green: 0 },
      meta_ads: { total: 1, red: 1, amber: 0, green: 0 },
      linkedin_ads: { total: 1, red: 0, amber: 0, green: 1 },
    },
  },
]

// 30 days of trend data
function generateTrends(): TrendPoint[] {
  const points: TrendPoint[] = []
  const base = new Date()
  base.setDate(base.getDate() - 29)
  const baseSpend = 520
  const baseImpressions = 9200
  for (let i = 0; i < 30; i++) {
    const d = new Date(base.getTime() + i * 24 * 60 * 60 * 1000)
    points.push({
      date: d.toISOString().split('T')[0],
      spend: baseSpend + i * 12 + (i % 3 === 0 ? 40 : 0),
      impressions: baseImpressions + i * 120 + (i % 5 === 0 ? 500 : 0),
    })
  }
  return points
}

export const analyticsTrends: TrendPoint[] = generateTrends()

export const kpiActualsDb: Record<string, Record<string, Record<string, number>>> = {
  'c-004': {
    'act-001': { 'Clicks': 2800, 'CTR': 3.1, 'Conversions': 130 },
    'act-002': { 'Impressions': 72000, 'Engagement Rate': 1.6, 'Lead Gen Forms': 175 },
    'act-003': { 'Reach': 140000, 'ROAS': 3.8 },
    'act-004': { 'Video Views': 17500, 'Click-Through': 1.9 },
  },
}
