# Context Graph: Deployment Options Analysis

**Product:** Context Graph - AI-Powered Product Review Engine  
**Date:** January 9, 2026  
**Author:** Dipen Shah

---

## Product Overview

Context Graph performs automated product reviews across multiple analyzers (security, architecture, engineering, compliance, privacy, infrastructure) by parsing PRDs/requirements and analyzing codebases. It generates comprehensive review reports identifying gaps, risks, and recommendations.

---

## Deployment Options Evaluation

### 1. Slack App

| What Works | What Doesn't Work |
|------------|-------------------|
| Low friction adoption - teams already use Slack | Limited UI for complex analysis visualization |
| Natural conversational interface for quick reviews | Message character limits constrain detailed reports |
| Real-time notifications when reviews complete | File/codebase upload is cumbersome |
| Easy team collaboration on findings | No persistent dashboard for historical reviews |
| Quick commands for ad-hoc security checks | Rate limits and API restrictions |
| Integrates into existing developer workflows | Slack workspace dependency |

**GTM Strategy:**
- Target: DevSecOps teams, startups with Slack-first culture
- Distribution: Slack App Directory listing
- Pricing: Free tier (5 reviews/month), Team ($29/user/month)
- Positioning: "Security review in your chat"

---

### 2. Desktop App (Electron) - PRIMARY PRODUCT

| What Works | What Doesn't Work |
|------------|-------------------|
| **Full codebase grounding - core value prop** | Distribution/update complexity |
| **Incremental PRD change analysis** | Platform-specific builds (macOS, Windows, Linux) |
| Direct filesystem access for codebase analysis | Collaboration requires manual export/share |
| No data leaves local machine (privacy) | Requires local Python environment setup |
| Works with air-gapped environments | Auto-updates need careful implementation |
| Rich UI for visualizing context graphs | |
| Persistent local context for change tracking | |
| One-time or subscription pricing flexibility | |

**GTM Strategy:**
- Target: Engineering leads, architects, security teams at any company with proprietary code
- Distribution: Direct download, developer communities, word-of-mouth
- Pricing: $29/month subscription or $349 perpetual + $99/year updates
- Positioning: "Ground your product reviews in your actual codebase - locally"

**Why Desktop Wins:**
1. Only way to deliver codebase grounding without asking companies to upload code
2. Enables incremental change analysis (compare new PRD against existing code)
3. Builds trust - users see their code never leaves their machine
4. Natural upsell to AWS-hosted when teams need collaboration

---

### 3. SaaS (Web Application)

| What Works | What Doesn't Work |
|------------|-------------------|
| Zero installation, instant access | **No codebase grounding - companies won't upload code** |
| Always up-to-date with latest analyzers | Limited to PRD-only analysis |
| Built-in collaboration and sharing | Cannot do incremental change impact analysis |
| Usage analytics for product improvement | Loses core value proposition |
| Good for open-source project analysis | Not viable for proprietary codebases |
| Lead generation for Desktop/AWS upsell | Competitive with generic PRD tools |

**GTM Strategy:**
- Target: Open-source maintainers, indie developers, early-stage startups
- Distribution: Product Hunt, content marketing (lead gen for Desktop)
- Pricing: Free (PRD-only analysis), paid tiers push to Desktop
- Positioning: "Preview Context Graph - full analysis requires Desktop"

**Note:** SaaS should be positioned as a trial/lead-gen channel, not the core product. Without codebase grounding, it cannot deliver the full value proposition.

---

### 4. AWS Hosted (Self-Managed)

| What Works | What Doesn't Work |
|------------|-------------------|
| Customer controls all data and infrastructure | Complex deployment and maintenance |
| Meets strict compliance requirements | Requires DevOps expertise to operate |
| Can customize and extend | Longer sales cycle (procurement) |
| No per-seat licensing for large teams | Support burden shifts to customer |
| Integrates with existing AWS toolchain | Higher upfront cost commitment |
| VPC deployment for network isolation | Version upgrades require manual work |

**GTM Strategy:**
- Target: Large enterprises, Fortune 500, government/defense
- Distribution: AWS Marketplace, direct enterprise sales
- Pricing: $2,500/month base + usage, or $25,000/year flat
- Positioning: "Enterprise-grade product review in your VPC"

---

## Comparison Matrix

