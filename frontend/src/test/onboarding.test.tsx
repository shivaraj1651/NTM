import { describe, it, expect } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { OnboardingPage } from '@/pages/Onboarding/OnboardingPage'
import { renderWithProviders } from './utils'

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
