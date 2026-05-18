import { describe, it, expect } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { OnboardingPage } from '@/pages/Onboarding/OnboardingPage'
import { renderWithProviders } from './utils'
import React from 'react'

describe('OnboardingPage — step 1 (OrgInfo)', () => {
  it('renders without crashing', () => {
    renderWithProviders(<OnboardingPage />, { route: '/onboarding', path: '/onboarding' })
    expect(document.body).toBeInTheDocument()
  })

  it('shows Organisation Info heading on first render', () => {
    renderWithProviders(<OnboardingPage />, { route: '/onboarding', path: '/onboarding' })
    expect(screen.getByText('Organisation Info')).toBeInTheDocument()
  })

  it('shows validation error when Next is clicked with empty org_name', async () => {
    renderWithProviders(<OnboardingPage />, { route: '/onboarding', path: '/onboarding' })
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    await waitFor(() =>
      expect(screen.getByText(/at least 2 characters/i)).toBeInTheDocument()
    )
  })

  it('shows step counter starting at 1', () => {
    renderWithProviders(<OnboardingPage />, { route: '/onboarding', path: '/onboarding' })
    expect(screen.getByText('1')).toBeInTheDocument()
  })
})

describe('OnboardingPage — LogoStep in isolation', () => {
  it('shows error when Next clicked without selecting a file', async () => {
    const { LogoStep } = await import('@/pages/Onboarding/LogoStep')
    renderWithProviders(
      <LogoStep onNext={() => {}} onBack={() => {}} />,
      { route: '/onboarding', path: '/onboarding' }
    )
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    await waitFor(() =>
      expect(screen.getByText(/logo is required/i)).toBeInTheDocument()
    )
  })
})

describe('OnboardingPage — BrandGuidelinesStep in isolation', () => {
  it('shows error when Next clicked without selecting a file', async () => {
    const { BrandGuidelinesStep } = await import('@/pages/Onboarding/BrandGuidelinesStep')
    renderWithProviders(
      <BrandGuidelinesStep onNext={() => {}} onBack={() => {}} />,
      { route: '/onboarding', path: '/onboarding' }
    )
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    await waitFor(() =>
      expect(screen.getByText(/brand guidelines pdf is required/i)).toBeInTheDocument()
    )
  })
})
