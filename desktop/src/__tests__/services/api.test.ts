/**
 * API Service Tests
 * 
 * These tests verify that the API service correctly communicates with the backend.
 * All API endpoints must work for the app to function properly.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReviewRequest, Review, ReviewStatus, DashboardData, ParsedIntent } from '../../types'

// Helper to create mock Response
const createMockResponse = (data: unknown, ok = true, status = 200): Response => ({
  ok,
  status,
  statusText: ok ? 'OK' : 'Error',
  headers: new Headers(),
  redirected: false,
  type: 'basic',
  url: '',
  clone: () => createMockResponse(data, ok, status),
  body: null,
  bodyUsed: false,
  arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
  blob: () => Promise.resolve(new Blob()),
  formData: () => Promise.resolve(new FormData()),
  json: () => Promise.resolve(data),
  text: () => Promise.resolve(typeof data === 'string' ? data : JSON.stringify(data)),
})

// Import api - it will use the globally mocked fetch from setup.ts
import { api } from '../../services/api'

describe('API Service', () => {
  beforeEach(() => {
    // Reset fetch mock before each test
    vi.mocked(global.fetch).mockReset()
    
    // Ensure electronAPI is set up
    window.electronAPI = {
      ...window.electronAPI,
      getBackendUrl: vi.fn().mockResolvedValue('http://127.0.0.1:8000'),
    }
  })

  describe('listReviews', () => {
    it('should fetch and return list of reviews', async () => {
      const mockReviews: Review[] = [
        {
          review_id: 'review-1',
          title: 'Test Review',
          status: 'completed',
          risk_rating: 'MEDIUM',
          findings_count: 5,
          dimensions: ['security'],
          security_findings: 5,
          privacy_findings: 0,
          compliance_findings: 0,
          engineering_findings: 0,
          architecture_findings: 0,
          reviewed_at: '2024-01-01T00:00:00Z',
        },
      ]

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(mockReviews))

      const result = await api.listReviews()
      expect(result).toEqual(mockReviews)
      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/reviews',
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' },
        })
      )
    })

    it('should throw error on non-ok response', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(
        createMockResponse('Internal Server Error', false, 500)
      )

      await expect(api.listReviews()).rejects.toThrow('Internal Server Error')
    })
  })

  describe('createReview', () => {
    it('should create a new review with correct payload', async () => {
      const request: ReviewRequest = {
        prd: {
          content: '# Test PRD\n\nThis is a test PRD.',
          source_type: 'markdown',
          title: 'Test Feature',
        },
        codebase: {
          path: '/path/to/codebase',
          languages: ['python', 'typescript'],
        },
        config: {
          use_llm: true,
          dimensions: ['security', 'privacy'],
          compliance_frameworks: ['soc2'],
        },
      }

      const mockResponse = {
        review_id: 'new-review-id',
        status: 'pending',
        message: 'Review started',
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(mockResponse))

      const result = await api.createReview(request)

      expect(result).toEqual(mockResponse)
      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/reviews',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(request),
        })
      )
    })

    it('should include API keys when provided', async () => {
      const request: ReviewRequest = {
        prd: {
          content: 'Test',
          source_type: 'markdown',
        },
        codebase: {
          path: '/path',
          languages: ['python'],
        },
        config: {
          use_llm: true,
          dimensions: ['security'],
          compliance_frameworks: [],
          openai_api_key: 'sk-test',
          anthropic_api_key: 'sk-ant-test',
        },
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse({ review_id: 'test' }))

      await api.createReview(request)

      const callArgs = vi.mocked(global.fetch).mock.calls[0]
      const callBody = JSON.parse(callArgs[1]?.body as string)
      expect(callBody.config.openai_api_key).toBe('sk-test')
      expect(callBody.config.anthropic_api_key).toBe('sk-ant-test')
    })
  })

  describe('getReviewStatus', () => {
    it('should fetch review status by ID', async () => {
      const mockStatus: ReviewStatus = {
        review_id: 'test-review',
        status: 'running',
        progress: 0.5,
        message: 'Analyzing codebase...',
        dimensions: ['security'],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(mockStatus))

      const result = await api.getReviewStatus('test-review')

      expect(result).toEqual(mockStatus)
      expect(global.fetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/reviews/test-review/status',
        expect.any(Object)
      )
    })

    it('should handle all status types', async () => {
      const statuses: ReviewStatus['status'][] = ['pending', 'running', 'completed', 'failed']

      for (const status of statuses) {
        vi.mocked(global.fetch).mockResolvedValueOnce(
          createMockResponse({
            review_id: 'test',
            status,
            progress: status === 'completed' ? 1 : 0.5,
            message: `Status: ${status}`,
          })
        )

        const result = await api.getReviewStatus('test')
        expect(result.status).toBe(status)
      }
    })
  })

  describe('getReviewDashboard', () => {
    it('should fetch complete dashboard data', async () => {
      const mockDashboard: DashboardData = {
        overview: {
          title: 'Test Review',
          risk_rating: 'MEDIUM',
          total_findings: 10,
          critical_count: 1,
          high_count: 3,
          reviewed_at: '2024-01-01T00:00:00Z',
          dimensions_analyzed: ['security', 'privacy'],
        },
        severity_chart: {
          labels: ['Critical', 'High', 'Medium', 'Low'],
          data: [1, 3, 4, 2],
          colors: ['#ef4444', '#ff7d11', '#eab308', '#22c55e'],
        },
        category_chart: {
          labels: ['Auth', 'Injection', 'XSS'],
          data: [3, 5, 2],
        },
        risk_gauge: { value: 65 },
        findings_table: [
          {
            id: 'finding-1',
            severity: 'critical',
            title: 'SQL Injection',
            description: 'Possible SQL injection vulnerability',
            category: 'injection',
            dimension: 'security',
            confidence: 'high',
            recommendation: 'Use parameterized queries',
            source_type: 'llm',
          },
        ],
        delta_summary: {
          cards: [
            { label: 'New Endpoints', value: 5, icon: 'api' },
            { label: 'Modified Files', value: 12, icon: 'file' },
          ],
          flags: {
            introduces_pii: true,
            modifies_auth: false,
            expands_attack_surface: true,
          },
        },
        llm_analysis: {
          used: true,
          providers: ['openai', 'anthropic'],
          findings_count: 8,
          consensus_count: 5,
          total_tokens: 15000,
          latency_ms: 3500,
        },
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(mockDashboard))

      const result = await api.getReviewDashboard('test-review')

      expect(result).toEqual(mockDashboard)
      expect(result.overview).toBeDefined()
      expect(result.findings_table).toBeDefined()
      expect(result.risk_gauge).toBeDefined()
    })

    it('should handle dashboard with all dimensions', async () => {
      const dimensions = ['security', 'privacy', 'compliance', 'engineering', 'architecture']

      vi.mocked(global.fetch).mockResolvedValueOnce(
        createMockResponse({
          overview: {
            title: 'Multi-dimension Review',
            risk_rating: 'HIGH',
            total_findings: 25,
            critical_count: 3,
            high_count: 8,
            reviewed_at: new Date().toISOString(),
            dimensions_analyzed: dimensions,
            dimension_counts: {
              security: 5,
              privacy: 5,
              compliance: 5,
              engineering: 5,
              architecture: 5,
            },
          },
          severity_chart: { labels: [], data: [], colors: [] },
          category_chart: { labels: [], data: [] },
          risk_gauge: { value: 75 },
          findings_table: [],
          delta_summary: {
            cards: [],
            flags: {
              introduces_pii: false,
              modifies_auth: false,
              expands_attack_surface: false,
            },
          },
        })
      )

      const result = await api.getReviewDashboard('test')

      expect(result.overview.dimensions_analyzed).toEqual(dimensions)
      expect(result.overview.dimension_counts).toBeDefined()
    })
  })

  describe('getReviewMarkdown', () => {
    it('should fetch markdown export', async () => {
      const mockMarkdown = {
        markdown: '# Security Review Report\n\n## Overview\n...',
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(mockMarkdown))

      const result = await api.getReviewMarkdown('test-review')

      expect(result.markdown).toContain('# Security Review Report')
    })
  })

  describe('parsePRD', () => {
    it('should parse PRD content and extract intent', async () => {
      const mockIntent: ParsedIntent = {
        title: 'User Authentication Feature',
        summary: 'Implementing OAuth2-based authentication',
        features: ['OAuth2 login', 'Session management', 'MFA support'],
        user_stories: ['As a user, I want to log in securely'],
        data_entities: [
          { name: 'User', type: 'model', is_sensitive: true },
          { name: 'Session', type: 'model', is_sensitive: true },
        ],
        api_changes: ['POST /api/auth/login', 'POST /api/auth/logout'],
        auth_requirements: ['JWT tokens', 'Refresh tokens'],
        external_integrations: ['OAuth provider'],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(mockIntent))

      const result = await api.parsePRD('# Auth Feature\n...', 'Auth Feature')

      expect(result).toEqual(mockIntent)
      expect(result.data_entities.filter((e) => e.is_sensitive).length).toBeGreaterThan(0)
    })
  })

  describe('analyzeCodebase', () => {
    it('should analyze codebase and return analysis results', async () => {
      const mockAnalysis = {
        path: '/path/to/codebase',
        files_analyzed: 150,
        lines_of_code: 25000,
        api_endpoints: [{ method: 'GET', path: '/api/users' }],
        data_models: [{ name: 'User', fields: ['id', 'email'] }],
        auth_patterns: ['JWT', 'OAuth2'],
        existing_controls: ['CSRF protection', 'Rate limiting'],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(mockAnalysis))

      const result = await api.analyzeCodebase('/path/to/codebase', ['python', 'typescript'])

      expect(result.files_analyzed).toBe(150)
      expect(result.existing_controls).toContain('CSRF protection')
    })
  })
})

describe('API Error Handling', () => {
  beforeEach(() => {
    vi.mocked(global.fetch).mockReset()
  })

  it('should handle network errors gracefully', async () => {
    vi.mocked(global.fetch).mockRejectedValueOnce(new Error('Network error'))

    await expect(api.listReviews()).rejects.toThrow('Network error')
  })

  it('should handle 404 errors', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      createMockResponse('Review not found', false, 404)
    )

    await expect(api.getReviewStatus('nonexistent')).rejects.toThrow('Review not found')
  })

  it('should handle 401 unauthorized', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      createMockResponse('Unauthorized', false, 401)
    )

    await expect(api.listReviews()).rejects.toThrow('Unauthorized')
  })

  it('should handle empty error responses', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      createMockResponse('', false, 500)
    )

    await expect(api.listReviews()).rejects.toThrow('HTTP 500')
  })
})
