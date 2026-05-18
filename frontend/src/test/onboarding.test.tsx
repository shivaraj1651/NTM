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

describe('OnboardingPage — CompetitorsStep in isolation', () => {
  it('shows error when Next is clicked with no competitors filled in', async () => {
    const { CompetitorsStep } = await import('@/pages/Onboarding/CompetitorsStep')
    renderWithProviders(
      <CompetitorsStep defaultValues={['']} onNext={() => {}} onBack={() => {}} />,
      { route: '/onboarding', path: '/onboarding' }
    )
    fireEvent.click(screen.getByRole('button', { name: /^next/i }))
    await waitFor(() =>
      expect(screen.getByText(/at least one competitor/i)).toBeInTheDocument()
    )
  })

  it('adds a new input when clicking Add another', async () => {
    const { CompetitorsStep } = await import('@/pages/Onboarding/CompetitorsStep')
    renderWithProviders(
      <CompetitorsStep defaultValues={['']} onNext={() => {}} onBack={() => {}} />,
      { route: '/onboarding', path: '/onboarding' }
    )
    fireEvent.click(screen.getByRole('button', { name: /add another/i }))
    await waitFor(() =>
      expect(screen.getAllByPlaceholderText(/competitor/i)).toHaveLength(2)
    )
  })
})

describe('OnboardingPage — ReviewStep in isolation', () => {
  it('shows all collected data', async () => {
    const { ReviewStep } = await import('@/pages/Onboarding/ReviewStep')
    renderWithProviders(
      <ReviewStep
        data={{
          org_name: 'Acme Corp',
          industry: 'Technology',
          logo: null,
          brand_guidelines: null,
          competitors: ['CompA', 'CompB'],
        }}
        onSubmit={() => {}}
        onBack={() => {}}
        isPending={false}
      />,
      { route: '/onboarding', path: '/onboarding' }
    )
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
    expect(screen.getByText('Technology')).toBeInTheDocument()
    expect(screen.getByText(/CompA, CompB/)).toBeInTheDocument()
  })
})
