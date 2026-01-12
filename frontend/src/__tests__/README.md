# Frontend Tests

This directory contains tests for the frontend React components.

## Test Setup

Tests use:
- **Vitest** - Fast test runner
- **React Testing Library** - Component testing utilities
- **@testing-library/jest-dom** - DOM matchers

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

## Test Structure

```
src/__tests__/
├── setup.ts                    # Test configuration
└── components/
    └── pm/                     # PM component tests
        ├── PRDChangeCard.test.tsx
        ├── PRDChangesView.test.tsx
        ├── BulkAcceptPanel.test.tsx
        ├── PRDQualityScore.test.tsx
        ├── EffortEstimation.test.tsx
        └── ExpertAskModal.test.tsx
```

## Test Coverage

### PM Components
- ✅ PRDChangeCard - Rendering, interactions, edit mode
- ✅ PRDChangesView - Data fetching, mutations, actions
- ✅ BulkAcceptPanel - Selection, filters, bulk accept
- ✅ PRDQualityScore - Score display, stats, gaps
- ✅ EffortEstimation - Time range, codebase support, sprints
- ✅ ExpertAskModal - Expert selection, question editing, send

## Writing Tests

### Test Template

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { YourComponent } from '../../../components/YourComponent'

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('YourComponent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders correctly', () => {
    render(
      <TestWrapper>
        <YourComponent />
      </TestWrapper>
    )
    
    expect(screen.getByText('Expected Text')).toBeInTheDocument()
  })
})
```

## Mocking

### API Service

```tsx
vi.mock('../../../services/api', () => ({
  api: {
    getData: vi.fn(),
    postData: vi.fn(),
  },
}))
```

### React Query

Always wrap components that use React Query in `QueryClientProvider`:

```tsx
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
```

## Best Practices

1. **Test user interactions**, not implementation details
2. **Use accessible queries** (`getByRole`, `getByLabelText`)
3. **Mock external dependencies** (API, services)
4. **Test loading and error states**
5. **Test edge cases** (empty data, long text, etc.)
6. **Keep tests focused** - one assertion per test when possible

## Coverage Goals

- Component rendering: 100%
- User interactions: 90%+
- Edge cases: 80%+
- Integration flows: 70%+
