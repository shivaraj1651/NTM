import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from './utils'
import { LoginPage } from '@/pages/Login/LoginPage'

describe('LoginPage', () => {
  it('renders without crashing', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    expect(document.body).toBeInTheDocument()
  })

  it('shows email input', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const emailInput =
      screen.queryByRole('textbox', { name: /email/i }) ??
      screen.queryByPlaceholderText(/email/i) ??
      document.querySelector('input[type="email"]')
    expect(emailInput).toBeTruthy()
  })

  it('shows password input', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const passwordInput = document.querySelector('input[type="password"]')
    expect(passwordInput).toBeTruthy()
  })

  it('shows submit button', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const btn =
      screen.queryByRole('button', { name: /sign in|log in|login|submit/i }) ??
      document.querySelector('button[type="submit"]')
    expect(btn).toBeTruthy()
  })
})
