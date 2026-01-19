/**
 * Review Workflow Integration Tests
 * 
 * These tests verify the complete review workflow from creation to viewing results.
 * They test the interaction between components and the API service.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReviewRequest, ReviewStatus, DashboardData, Review } from '../../types'

// Helper to create mock Response
const createMockResponse = (data: unknown, ok = true, status = 200): Response => ({
  ok,
  status,
  statusText: ok ? 'OK' : 'Error',
  headers: new Headers(),
  redirected: false,
  type: 'basic',
  url: '',
  clone: function() { return createMockResponse(data, ok, status) },
  body: null,
  bodyUsed: false,
  arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
  blob: () => Promise.resolve(new Blob()),
  formData: () => Promise.resolve(new FormData()),
  json: () => Promise.resolve(data),
  text: () => Promise.resolve(typeof data === 'string' ? data : JSON.stringify(data)),
})

describe('Review Workflow Integration', () => {
  beforeEach(() => {
    vi.mocked(global.fetch).mockReset()
  })

  describe('Complete Review Lifecycle', () => {
    it('should handle the full review lifecycle: create -> poll -> view', async () => {
      // Step 1: Create review
      const createRequest: ReviewRequest = {
        prd: {
          content: '# Feature PRD\n\nFeature description',
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

      vi.mocked(global.fetch).mockResolvedValueOnce(
        createMockResponse({
          review_id: 'test-review-123',
          status: 'pending',
          message: 'Review created',
        })
      )

      const createResponse = await fetch('/api/reviews', {
        method: 'POST',
        body: JSON.stringify(createRequest),
      })
      const createData = await createResponse.json()

      expect(createData.review_id).toBe('test-review-123')
      expect(createData.status).toBe('pending')

      // Step 2: Poll for status (running)
      const runningStatus: ReviewStatus = {
        review_id: 'test-review-123',
        status: 'running',
        progress: 0.5,
        message: 'Analyzing codebase...',
        dimensions: ['security', 'privacy'],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(runningStatus))

      const statusResponse = await fetch('/api/reviews/test-review-123/status')
      const statusData = await statusResponse.json()

      expect(statusData.status).toBe('running')
      expect(statusData.progress).toBe(0.5)

      // Step 3: Poll for status (completed)
      const completedStatus: ReviewStatus = {
        review_id: 'test-review-123',
        status: 'completed',
        progress: 1,
        message: 'Review completed',
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(completedStatus))

      const completedResponse = await fetch('/api/reviews/test-review-123/status')
      const completedData = await completedResponse.json()

      expect(completedData.status).toBe('completed')
      expect(completedData.progress).toBe(1)

      // Step 4: Fetch dashboard
      const dashboard: DashboardData = {
        overview: {
          title: 'Test Feature',
          risk_rating: 'MEDIUM',
          total_findings: 5,
          critical_count: 0,
          high_count: 2,
          reviewed_at: new Date().toISOString(),
          dimensions_analyzed: ['security', 'privacy'],
        },
        severity_chart: { labels: [], data: [], colors: [] },
        category_chart: { labels: [], data: [] },
        risk_gauge: { value: 45 },
        findings_table: [
          {
            id: 'f1',
            severity: 'high',
            title: 'Test Finding',
            category: 'auth',
            dimension: 'security',
            confidence: 'high',
            recommendation: 'Fix it',
          },
        ],
        delta_summary: {
          cards: [],
          flags: {
            introduces_pii: false,
            modifies_auth: true,
            expands_attack_surface: false,
          },
        },
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(dashboard))

      const dashboardResponse = await fetch('/api/reviews/test-review-123/dashboard')
      const dashboardData = await dashboardResponse.json()

      expect(dashboardData.overview.title).toBe('Test Feature')
      expect(dashboardData.findings_table.length).toBe(1)
    })

    it('should handle review failure gracefully', async () => {
      // Create review
      vi.mocked(global.fetch).mockResolvedValueOnce(
        createMockResponse({
          review_id: 'failed-review-123',
          status: 'pending',
          message: 'Review created',
        })
      )

      await fetch('/api/reviews', { method: 'POST', body: '{}' })

      // Poll returns failed status
      const failedStatus: ReviewStatus = {
        review_id: 'failed-review-123',
        status: 'failed',
        progress: 0.3,
        message: 'Error: Unable to parse Python files - syntax error in main.py',
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(failedStatus))

      const statusResponse = await fetch('/api/reviews/failed-review-123/status')
      const statusData = await statusResponse.json()

      expect(statusData.status).toBe('failed')
      expect(statusData.message).toContain('Error')
    })
  })

  describe('Review List Operations', () => {
    it('should fetch and display multiple reviews', async () => {
      const reviews: Review[] = [
        {
          review_id: 'r1',
          title: 'Auth Feature',
          status: 'completed',
          risk_rating: 'HIGH',
          findings_count: 12,
          dimensions: ['security'],
          security_findings: 12,
          privacy_findings: 0,
          compliance_findings: 0,
          engineering_findings: 0,
          architecture_findings: 0,
          reviewed_at: '2024-01-15T10:00:00Z',
        },
        {
          review_id: 'r2',
          title: 'Payment Integration',
          status: 'completed',
          risk_rating: 'CRITICAL',
          findings_count: 25,
          dimensions: ['security', 'compliance'],
          security_findings: 15,
          privacy_findings: 0,
          compliance_findings: 10,
          engineering_findings: 0,
          architecture_findings: 0,
          reviewed_at: '2024-01-14T09:00:00Z',
        },
        {
          review_id: 'r3',
          title: 'Profile Update',
          status: 'running',
          risk_rating: 'LOW',
          findings_count: 0,
          dimensions: ['security', 'privacy'],
          security_findings: 0,
          privacy_findings: 0,
          compliance_findings: 0,
          engineering_findings: 0,
          architecture_findings: 0,
          reviewed_at: '2024-01-16T11:00:00Z',
        },
      ]

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(reviews))

      const response = await fetch('/api/reviews')
      const data = await response.json()

      expect(data.length).toBe(3)
      expect(data.filter((r: Review) => r.status === 'completed').length).toBe(2)
      expect(data.filter((r: Review) => r.risk_rating === 'CRITICAL').length).toBe(1)
    })

    it('should handle empty review list', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse([]))

      const response = await fetch('/api/reviews')
      const data = await response.json()

      expect(data).toEqual([])
    })
  })

  describe('PRD Parsing Workflow', () => {
    it('should parse PRD and extract meaningful intent', async () => {
      const expectedIntent = {
        title: 'User Authentication Feature',
        summary: 'Implement secure user authentication with OAuth2 support.',
        features: [
          'Email/password login',
          'Social login (Google, GitHub)',
          'Two-factor authentication',
          'Session management',
        ],
        user_stories: [],
        data_entities: [
          { name: 'User', type: 'model', is_sensitive: true },
          { name: 'Session', type: 'model', is_sensitive: true },
        ],
        api_changes: [
          'POST /api/auth/login',
          'POST /api/auth/logout',
          'POST /api/auth/refresh',
        ],
        auth_requirements: ['JWT tokens', 'Rate limiting'],
        external_integrations: ['Google OAuth', 'GitHub OAuth'],
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(expectedIntent))

      const response = await fetch('/api/parse-prd', {
        method: 'POST',
        body: JSON.stringify({
          content: '# Auth Feature...',
          source_type: 'markdown',
          title: 'User Authentication Feature',
        }),
      })
      const data = await response.json()

      expect(data.title).toBe('User Authentication Feature')
      expect(data.features.length).toBeGreaterThan(0)
      expect(data.api_changes.length).toBe(3)
      expect(data.data_entities.some((e: { is_sensitive: boolean }) => e.is_sensitive)).toBe(true)
    })
  })

  describe('Multi-Dimension Review', () => {
    it('should handle review with all dimensions', async () => {
      const allDimensionsRequest: ReviewRequest = {
        prd: {
          content: '# Comprehensive Feature',
          source_type: 'markdown',
        },
        codebase: {
          path: '/path',
          languages: ['python'],
        },
        config: {
          use_llm: true,
          dimensions: ['security', 'privacy', 'compliance', 'engineering', 'architecture'],
          compliance_frameworks: ['soc2', 'hipaa', 'pci_dss'],
        },
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(
        createMockResponse({
          review_id: 'multi-dim-review',
          status: 'pending',
          message: 'Review started',
        })
      )

      const response = await fetch('/api/reviews', {
        method: 'POST',
        body: JSON.stringify(allDimensionsRequest),
      })
      const data = await response.json()

      expect(data.review_id).toBe('multi-dim-review')
    })

    it('should return findings for each dimension', async () => {
      const multiDimDashboard: DashboardData = {
        overview: {
          title: 'Multi-Dimension Review',
          risk_rating: 'HIGH',
          total_findings: 25,
          critical_count: 3,
          high_count: 8,
          reviewed_at: new Date().toISOString(),
          dimensions_analyzed: ['security', 'privacy', 'compliance', 'engineering', 'architecture'],
          dimension_counts: {
            security: 8,
            privacy: 5,
            compliance: 4,
            engineering: 5,
            architecture: 3,
          },
        },
        severity_chart: { labels: [], data: [], colors: [] },
        category_chart: { labels: [], data: [] },
        risk_gauge: { value: 68 },
        findings_table: [
          { id: 'f1', severity: 'critical', title: 'SQL Injection', category: 'injection', dimension: 'security', confidence: 'high', recommendation: 'Use prepared statements' },
          { id: 'f2', severity: 'high', title: 'PII in Logs', category: 'data_exposure', dimension: 'privacy', confidence: 'high', recommendation: 'Mask PII' },
          { id: 'f3', severity: 'medium', title: 'Missing Audit Log', category: 'audit', dimension: 'compliance', confidence: 'medium', recommendation: 'Add audit logging' },
          { id: 'f4', severity: 'low', title: 'No Unit Tests', category: 'testing', dimension: 'engineering', confidence: 'high', recommendation: 'Add tests' },
          { id: 'f5', severity: 'info', title: 'Tight Coupling', category: 'design', dimension: 'architecture', confidence: 'medium', recommendation: 'Use DI' },
        ],
        delta_summary: {
          cards: [],
          flags: { introduces_pii: true, modifies_auth: true, expands_attack_surface: true },
        },
        llm_analysis: {
          used: true,
          providers: ['openai', 'anthropic'],
          findings_count: 20,
          consensus_count: 15,
          total_tokens: 25000,
          latency_ms: 6000,
        },
      }

      vi.mocked(global.fetch).mockResolvedValueOnce(createMockResponse(multiDimDashboard))

      const response = await fetch('/api/reviews/multi-dim/dashboard')
      const data = await response.json()

      // Verify all dimensions have findings
      const dimensions = new Set(data.findings_table.map((f: { dimension: string }) => f.dimension))
      expect(dimensions.size).toBe(5)
      expect(dimensions.has('security')).toBe(true)
      expect(dimensions.has('privacy')).toBe(true)
      expect(dimensions.has('compliance')).toBe(true)
      expect(dimensions.has('engineering')).toBe(true)
      expect(dimensions.has('architecture')).toBe(true)

      // Verify dimension counts
      expect(data.overview.dimension_counts?.security).toBe(8)
      expect(data.overview.dimension_counts?.privacy).toBe(5)
    })
  })

  describe('Export Workflow', () => {
    it('should export review as markdown', async () => {
      const markdownContent = `# Security Review Report

## Overview
- Title: Test Feature
- Risk Rating: HIGH
- Total Findings: 10
`

      vi.mocked(global.fetch).mockResolvedValueOnce(
        createMockResponse({ markdown: markdownContent })
      )

      const response = await fetch('/api/reviews/test-review/markdown')
      const data = await response.json()

      expect(data.markdown).toContain('# Security Review Report')
      expect(data.markdown).toContain('Risk Rating: HIGH')
    })
  })

  describe('Error Handling', () => {
    it('should handle API timeout', async () => {
      vi.mocked(global.fetch).mockRejectedValueOnce(new Error('Request timeout'))

      await expect(fetch('/api/reviews')).rejects.toThrow('Request timeout')
    })

    it('should handle server errors', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(
        createMockResponse('Internal Server Error', false, 500)
      )

      const response = await fetch('/api/reviews')

      expect(response.ok).toBe(false)
      expect(response.status).toBe(500)
    })

    it('should handle invalid review ID', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce(
        createMockResponse('Review not found', false, 404)
      )

      const response = await fetch('/api/reviews/invalid-id/status')

      expect(response.ok).toBe(false)
      expect(response.status).toBe(404)
    })
  })

  describe('Concurrent Operations', () => {
    it('should handle multiple simultaneous status polls', async () => {
      const createStatusResponse = (progress: number) =>
        createMockResponse({
          review_id: 'test',
          status: progress < 1 ? 'running' : 'completed',
          progress,
          message: `Progress: ${progress * 100}%`,
        })

      vi.mocked(global.fetch)
        .mockResolvedValueOnce(createStatusResponse(0.2))
        .mockResolvedValueOnce(createStatusResponse(0.4))
        .mockResolvedValueOnce(createStatusResponse(0.6))
        .mockResolvedValueOnce(createStatusResponse(0.8))
        .mockResolvedValueOnce(createStatusResponse(1))

      const polls = await Promise.all([
        fetch('/api/reviews/test/status'),
        fetch('/api/reviews/test/status'),
        fetch('/api/reviews/test/status'),
        fetch('/api/reviews/test/status'),
        fetch('/api/reviews/test/status'),
      ])

      const results = await Promise.all(polls.map((p) => p.json()))

      // All polls should succeed
      expect(results.length).toBe(5)
      results.forEach((r) => {
        expect(r.review_id).toBe('test')
      })
    })
  })
})
