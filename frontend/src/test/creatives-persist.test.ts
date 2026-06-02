import { describe, it, expect } from 'vitest'
import { flattenCreativeAssets, creativesStore, generateCreativeAssets } from '@/mocks/db/campaigns'

describe('flattenCreativeAssets', () => {
  const assets = generateCreativeAssets('test-cam')
  const flat = flattenCreativeAssets('test-cam', assets)

  it('returns a flat array (one entry per sub-asset)', () => {
    const expected = assets.images.length + assets.copy.length + assets.scripts.length + assets.audio.length
    expect(flat.length).toBe(expected)
  })

  it('every item has campaign_id, creative_type, platform, content, validation_status', () => {
    for (const c of flat) {
      expect(c.campaign_id).toBe('test-cam')
      expect(typeof c.creative_type).toBe('string')
      expect(typeof c.platform).toBe('string')
      expect(c.content).toBeTruthy()
      expect(c.validation_status).toBe('ai_draft')
    }
  })

  it('image items have content.url', () => {
    const images = flat.filter((c) => c.creative_type === 'image')
    expect(images.length).toBeGreaterThan(0)
    for (const img of images) {
      expect((img.content as Record<string, unknown>).url).toBeTruthy()
    }
  })

  it('copy items have content.preview', () => {
    const copies = flat.filter((c) => c.creative_type === 'copy')
    expect(copies.length).toBeGreaterThan(0)
    for (const cp of copies) {
      expect(typeof (cp.content as Record<string, unknown>).preview).toBe('string')
    }
  })

  it('script items have content.content_preview and content.duration_estimate', () => {
    const scripts = flat.filter((c) => c.creative_type === 'script')
    expect(scripts.length).toBeGreaterThan(0)
    for (const sc of scripts) {
      const cnt = sc.content as Record<string, unknown>
      expect(typeof cnt.content_preview).toBe('string')
      expect(typeof cnt.duration_estimate).toBe('string')
    }
  })

  it('audio items have content.url and content.duration_seconds', () => {
    const audios = flat.filter((c) => c.creative_type === 'audio')
    expect(audios.length).toBeGreaterThan(0)
    for (const au of audios) {
      const cnt = au.content as Record<string, unknown>
      expect(typeof cnt.url).toBe('string')
      expect(typeof cnt.duration_seconds).toBe('number')
    }
  })

  it('ids are unique across different campaigns (no id collision)', () => {
    // Generate assets independently per campaign so script/audio ids use the right prefix
    const flatA = flattenCreativeAssets('cam-A', generateCreativeAssets('cam-A'))
    const flatB = flattenCreativeAssets('cam-B', generateCreativeAssets('cam-B'))
    const idsA = new Set(flatA.map((c) => c.id as string))
    const idsB = new Set(flatB.map((c) => c.id as string))
    for (const id of idsB) {
      expect(idsA.has(id)).toBe(false)
    }
  })
})

describe('creativesStore seeded from initialCampaigns', () => {
  it('contains creatives for c-003 (seeded campaign with creative_assets)', () => {
    const c003Items = Object.values(creativesStore).filter(
      (c) => (c as Record<string, unknown>).campaign_id === 'c-003'
    )
    expect(c003Items.length).toBeGreaterThan(0)
  })

  it('contains creatives for c-004 (seeded campaign with creative_assets)', () => {
    const c004Items = Object.values(creativesStore).filter(
      (c) => (c as Record<string, unknown>).campaign_id === 'c-004'
    )
    expect(c004Items.length).toBeGreaterThan(0)
  })
})
