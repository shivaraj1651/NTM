import { http, HttpResponse } from 'msw'
import * as db from '../db/campaigns'
import type { Campaign, KpiConfig } from '@/types/admin'
import { kpiActualsDb } from '../db/analytics'
import { mandateStore } from '../db/mandates'

const IMAGE_SIZES: Record<string, string> = {
  square: '1024x1024/1a1a2e/ffffff?text=Square+Ad',
  landscape: '1344x768/16213e/ffffff?text=Landscape+Ad',
  portrait: '768x1344/0f3460/ffffff?text=Portrait+Ad',
}

const AUDIO_POOL = [
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
]

export const campaignHandlers = [
  http.get('/api/v1/campaigns', ({ request }) => {
    const tenantId = new URL(request.url).searchParams.get('tenant_id')
    const results = Object.values(db.campaignStore).filter(
      (c) => !tenantId || c.tenant_id === tenantId
    )
    return HttpResponse.json(results)
  }),

  http.post('/api/v1/campaigns', async ({ request }) => {
    const { mandate_id } = (await request.json()) as { mandate_id: string }
    const mandate = mandateStore[mandate_id]
    if (!mandate) return new HttpResponse(null, { status: 404 })
    const newId = `c-${Date.now()}`
    const newCampaign: Campaign = {
      id: newId,
      mandate_id,
      tenant_id: mandate.tenant_id,
      status: 'concepts_ready',
      concepts: db.generateConcepts(mandate_id),
      selected_concept_id: null,
      activation_plan: [],
      budget_proposal: null,
      creative_assets: null,
      kpi_configs: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    db.campaignStore[newId] = newCampaign
    return HttpResponse.json(newCampaign, { status: 201 })
  }),

  http.get('/api/v1/campaigns/:id', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(campaign)
  }),

  http.post('/api/v1/campaigns/:id/confirm', async ({ params, request }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    const { selected_concept_id } = (await request.json()) as { selected_concept_id: string }
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'confirmed',
      selected_concept_id,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.get('/api/v1/campaigns/:id/activation-plan', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    if (campaign.status === 'confirmed') {
      db.campaignStore[campaign.id] = {
        ...campaign,
        status: 'planned',
        activation_plan: db.generateActivationPlan(campaign.mandate_id),
        updated_at: new Date().toISOString(),
      }
    }
    return HttpResponse.json(db.campaignStore[params.id as string])
  }),

  http.post('/api/v1/campaigns/:id/approve-budget', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'budget_proposed',
      budget_proposal: db.generateBudgetProposal(campaign.activation_plan ?? []),
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.post('/api/v1/campaigns/:id/confirm-budget', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'approved',
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.post('/api/v1/campaigns/:id/generate-creatives', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    const creative_assets = db.generateCreativeAssets(campaign.id)
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'creative_ready',
      creative_assets,
      updated_at: new Date().toISOString(),
    }
    // Populate creativesStore so Creative Studio shows these assets immediately
    for (const c of db.flattenCreativeAssets(campaign.id, creative_assets)) {
      db.creativesStore[c.id as string] = c
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  // POST /api/v1/campaigns/:id/creatives/stage — advance stage
  http.post('/api/v1/campaigns/:id/creatives/stage', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign?.creative_assets) return new HttpResponse(null, { status: 404 })
    const current = campaign.creative_assets.stage
    const next: Record<string, string> = {
      internal_review: 'client_review',
      client_review: 'locked',
    }
    const nextStage = next[current]
    if (!nextStage) return new HttpResponse(null, { status: 400 })
    db.campaignStore[campaign.id] = {
      ...campaign,
      creative_assets: { ...campaign.creative_assets, stage: nextStage as any },
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  // POST /api/v1/campaigns/:id/creatives/:kind/:assetId/review
  http.post('/api/v1/campaigns/:id/creatives/:kind/:assetId/review', async ({ params, request }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign?.creative_assets) return new HttpResponse(null, { status: 404 })
    const { action } = (await request.json()) as { action: string; comment?: string }
    const { kind, assetId } = params as { kind: string; assetId: string }
    const approved = action === 'approve' ? true : action === 'reject' ? false : null

    let assets = campaign.creative_assets
    const patchAsset = (a: any) =>
      a.asset_type === assetId || a.id === assetId
        ? {
            ...a,
            approved,
            revision_count: action === 'request_change' ? (a.revision_count ?? 0) + 1 : a.revision_count,
          }
        : a

    if (kind === 'copy') assets = { ...assets, copy: assets.copy.map(patchAsset) }
    else if (kind === 'scripts') assets = { ...assets, scripts: assets.scripts.map(patchAsset) }
    else if (kind === 'images') assets = { ...assets, images: assets.images.map(patchAsset) }
    else if (kind === 'audio') assets = { ...assets, audio: assets.audio.map(patchAsset) }

    // Auto-lock: if client_review and every asset is approved, advance to locked
    if (assets.stage === 'client_review') {
      const allApproved = [
        ...assets.copy.map((a: any) => a.approved),
        ...assets.scripts.map((a: any) => a.approved),
        ...assets.images.map((a: any) => a.approved),
        ...assets.audio.map((a: any) => a.approved),
      ].every(Boolean)
      if (allApproved) assets = { ...assets, stage: 'locked' as any }
    }

    db.campaignStore[campaign.id] = { ...campaign, creative_assets: assets, updated_at: new Date().toISOString() }

    // Sync approval state into creativesStore so Creative Studio badge updates persist
    const newStatus = approved === true ? 'internal_approved' : approved === false ? 'revision_requested' : 'ai_draft'
    const existingCreative = db.creativesStore[assetId] as Record<string, unknown> | undefined
    if (existingCreative) {
      db.creativesStore[assetId] = {
        ...existingCreative,
        validation_status: newStatus,
        status: newStatus,
        updated_at: new Date().toISOString(),
      }
    }

    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.post('/api/v1/campaigns/:id/creatives/:assetKind/:assetId/regenerate', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign?.creative_assets) return new HttpResponse(null, { status: 404 })
    const { assetKind, assetId } = params as { assetKind: string; assetId: string }
    const fresh = db.generateCreativeAssets(campaign.id)
    let assets = campaign.creative_assets

    if (assetKind === 'copy') {
      const freshAsset = fresh.copy.find((a) => a.asset_type === assetId)
      if (freshAsset) {
        assets = { ...assets, copy: assets.copy.map((a) => a.asset_type === assetId ? { ...freshAsset, approved: null } : a) }
      }
    } else if (assetKind === 'scripts') {
      const idx = assets.scripts.findIndex((s) => s.id === assetId)
      if (idx >= 0 && fresh.scripts[idx]) {
        const updated = [...assets.scripts]
        updated[idx] = { ...fresh.scripts[idx], id: assetId, approved: null }
        assets = { ...assets, scripts: updated }
      }
    } else if (assetKind === 'images') {
      assets = {
        ...assets,
        images: assets.images.map((img) =>
          img.id === assetId
            ? { ...img, url: `https://placehold.co/${IMAGE_SIZES[img.format]}&t=${Date.now()}`, approved: null }
            : img
        ),
      }
    } else if (assetKind === 'audio') {
      const idx = assets.audio.findIndex((a) => a.id === assetId)
      if (idx >= 0) {
        const updated = [...assets.audio]
        updated[idx] = { ...updated[idx], url: AUDIO_POOL[(idx + 1) % AUDIO_POOL.length], approved: null }
        assets = { ...assets, audio: updated }
      }
    }

    db.campaignStore[campaign.id] = { ...campaign, creative_assets: assets, updated_at: new Date().toISOString() }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.post('/api/v1/campaigns/:id/go-live', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    const kpi_configs: KpiConfig[] = (campaign.activation_plan ?? []).flatMap((act) =>
      (act.kpis ?? []).map((kpi) => ({
        activation_id: act.id,
        kpi_name: kpi.name,
        unit: kpi.unit,
        target: kpi.target,
        green_threshold: 90,
        amber_threshold: 70,
      }))
    )
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'live',
      kpi_configs,
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  // Backend-canonical KPIs source: GET /campaigns/:id/analytics (activations[].kpi_results[])
  http.get('/api/v1/campaigns/:id/analytics', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json({
      campaign_id: params.id,
      activations: [
        {
          activation_id: 'act-analytics-1',
          channel: 'Google Ads',
          sub_channel: 'Search',
          status: 'green',
          kpi_results: [
            { kpi_name: 'Clicks', target: 1000, actual: 1200, achievement_percent: 120, threshold_unit: 'count', status: 'green' },
            { kpi_name: 'CTR', target: 2, actual: 2.5, achievement_percent: 125, threshold_unit: 'percent', status: 'green' },
          ],
        },
      ],
    })
  }),

  http.get('/api/v1/campaigns/:id/kpis', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    const rows = (campaign.kpi_configs ?? []).map((config) => {
      const actual = kpiActualsDb[campaign.id]?.[config.activation_id]?.[config.kpi_name] ?? 0
      const achievement_percent =
        config.target > 0 ? Math.round((actual / config.target) * 1000) / 10 : 0
      const status: 'green' | 'amber' | 'red' =
        achievement_percent >= config.green_threshold
          ? 'green'
          : achievement_percent >= config.amber_threshold
          ? 'amber'
          : 'red'
      const act = (campaign.activation_plan ?? []).find((a) => a.id === config.activation_id)
      return {
        activation_id: config.activation_id,
        channel: act?.channel ?? '',
        sub_channel: act?.sub_channel ?? '',
        kpi_name: config.kpi_name,
        unit: config.unit,
        target: config.target,
        actual,
        achievement_percent,
        green_threshold: config.green_threshold,
        amber_threshold: config.amber_threshold,
        status,
      }
    })
    return HttpResponse.json(rows)
  }),

  http.patch(
    '/api/v1/campaigns/:id/kpi-configs/:activationId/:kpiName',
    async ({ params, request }) => {
      const campaign = db.campaignStore[params.id as string]
      if (!campaign) return new HttpResponse(null, { status: 404 })
      const { activationId, kpiName } = params as { activationId: string; kpiName: string }
      const patch = (await request.json()) as {
        target?: number
        green_threshold?: number
        amber_threshold?: number
      }
      db.campaignStore[campaign.id] = {
        ...campaign,
        kpi_configs: campaign.kpi_configs.map((cfg) =>
          cfg.activation_id === activationId && cfg.kpi_name === kpiName
            ? { ...cfg, ...patch }
            : cfg
        ),
        updated_at: new Date().toISOString(),
      }
      return HttpResponse.json(db.campaignStore[campaign.id])
    }
  ),

  // Physical Activation Log — M8
  http.get('/api/v1/activations/:activationId/physical-logs', ({ params }) => {
    const logs = (db.physicalLogStore[params.activationId as string] ?? [])
    return HttpResponse.json(logs)
  }),

  http.post('/api/v1/activations/:activationId/log-physical', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const log = {
      id: `pal-${Date.now()}`,
      tenant_id: 'tenant-1',
      campaign_id: body.campaign_id ?? '',
      activation_id: params.activationId as string,
      event_type: body.event_type ?? 'proof_of_execution',
      channel: body.channel ?? '',
      payload: {
        actual_run_date: body.actual_run_date,
        actual_cost: body.actual_cost,
        vendor_name: body.vendor_name,
        grp_circulation: body.grp_circulation,
        proof_urls: body.proof_urls ?? [],
        notes: body.notes,
        logged_by: 'mock-user',
      },
      logged_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
    }
    // Spread + reassign on the Proxy key triggers localStorage persist.
    // Direct .push() on a nested array bypasses the Proxy trap and loses data on reload.
    db.physicalLogStore[params.activationId as string] = [
      ...(db.physicalLogStore[params.activationId as string] ?? []),
      log,
    ]
    return HttpResponse.json(log, { status: 201 })
  }),

  // ── Activations resource (PRD Section 10) ──────────────────────────────────

  http.get('/api/v1/activations', ({ request }) => {
    const url = new URL(request.url)
    const campaignId = url.searchParams.get('campaign_id')
    const status = url.searchParams.get('status')
    let activations = Object.values(db.activationStore ?? {})
    if (campaignId) activations = activations.filter((a: any) => a.campaign_id === campaignId)
    if (status) activations = activations.filter((a: any) => a.status === status)
    return HttpResponse.json({ activations, total: activations.length })
  }),

  http.get('/api/v1/activations/:activationId/performance', ({ params }) => {
    const metrics = db.performanceStore?.[params.activationId as string] ?? []
    return HttpResponse.json({ activation_id: params.activationId, metrics, total: metrics.length })
  }),

  // ── Creatives resource (PRD Section 10) ────────────────────────────────────

  http.get('/api/v1/creatives', ({ request }) => {
    const url = new URL(request.url)
    const campaignId = url.searchParams.get('campaign_id')
    const activationId = url.searchParams.get('activation_id')
    let creatives = Object.values(db.creativesStore ?? {})
    if (campaignId) creatives = creatives.filter((c: any) => c.campaign_id === campaignId)
    if (activationId) creatives = creatives.filter((c: any) => c.activation_id === activationId)
    return HttpResponse.json({ creatives, total: creatives.length })
  }),

  http.patch('/api/v1/creatives/:id/status', async ({ params, request }) => {
    const body = (await request.json()) as { status: string; notes?: string }
    const id = params.id as string
    const existing = db.creativesStore[id]
    if (!existing) return new HttpResponse(null, { status: 404 })
    db.creativesStore[id] = { ...existing, status: body.status, notes: body.notes ?? existing.notes }
    return HttpResponse.json(db.creativesStore[id])
  }),

  http.post('/api/v1/creatives/:creativeId/internal-approve', ({ params }) => {
    return HttpResponse.json({ id: params.creativeId, validation_status: 'internal_approved' })
  }),

  http.post('/api/v1/creatives/:creativeId/client-approve', ({ params }) => {
    return HttpResponse.json({ id: params.creativeId, validation_status: 'client_approved' })
  }),

  http.post('/api/v1/creatives/:creativeId/request-revision', async ({ params, request }) => {
    const body = (await request.json()) as { comment: string }
    return HttpResponse.json({
      id: params.creativeId,
      validation_status: 'revision_requested',
      refinement_attempts: 1,
      comment: body.comment,
    })
  }),

  http.get('/api/v1/creatives/:creativeId/download', ({ params }) => {
    return HttpResponse.json({
      id: params.creativeId,
      asset_url: 'https://placehold.co/1024x1024/1a1a2e/ffffff?text=Creative+Asset',
      creative_type: 'social_post',
      platform: 'instagram',
    })
  }),

  // ── Campaign deck (PRD Section 10) ─────────────────────────────────────────

  http.get('/api/v1/campaigns/:campaignId/deck', ({ params }) => {
    return HttpResponse.json({
      campaign_id: params.campaignId,
      deck_url: null,
      sections: {
        executive_summary: 'Bold campaign strategy for market expansion',
        campaign_name_options: ['Rise Together', 'Forward India', 'The Next Chapter'],
        tagline_options: ['Where ambition meets scale', 'Built for tomorrow'],
        narrative: 'A story of growth, trust, and bold market moves.',
        channel_mix: { digital: 60, ooh: 20, print: 15, radio: 5 },
        tone_board: ['Bold', 'Aspirational', 'Authentic', 'Modern'],
      },
    })
  }),

  // ── Analytics mandate-scoped (PRD Section 10) ──────────────────────────────

  http.get('/api/v1/analytics/dashboard', ({ request }) => {
    const mandateId = new URL(request.url).searchParams.get('mandate_id')
    return HttpResponse.json({ mandate_id: mandateId, summary: {} })
  }),

  http.get('/api/v1/analytics/channel-performance', ({ request }) => {
    const mandateId = new URL(request.url).searchParams.get('mandate_id')
    return HttpResponse.json({
      mandate_id: mandateId,
      channels: { google_ads: { total: 2, green: 1, amber: 1, red: 0 }, meta_ads: { total: 1, green: 1, amber: 0, red: 0 } },
    })
  }),

  http.get('/api/v1/analytics/kpi-status', ({ request }) => {
    const mandateId = new URL(request.url).searchParams.get('mandate_id')
    return HttpResponse.json({ mandate_id: mandateId, kpis: [], summary: { total: 0, red: 0, amber: 0, green: 0 } })
  }),

  http.get('/api/v1/analytics/report', ({ request }) => {
    const mandateId = new URL(request.url).searchParams.get('mandate_id')
    return HttpResponse.json({ mandate_id: mandateId, report_type: 'weekly', report_json: {} }, { status: 200 })
  }),

  http.post('/api/v1/analytics/replan/approve/:recommendationId', ({ params }) => {
    return HttpResponse.json({ recommendation_id: params.recommendationId, status: 'approved' })
  }),
]
