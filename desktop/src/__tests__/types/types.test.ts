/**
 * Type Validation Tests
 * 
 * These tests ensure that data structures conform to expected types.
 * They serve as a contract for the backend API responses.
 */

import { describe, it, expect } from 'vitest'
import type {
  Review,
  ReviewStatus,
  ParsedIntent,
  Finding,
  DashboardData,
  PRDInput,
  CodebaseInput,
  ReviewConfig,
  ReviewRequest,
  AppSettings,
} from '../../types'

describe('Type Contracts', () => {
  describe('Review type', () => {
    it('should accept valid review data', () => {
      const validReview: Review = {
        review_id: 'test-123',
        title: 'Test Review',
        status: 'completed',
        risk_rating: 'MEDIUM',
        findings_count: 10,
        dimensions: ['security', 'privacy'],
        security_findings: 5,
        privacy_findings: 3,
        compliance_findings: 2,
        engineering_findings: 0,
        architecture_findings: 0,
        reviewed_at: '2024-01-01T00:00:00Z',
      }

      expect(validReview.review_id).toBeTruthy()
      expect(validReview.status).toMatch(/^(pending|running|completed|failed)$/)
      expect(validReview.risk_rating).toMatch(/^(CRITICAL|HIGH|MEDIUM|LOW|MINIMAL)$/)
    })

    it('should enforce valid status values', () => {
      const statuses: Review['status'][] = ['pending', 'running', 'completed', 'failed']
      statuses.forEach((status) => {
        expect(['pending', 'running', 'completed', 'failed']).toContain(status)
      })
    })

    it('should enforce valid risk ratings', () => {
      const ratings: Review['risk_rating'][] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'MINIMAL']
      ratings.forEach((rating) => {
        expect(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'MINIMAL']).toContain(rating)
      })
    })
  })

  describe('ReviewStatus type', () => {
    it('should represent pending status', () => {
      const status: ReviewStatus = {
        review_id: 'test',
        status: 'pending',
        progress: 0,
        message: 'Waiting to start...',
      }

      expect(status.progress).toBe(0)
    })

    it('should represent running status with progress', () => {
      const status: ReviewStatus = {
        review_id: 'test',
        status: 'running',
        progress: 0.5,
        message: 'Analyzing codebase...',
        dimensions: ['security'],
      }

      expect(status.progress).toBeGreaterThan(0)
      expect(status.progress).toBeLessThanOrEqual(1)
    })

    it('should represent completed status', () => {
      const status: ReviewStatus = {
        review_id: 'test',
        status: 'completed',
        progress: 1,
        message: 'Review completed',
      }

      expect(status.progress).toBe(1)
    })

    it('should represent failed status', () => {
      const status: ReviewStatus = {
        review_id: 'test',
        status: 'failed',
        progress: 0.3,
        message: 'Error: Unable to parse codebase',
      }

      expect(status.status).toBe('failed')
    })
  })

  describe('Finding type', () => {
    it('should accept security findings', () => {
      const finding: Finding = {
        id: 'finding-1',
        severity: 'critical',
        title: 'SQL Injection Vulnerability',
        description: 'User input is directly concatenated into SQL query',
        category: 'injection',
        dimension: 'security',
        confidence: 'high',
        recommendation: 'Use parameterized queries',
        source_type: 'llm',
        technical_details: 'The query builder concatenates user input...',
        attack_scenario: 'An attacker could inject malicious SQL...',
        business_impact: 'Complete database compromise possible',
        implementation_guidance: 'Replace string concatenation with prepared statements',
        references: ['OWASP SQL Injection', 'CWE-89'],
      }

      expect(finding.dimension).toBe('security')
      expect(finding.severity).toMatch(/^(critical|high|medium|low|info)$/)
    })

    it('should accept privacy findings', () => {
      const finding: Finding = {
        id: 'finding-2',
        severity: 'high',
        title: 'PII Exposure in Logs',
        category: 'data_exposure',
        dimension: 'privacy',
        confidence: 'medium',
        recommendation: 'Mask sensitive data in logs',
      }

      expect(finding.dimension).toBe('privacy')
    })

    it('should accept engineering findings', () => {
      const finding: Finding = {
        id: 'finding-3',
        severity: 'medium',
        title: 'Missing Unit Tests',
        category: 'code_quality',
        dimension: 'engineering',
        confidence: 'high',
        recommendation: 'Add unit tests for critical paths',
        estimated_effort: '4 hours',
        complexity_score: 3,
        affected_files: ['src/auth/login.ts', 'src/auth/logout.ts'],
      }

      expect(finding.dimension).toBe('engineering')
      expect(finding.estimated_effort).toBeDefined()
    })

    it('should accept architecture findings', () => {
      const finding: Finding = {
        id: 'finding-4',
        severity: 'low',
        title: 'Tight Coupling',
        category: 'design',
        dimension: 'architecture',
        confidence: 'medium',
        recommendation: 'Introduce dependency injection',
        architectural_pattern: 'microservices',
        affected_services: ['auth-service', 'user-service'],
        breaking_change: false,
      }

      expect(finding.dimension).toBe('architecture')
      expect(finding.affected_services).toHaveLength(2)
    })
  })

  describe('DashboardData type', () => {
    it('should have all required sections', () => {
      const dashboard: DashboardData = {
        overview: {
          title: 'Test',
          risk_rating: 'MEDIUM',
          total_findings: 10,
          critical_count: 1,
          high_count: 3,
          reviewed_at: new Date().toISOString(),
        },
        severity_chart: { labels: [], data: [], colors: [] },
        category_chart: { labels: [], data: [] },
        risk_gauge: { value: 50 },
        findings_table: [],
        delta_summary: {
          cards: [],
          flags: {
            introduces_pii: false,
            modifies_auth: false,
            expands_attack_surface: false,
          },
        },
      }

      expect(dashboard.overview).toBeDefined()
      expect(dashboard.severity_chart).toBeDefined()
      expect(dashboard.category_chart).toBeDefined()
      expect(dashboard.risk_gauge).toBeDefined()
      expect(dashboard.findings_table).toBeDefined()
      expect(dashboard.delta_summary).toBeDefined()
    })

    it('should support optional LLM analysis', () => {
      const dashboardWithLLM: DashboardData = {
        overview: {
          title: 'Test',
          risk_rating: 'HIGH',
          total_findings: 15,
          critical_count: 2,
          high_count: 5,
          reviewed_at: new Date().toISOString(),
          dimensions_analyzed: ['security', 'privacy'],
        },
        severity_chart: { labels: [], data: [], colors: [] },
        category_chart: { labels: [], data: [] },
        risk_gauge: { value: 70 },
        findings_table: [],
        delta_summary: {
          cards: [],
          flags: {
            introduces_pii: true,
            modifies_auth: true,
            expands_attack_surface: false,
          },
        },
        llm_analysis: {
          used: true,
          providers: ['openai', 'anthropic'],
          findings_count: 12,
          consensus_count: 8,
          total_tokens: 20000,
          latency_ms: 5000,
          summary_details: {
            executive_summary: 'This feature introduces several security concerns...',
            key_concerns: ['SQL injection risk', 'Missing rate limiting'],
            positive_observations: ['Uses HTTPS', 'Input validation present'],
          },
          dimension_summaries: {
            security: '5 findings, 2 critical',
            privacy: '3 findings related to PII handling',
          },
        },
      }

      expect(dashboardWithLLM.llm_analysis?.used).toBe(true)
      expect(dashboardWithLLM.llm_analysis?.providers).toContain('openai')
    })
  })

  describe('ParsedIntent type', () => {
    it('should capture all intent aspects', () => {
      const intent: ParsedIntent = {
        title: 'User Registration Feature',
        summary: 'Allow users to create accounts',
        features: ['Email registration', 'Social login', 'Profile setup'],
        user_stories: [
          'As a new user, I want to register with my email',
          'As a user, I want to log in with Google',
        ],
        data_entities: [
          { name: 'User', type: 'model', is_sensitive: true },
          { name: 'Profile', type: 'model', is_sensitive: false },
        ],
        api_changes: [
          'POST /api/users/register',
          'POST /api/auth/social',
          'GET /api/users/profile',
        ],
        auth_requirements: ['Email verification', 'OAuth2'],
        external_integrations: ['Google OAuth', 'SendGrid'],
      }

      expect(intent.features.length).toBeGreaterThan(0)
      expect(intent.data_entities.some((e) => e.is_sensitive)).toBe(true)
      expect(intent.api_changes.length).toBeGreaterThan(0)
    })
  })

  describe('ReviewRequest type', () => {
    it('should compose valid request from sub-types', () => {
      const prd: PRDInput = {
        content: '# Feature\n\nDescription here...',
        source_type: 'markdown',
        title: 'New Feature',
      }

      const codebase: CodebaseInput = {
        path: '/Users/test/project',
        languages: ['python', 'typescript'],
      }

      const config: ReviewConfig = {
        use_llm: true,
        dimensions: ['security', 'privacy'],
        compliance_frameworks: ['soc2', 'hipaa'],
      }

      const request: ReviewRequest = { prd, codebase, config }

      expect(request.prd.source_type).toMatch(/^(markdown|notion|gdocs)$/)
      expect(request.codebase.languages.length).toBeGreaterThan(0)
      expect(request.config.dimensions.length).toBeGreaterThan(0)
    })

    it('should support GitHub URL as codebase path', () => {
      const codebase: CodebaseInput = {
        path: 'https://github.com/owner/repo',
        languages: ['python'],
        branch: 'main',
        pr: 123,
        github_token: 'ghp_xxx',
      }

      expect(codebase.path).toContain('github.com')
    })
  })

  describe('AppSettings type', () => {
    it('should represent all settings', () => {
      const settings: AppSettings = {
        contextGraphPath: '/Users/test/intently',
        pythonPath: '/usr/bin/python3',
        openaiApiKey: 'sk-xxx',
        anthropicApiKey: 'sk-ant-xxx',
        theme: 'dark',
        autoStartBackend: true,
      }

      expect(settings.theme).toMatch(/^(dark|light)$/)
    })
  })
})

describe('Data Validation Helpers', () => {
  it('should validate risk gauge value is between 0-100', () => {
    const isValidRiskValue = (value: number) => value >= 0 && value <= 100
    
    expect(isValidRiskValue(0)).toBe(true)
    expect(isValidRiskValue(50)).toBe(true)
    expect(isValidRiskValue(100)).toBe(true)
    expect(isValidRiskValue(-1)).toBe(false)
    expect(isValidRiskValue(101)).toBe(false)
  })

  it('should validate progress is between 0-1', () => {
    const isValidProgress = (value: number) => value >= 0 && value <= 1
    
    expect(isValidProgress(0)).toBe(true)
    expect(isValidProgress(0.5)).toBe(true)
    expect(isValidProgress(1)).toBe(true)
    expect(isValidProgress(-0.1)).toBe(false)
    expect(isValidProgress(1.1)).toBe(false)
  })

  it('should validate ISO date strings', () => {
    const isValidISODate = (str: string) => !isNaN(Date.parse(str))
    
    expect(isValidISODate('2024-01-01T00:00:00Z')).toBe(true)
    expect(isValidISODate('2024-01-01')).toBe(true)
    expect(isValidISODate('invalid')).toBe(false)
  })
})

