import { http, HttpResponse } from 'msw'
import { users } from '../db'

const STORAGE_KEY = 'ntm:registered_emails'

// Seed user emails — always treated as already registered
const SEED_EMAILS = new Set(users.map((u) => u.email.toLowerCase()))

/** Read persisted registrations from localStorage (survives page reload). */
function isRegistered(email: string): boolean {
  if (SEED_EMAILS.has(email)) return true
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as string[]
    return stored.includes(email)
  } catch {
    return false
  }
}

/** Persist a newly registered email to localStorage. */
function saveRegistered(email: string): void {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as string[]
    if (!stored.includes(email)) {
      stored.push(email)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stored))
    }
  } catch {
    // localStorage unavailable — skip persistence
  }
}

export const authHandlers = [
  // Login — always succeeds, always returns admin role
  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    return HttpResponse.json({
      token: 'mock-jwt-token',
      user: {
        id: `user-${body.email}`,
        email: body.email,
        role: 'admin',
      },
    })
  }),

  // Register — checks localStorage + seed emails for duplicates
  http.post('/api/v1/auth/register', async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    const email = body.email.toLowerCase().trim()

    if (isRegistered(email)) {
      return HttpResponse.json(
        { detail: 'User already exists' },
        { status: 409 },
      )
    }

    saveRegistered(email)

    return HttpResponse.json({
      token: 'mock-jwt-token',
      user: {
        id: `user-${email}`,
        email: body.email,
        role: 'admin',
      },
    })
  }),
]
