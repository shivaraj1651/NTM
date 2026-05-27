import type { Tenant, User, AuditEntry } from '@/types/admin'

// ── localStorage-persisted store ─────────────────────────────────────────────
// Same pattern as db/mandates.ts and db/campaigns.ts — Proxy traps top-level
// property assignments and flushes the whole store to localStorage.

function createPersistedStore<V>(
  storageKey: string,
  seed: Record<string, V>,
): Record<string, V> {
  let initial: Record<string, V>
  try {
    const raw = localStorage.getItem(storageKey)
    // Merge: seed provides defaults; stored data overrides (keeps user changes)
    initial = raw ? { ...seed, ...(JSON.parse(raw) as Record<string, V>) } : { ...seed }
  } catch {
    initial = { ...seed }
  }

  const persist = (target: Record<string, V>) => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(target))
    } catch {}
  }

  return new Proxy(initial, {
    set(target, prop, value) {
      const ok = Reflect.set(target, prop, value)
      persist(target)
      return ok
    },
    deleteProperty(target, prop) {
      const ok = Reflect.deleteProperty(target, prop)
      persist(target)
      return ok
    },
  })
}

// ── Seed data ─────────────────────────────────────────────────────────────────

const SEED_TENANTS: Record<string, Tenant> = {
  't1': { id: 't1', name: 'Acme Corp',    is_active: true,  created_at: '2026-01-10T09:00:00Z' },
  't2': { id: 't2', name: 'BrandCo',      is_active: true,  created_at: '2026-02-15T14:30:00Z' },
  't3': { id: 't3', name: 'MediaGroup',   is_active: false, created_at: '2026-03-01T11:00:00Z' },
}

const SEED_USERS: Record<string, User> = {
  'u1': { id: 'u1', email: 'alice@acme.com',      role: 'tenant_admin',    is_active: true,  tenant_id: 't1', created_at: '2026-01-11T09:00:00Z' },
  'u2': { id: 'u2', email: 'bob@acme.com',         role: 'brand_manager',   is_active: true,  tenant_id: 't1', created_at: '2026-01-12T10:00:00Z' },
  'u3': { id: 'u3', email: 'carol@brandco.com',    role: 'cmo',             is_active: true,  tenant_id: 't2', created_at: '2026-02-16T09:00:00Z' },
  'u4': { id: 'u4', email: 'dave@brandco.com',     role: 'campaign_manager',is_active: false, tenant_id: 't2', created_at: '2026-02-20T14:00:00Z' },
  'u5': { id: 'u5', email: 'eve@mediagroup.com',   role: 'viewer',          is_active: true,  tenant_id: 't3', created_at: '2026-03-02T11:00:00Z' },
}

// ── Persisted stores (survive page reload via localStorage) ───────────────────

export const tenantsStore = createPersistedStore<Tenant>('ntm:tenants', SEED_TENANTS)
export const usersStore   = createPersistedStore<User>('ntm:users', SEED_USERS)

// ── Backward-compat seed arrays (auth handler uses users.map() for SEED_EMAILS)
// These are read-only references to the original seed — do NOT mutate them.
export const users:   User[]   = Object.values(SEED_USERS)
export const tenants: Tenant[] = Object.values(SEED_TENANTS)

// ── Audit entries (append-only log, plain array acceptable) ───────────────────

export const auditEntries: AuditEntry[] = [
  { id: 'a1',  timestamp: '2026-05-14T08:00:00Z', actor: 'admin@ntm.com', action: 'CREATE',      entity_type: 'tenant', entity_id: 't1', detail: 'Created tenant Acme Corp' },
  { id: 'a2',  timestamp: '2026-05-14T08:05:00Z', actor: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u1', detail: 'Created user alice@acme.com' },
  { id: 'a3',  timestamp: '2026-05-14T08:10:00Z', actor: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u2', detail: 'Created user bob@acme.com' },
  { id: 'a4',  timestamp: '2026-05-14T09:00:00Z', actor: 'admin@ntm.com', action: 'CREATE',      entity_type: 'tenant', entity_id: 't2', detail: 'Created tenant BrandCo' },
  { id: 'a5',  timestamp: '2026-05-14T09:05:00Z', actor: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u3', detail: 'Created user carol@brandco.com' },
  { id: 'a6',  timestamp: '2026-05-14T09:10:00Z', actor: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u4', detail: 'Created user dave@brandco.com' },
  { id: 'a7',  timestamp: '2026-05-14T10:00:00Z', actor: 'admin@ntm.com', action: 'DEACTIVATE',  entity_type: 'user',   entity_id: 'u4', detail: 'Deactivated user dave@brandco.com' },
  { id: 'a8',  timestamp: '2026-05-14T10:30:00Z', actor: 'admin@ntm.com', action: 'CREATE',      entity_type: 'tenant', entity_id: 't3', detail: 'Created tenant MediaGroup' },
  { id: 'a9',  timestamp: '2026-05-14T10:35:00Z', actor: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u5', detail: 'Created user eve@mediagroup.com' },
  { id: 'a10', timestamp: '2026-05-14T11:00:00Z', actor: 'admin@ntm.com', action: 'DEACTIVATE',  entity_type: 'tenant', entity_id: 't3', detail: 'Deactivated tenant MediaGroup' },
  { id: 'a11', timestamp: '2026-05-14T11:30:00Z', actor: 'super@ntm.com', action: 'ROLE_CHANGE', entity_type: 'user',   entity_id: 'u2', detail: 'Changed role to brand_manager' },
  { id: 'a12', timestamp: '2026-05-14T12:00:00Z', actor: 'super@ntm.com', action: 'LOGIN',       entity_type: 'user',   entity_id: 'u1', detail: 'User login from 192.168.1.1' },
  { id: 'a13', timestamp: '2026-05-14T12:30:00Z', actor: 'admin@ntm.com', action: 'UPDATE',      entity_type: 'tenant', entity_id: 't1', detail: 'Updated tenant settings' },
  { id: 'a14', timestamp: '2026-05-14T13:00:00Z', actor: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u6', detail: 'Created user frank@acme.com' },
  { id: 'a15', timestamp: '2026-05-14T13:30:00Z', actor: 'super@ntm.com', action: 'ACTIVATE',    entity_type: 'user',   entity_id: 'u4', detail: 'Activated user dave@brandco.com' },
  { id: 'a16', timestamp: '2026-05-14T14:00:00Z', actor: 'admin@ntm.com', action: 'DEACTIVATE',  entity_type: 'user',   entity_id: 'u6', detail: 'Deactivated user frank@acme.com' },
  { id: 'a17', timestamp: '2026-05-14T14:30:00Z', actor: 'super@ntm.com', action: 'LOGIN',       entity_type: 'user',   entity_id: 'u3', detail: 'User login from 10.0.0.5' },
  { id: 'a18', timestamp: '2026-05-14T15:00:00Z', actor: 'admin@ntm.com', action: 'ACTIVATE',    entity_type: 'tenant', entity_id: 't3', detail: 'Reactivated tenant MediaGroup' },
  { id: 'a19', timestamp: '2026-05-14T15:30:00Z', actor: 'super@ntm.com', action: 'UPDATE',      entity_type: 'user',   entity_id: 'u5', detail: 'Updated user profile' },
  { id: 'a20', timestamp: '2026-05-14T16:00:00Z', actor: 'admin@ntm.com', action: 'CREATE',      entity_type: 'tenant', entity_id: 't4', detail: 'Created tenant GlobalBrands' },
]
