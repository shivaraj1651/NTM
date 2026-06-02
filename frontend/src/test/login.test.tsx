import { describe, it, expect } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
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

describe('LoginPage — register mode role preview', () => {
  it('shows no preview when email has no domain', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const registerLink = screen.getByRole('button', { name: /register/i })
    fireEvent.click(registerLink)

    const emailInput = document.querySelector('input[type="email"]')!
    fireEvent.change(emailInput, { target: { value: 'tenant' } })

    expect(screen.queryByText(/Role:/i)).toBeNull()
  })

  it('shows Tenant Admin + tenant name when email is tenant@acme.com', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const registerLink = screen.getByRole('button', { name: /register/i })
    fireEvent.click(registerLink)

    const emailInput = document.querySelector('input[type="email"]')!
    fireEvent.change(emailInput, { target: { value: 'tenant@acme.com' } })

    expect(screen.getByText(/Tenant Admin/i)).toBeInTheDocument()
    expect(screen.getByText(/acme/i)).toBeInTheDocument()
  })

  it('shows Platform Admin for admin@newco.com', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const registerLink = screen.getByRole('button', { name: /register/i })
    fireEvent.click(registerLink)

    const emailInput = document.querySelector('input[type="email"]')!
    fireEvent.change(emailInput, { target: { value: 'admin@newco.com' } })

    expect(screen.getByText(/Platform Admin/i)).toBeInTheDocument()
    expect(screen.getByText(/newco/i)).toBeInTheDocument()
  })

  it('defaults to Brand Manager for unknown prefix', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    const registerLink = screen.getByRole('button', { name: /register/i })
    fireEvent.click(registerLink)

    const emailInput = document.querySelector('input[type="email"]')!
    fireEvent.change(emailInput, { target: { value: 'randomuser@startup.io' } })

    expect(screen.getByText(/Brand Manager/i)).toBeInTheDocument()
    expect(screen.getByText(/startup/i)).toBeInTheDocument()
  })
})
