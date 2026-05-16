import { http, HttpResponse } from 'msw'
import * as db from '../db/campaigns'
import type { Campaign } from '@/types/admin'

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
    const mandate = db.mandates.find((m) => m.id === mandate_id)
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
      budget_proposal: db.generateBudgetProposal(campaign.activation_plan),
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

  http.get('/api/v1/mandates', ({ request }) => {
    const tenantId = new URL(request.url).searchParams.get('tenant_id')
    const results = tenantId
      ? db.mandates.filter((m) => m.tenant_id === tenantId)
      : db.mandates
    return HttpResponse.json(results)
  }),

  http.post('/api/v1/campaigns/:id/generate-creatives', ({ params }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign) return new HttpResponse(null, { status: 404 })
    db.campaignStore[campaign.id] = {
      ...campaign,
      status: 'creative_ready',
      creative_assets: db.generateCreativeAssets(campaign.id),
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(db.campaignStore[campaign.id])
  }),

  http.patch('/api/v1/campaigns/:id/creatives/:assetKind/:assetId', async ({ params, request }) => {
    const campaign = db.campaignStore[params.id as string]
    if (!campaign?.creative_assets) return new HttpResponse(null, { status: 404 })
    const { approved } = (await request.json()) as { approved: boolean }
    const { assetKind, assetId } = params as { assetKind: string; assetId: string }
    let assets = campaign.creative_assets
    if (assetKind === 'copy') {
      assets = { ...assets, copy: assets.copy.map((a) => a.asset_type === assetId ? { ...a, approved } : a) }
    } else if (assetKind === 'scripts') {
      assets = { ...assets, scripts: assets.scripts.map((s) => s.id === assetId ? { ...s, approved } : s) }
    } else if (assetKind === 'images') {
      assets = { ...assets, images: assets.images.map((i) => i.id === assetId ? { ...i, approved } : i) }
    } else if (assetKind === 'audio') {
      assets = { ...assets, audio: assets.audio.map((a) => a.id === assetId ? { ...a, approved } : a) }
    }
    db.campaignStore[campaign.id] = { ...campaign, creative_assets: assets, updated_at: new Date().toISOString() }
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
      const IMAGE_SIZES: Record<string, string> = {
        square: '1024x1024/1a1a2e/ffffff?text=Square+Ad',
        landscape: '1344x768/16213e/ffffff?text=Landscape+Ad',
        portrait: '768x1344/0f3460/ffffff?text=Portrait+Ad',
      }
      assets = {
        ...assets,
        images: assets.images.map((img) =>
          img.id === assetId
            ? { ...img, url: `https://placehold.co/${IMAGE_SIZES[img.format]}&t=${Date.now()}`, approved: null }
            : img
        ),
      }
    } else if (assetKind === 'audio') {
      const AUDIO_POOL = [
        'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
        'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
        'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
      ]
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
]
