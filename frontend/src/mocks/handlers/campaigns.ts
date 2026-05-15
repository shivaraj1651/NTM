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
]