| Criteria | Slack | Desktop | SaaS | AWS Hosted |
|----------|-------|---------|------|------------|
| **Codebase Grounding** | No | **Yes** | Limited | **Yes** |
| Time to Market | 4-6 weeks | 8-12 weeks | 6-10 weeks | 12-16 weeks |
| Development Effort | Low | Medium | Medium | High |
| Distribution Cost | Low | Medium | Low | High |
| Revenue Potential | Low | **High** | Medium | **Very High** |
| Support Burden | Low | Medium | Medium | Medium |
| Data Privacy | Low | **Very High** | Low | **Very High** |
| Incremental Change Analysis | No | **Yes** | No | **Yes** |
| Collaboration | Built-in | Add-on | Built-in | Built-in |
| Enterprise Ready | No | Yes | Partial | **Yes** |

---

## Critical Constraint: Codebase Grounding

Context Graph's core value is grounding PRD analysis against actual codebases to:
- Identify gaps between product requirements and implementation
- Detect security/architecture patterns in existing code
- Understand incremental change impact on existing systems
- Provide contextually-aware recommendations

**This requires direct codebase access.** Companies will not upload proprietary source code to third-party SaaS platforms due to:
- IP protection concerns
- Compliance requirements (SOC 2, HIPAA, FedRAMP)
- Legal/contractual restrictions
- Security policies

**Implication:** Desktop and AWS-hosted become primary options; SaaS is limited to PRD-only analysis or public/open-source codebases.

---

## Recommended GTM Approach

### Phase 1: Desktop-First (Months 1-3)
- Launch Desktop app as the flagship product
- Full codebase grounding with zero data leaving local machine
- Target: Engineering leads, architects, security teams
- Iterate on analyzers based on real codebase feedback

### Phase 2: AWS Marketplace (Months 4-6)
- Package for enterprise self-hosting within customer VPC
- Enables team collaboration while keeping code internal
- CI/CD integration for automated reviews on PR/merge
- Target: Enterprise DevSecOps, platform teams

### Phase 3: SaaS Lite + Slack (Months 5-8)
- SaaS version for PRD-only analysis (no code grounding)
- GitHub/GitLab integration that pulls code into customer's own runners
- Slack as notification layer for Desktop/AWS users
- Target: Early-stage teams, open-source projects

### Primary Focus Recommendation

**Lead with Desktop** as the primary product:
1. Codebase grounding requires local access - this is non-negotiable for most companies
2. Privacy-first positioning is a competitive differentiator
3. Incremental PRD change analysis needs persistent local context
4. Enterprise upsell path: Desktop users → AWS-hosted for team collaboration
5. SaaS becomes a "try before you buy" for PRD analysis only

---

## Key Success Metrics

| Metric | Target (6 months) |
|--------|-------------------|
| Desktop Downloads | 2,000+ |
| Desktop Paid Conversions | 200+ ($70K ARR) |
| AWS Enterprise Pipeline | $150K ARR |
| SaaS Leads (for Desktop upsell) | 1,000+ |
| Reviews with Codebase Grounding | 5,000+ |
| NPS Score | 45+ |
| Avg Reviews per User | 8+/month |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Desktop distribution complexity | Auto-update mechanism; clear installation docs; consider notarization for macOS |
| Local environment setup friction | Bundled Python runtime; one-click installer; comprehensive troubleshooting guide |
| Competitive pressure from Snyk, SonarQube | Focus on PRD-to-code grounding (unique value prop they cannot match without local access) |
| Enterprise needs collaboration | Clear upgrade path to AWS-hosted; export/share features in Desktop |
| Analyzer accuracy issues | Beta program with feedback loop; transparent confidence scores |
| Piracy/license enforcement | License key system; focus on enterprise where compliance matters |

---

## Incremental Change Analysis Capability

A key differentiator is analyzing **incremental PRD changes** against existing codebase context:

| Capability | Requires Local Codebase |
|------------|------------------------|
| Gap analysis: PRD vs current implementation | Yes |
| Impact assessment: what code needs to change | Yes |
| Security review of proposed changes | Yes |
| Architecture compatibility check | Yes |
| Effort estimation based on existing patterns | Yes |
| Regression risk identification | Yes |

This capability is only possible with Desktop or AWS-hosted deployments where the full codebase context is available.

---

## Conclusion

Context Graph's core value proposition - **grounding PRD analysis against actual codebases** - fundamentally shapes deployment strategy. Since companies will not upload proprietary code to third-party platforms:

1. **Desktop is the primary product** - enables full codebase grounding with zero data exposure
2. **AWS-hosted is the enterprise tier** - same capabilities with team collaboration in customer VPC
3. **SaaS is a limited "lite" version** - PRD-only analysis, useful for lead generation
4. **Slack is a notification layer** - triggers and alerts, not standalone

The moat is in the codebase grounding and incremental change analysis. Protect this by keeping code local.

