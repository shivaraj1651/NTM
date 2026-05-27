import { http, HttpResponse } from 'msw'
import { users } from '../db'

// Runtime registry — starts with seed user emails, grows as new accounts are registered
const registeredEmails = new Set<string>(users.map((u) => u.email))

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

  // Register — checks for duplicate email, creates user on success
  http.post('/api/v1/auth/register', async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    const email = body.email.toLowerCase().trim()

    if (registeredEmails.has(email)) {
      return HttpResponse.json(
        { detail: 'User already exists' },
        { status: 409 },
      )
    }

    // Persist for this session
    registeredEmails.add(email)

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
