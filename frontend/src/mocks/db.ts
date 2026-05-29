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
  { id: 'a1',  created_at: '2026-05-14T08:00:00Z', actor_id: 'admin@ntm.com', action: 'CREATE',      entity_type: 'tenant', entity_id: 't1', tenant_id: 't1', notes: 'Created tenant Acme Corp',               status_before: null, status_after: 'active' },
  { id: 'a2',  created_at: '2026-05-14T08:05:00Z', actor_id: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u1', tenant_id: 't1', notes: 'Created user alice@acme.com',             status_before: null, status_after: 'active' },
  { id: 'a3',  created_at: '2026-05-14T08:10:00Z', actor_id: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u2', tenant_id: 't1', notes: 'Created user bob@acme.com',               status_before: null, status_after: 'active' },
  { id: 'a4',  created_at: '2026-05-14T09:00:00Z', actor_id: 'admin@ntm.com', action: 'CREATE',      entity_type: 'tenant', entity_id: 't2', tenant_id: 't2', notes: 'Created tenant BrandCo',                  status_before: null, status_after: 'active' },
  { id: 'a5',  created_at: '2026-05-14T09:05:00Z', actor_id: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u3', tenant_id: 't2', notes: 'Created user carol@brandco.com',          status_before: null, status_after: 'active' },
  { id: 'a6',  created_at: '2026-05-14T09:10:00Z', actor_id: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u4', tenant_id: 't2', notes: 'Created user dave@brandco.com',           status_before: null, status_after: 'active' },
  { id: 'a7',  created_at: '2026-05-14T10:00:00Z', actor_id: 'admin@ntm.com', action: 'DEACTIVATE',  entity_type: 'user',   entity_id: 'u4', tenant_id: 't2', notes: 'Deactivated user dave@brandco.com',       status_before: 'active', status_after: 'inactive' },
  { id: 'a8',  created_at: '2026-05-14T10:30:00Z', actor_id: 'admin@ntm.com', action: 'CREATE',      entity_type: 'tenant', entity_id: 't3', tenant_id: 't3', notes: 'Created tenant MediaGroup',               status_before: null, status_after: 'active' },
  { id: 'a9',  created_at: '2026-05-14T10:35:00Z', actor_id: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u5', tenant_id: 't3', notes: 'Created user eve@mediagroup.com',         status_before: null, status_after: 'active' },
  { id: 'a10', created_at: '2026-05-14T11:00:00Z', actor_id: 'admin@ntm.com', action: 'DEACTIVATE',  entity_type: 'tenant', entity_id: 't3', tenant_id: 't3', notes: 'Deactivated tenant MediaGroup',           status_before: 'active', status_after: 'inactive' },
  { id: 'a11', created_at: '2026-05-14T11:30:00Z', actor_id: 'super@ntm.com', action: 'ROLE_CHANGE', entity_type: 'user',   entity_id: 'u2', tenant_id: 't1', notes: 'Changed role to brand_manager',           status_before: 'viewer', status_after: 'brand_manager' },
  { id: 'a12', created_at: '2026-05-14T12:00:00Z', actor_id: 'super@ntm.com', action: 'LOGIN',       entity_type: 'user',   entity_id: 'u1', tenant_id: 't1', notes: 'User login from 192.168.1.1',             status_before: null, status_after: null },
  { id: 'a13', created_at: '2026-05-14T12:30:00Z', actor_id: 'admin@ntm.com', action: 'UPDATE',      entity_type: 'tenant', entity_id: 't1', tenant_id: 't1', notes: 'Updated tenant settings',                 status_before: null, status_after: null },
  { id: 'a14', created_at: '2026-05-14T13:00:00Z', actor_id: 'admin@ntm.com', action: 'CREATE',      entity_type: 'user',   entity_id: 'u6', tenant_id: 't1', notes: 'Created user frank@acme.com',             status_before: null, status_after: 'active' },
  { id: 'a15', created_at: '2026-05-14T13:30:00Z', actor_id: 'super@ntm.com', action: 'ACTIVATE',    entity_type: 'user',   entity_id: 'u4', tenant_id: 't2', notes: 'Activated user dave@brandco.com',         status_before: 'inactive', status_after: 'active' },
  { id: 'a16', created_at: '2026-05-14T14:00:00Z', actor_id: 'admin@ntm.com', action: 'DEACTIVATE',  entity_type: 'user',   entity_id: 'u6', tenant_id: 't1', notes: 'Deactivated user frank@acme.com',         status_before: 'active', status_after: 'inactive' },
  { id: 'a17', created_at: '2026-05-14T14:30:00Z', actor_id: 'super@ntm.com', action: 'LOGIN',       entity_type: 'user',   entity_id: 'u3', tenant_id: 't2', notes: 'User login from 10.0.0.5',               status_before: null, status_after: null },
  { id: 'a18', created_at: '2026-05-14T15:00:00Z', actor_id: 'admin@ntm.com', action: 'ACTIVATE',    entity_type: 'tenant', entity_id: 't3', tenant_id: 't3', notes: 'Reactivated tenant MediaGroup',           status_before: 'inactive', status_after: 'active' },
  { id: 'a19', created_at: '2026-05-14T15:30:00Z', actor_id: 'super@ntm.com', action: 'UPDATE',      entity_type: 'user',   entity_id: 'u5', tenant_id: 't3', notes: 'Updated user profile',                   status_before: null, status_after: null },
  { id: 'a20', created_at: '2026-05-14T16:00:00Z', actor_id: 'admin@ntm.com', action: 'CREATE',      entity_type: 'tenant', entity_id: 't4', tenant_id: 't4', notes: 'Created tenant GlobalBrands',             status_before: null, status_after: 'active' },
]
