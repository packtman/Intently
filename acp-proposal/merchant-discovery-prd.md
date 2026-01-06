# Product Requirements Document: Merchant Discovery Protocol

**Version:** 1.0  
**Status:** Draft  
**Author:** Dipen Shah  
**Date:** January 5, 2026  
**Target Audience:** ACP Maintainers (OpenAI & Stripe)

---

## 1. Executive Summary

The **Merchant Discovery Protocol (MDP)** enables AI agents to dynamically discover, evaluate, and select ACP-compatible merchants without requiring manual integration for each merchant. Currently, agents must be hardcoded with merchant endpoints, limiting scalability as the ecosystem grows.

MDP introduces a standardized registry and capability advertisement system that allows merchants to publish their offerings and agents to discover them programmatically.

---

## 2. Problem Statement

### Current State
- AI agents must manually integrate with each merchant
- No standardized way to discover what merchants offer
- Agents can't compare merchants or find best fit for user needs
- New merchants require agent updates to be discoverable
- No trust signals or verification system

### User Impact
- **Users:** Limited merchant selection, agents miss better options
- **Merchants:** Difficult to reach AI agent users, high barrier to entry
- **Agent Developers:** Maintenance burden grows with each merchant integration

---

## 3. Goals & Non-Goals

### Goals
1. Enable agents to discover ACP merchants dynamically without hardcoding
2. Provide rich merchant metadata (categories, payment methods, shipping, etc.)
3. Establish trust signals and verification mechanisms
4. Support both centralized and decentralized discovery approaches
5. Enable merchant comparison and filtering by capabilities

### Non-Goals
- Real-time inventory management (out of scope for v1)
- Complex recommendation algorithms (agents decide selection logic)
- Merchant-to-merchant discovery (B2B use case)
- Payment processing (handled by existing ACP checkout spec)

---

## 4. User Stories

### As an AI Agent Developer
- I want to query a registry of merchants by category so my agent can find relevant sellers
- I want to understand merchant capabilities before initiating checkout
- I want to filter merchants by payment methods, shipping regions, and product categories
- I want trust signals to recommend reliable merchants to users

### As a Merchant
- I want to advertise my ACP support so agents can discover my store
- I want to specify my capabilities (products, payment, shipping) in a standard format
- I want to control how often my data is refreshed
- I want verification badges to build trust with agents and users

### As an End User
- I want my AI agent to find the best merchant for my request automatically
- I want my agent to compare options (price, shipping, ratings) across merchants
- I want to purchase from trusted, verified merchants

---

## 5. Proposed Solution

### Architecture Overview

```
User Query: "Buy organic coffee"
         ↓
    AI Agent
         ↓
   Discovery Registry ← Merchants register here
         ↓
  Merchant List (filtered)
         ↓
   Fetch Capabilities from each merchant
         ↓
   Evaluate & Select Best Match
         ↓
   Proceed to ACP Checkout
```

### Core Components

#### 5.1 Central Registry (Phase 1)
- **Purpose:** Curated directory of verified ACP merchants
- **Format:** JSON API endpoint
- **Maintained By:** ACP maintainers (OpenAI/Stripe) initially
- **Key Data:**
  - Merchant ID, name, domain
  - ACP endpoint URLs
  - Categories and tags
  - Verification status
  - Trust signals (ratings, transaction volume)

#### 5.2 Merchant Capabilities Endpoint (Required)
- **Endpoint:** `GET /acp/capabilities`
- **Hosted By:** Each merchant
- **Returns:**
  - Merchant info (name, description, logo)
  - Supported ACP operations (checkout, returns, etc.)
  - Catalog structure (categories, search endpoint)
  - Payment methods and currencies
  - Shipping regions and methods
  - Business constraints (min order, age restrictions)
  - Rate limits

#### 5.3 Search & Filter API
- **Purpose:** Allow agents to query merchants by criteria
- **Filters:**
  - Category (e.g., "coffee", "books", "travel")
  - Tags (e.g., "organic", "fair_trade", "budget")
  - Region (supported countries)
  - Payment methods
  - Verification level

---

## 6. Key Features

### 6.1 Discovery Flow
1. Agent receives user query
2. Agent queries registry with filters (category, location, etc.)
3. Registry returns matching merchants
4. Agent fetches capabilities from top candidates
5. Agent evaluates and selects best match
6. Agent proceeds to checkout via existing ACP spec

### 6.2 Trust & Verification
**Verification Levels:**
- **Self-Declared:** Merchant claims ACP support (lowest trust)
- **DNS-Verified:** TXT record proves domain ownership
- **Registry-Verified:** Vetted by payment provider or ACP maintainer
- **Transaction-Proven:** History of successful ACP transactions

**Trust Signals:**
- Years in business
- Transaction volume tier (low/medium/high)
- Average rating and review count
- Success rate and dispute rate
- Certifications (PCI-DSS, industry-specific)

### 6.3 Capability Advertisement
Merchants expose structured data about:
- **Catalog:** Product categories, search support, total products
- **Payment:** Supported methods (card, wallet, crypto), currencies
- **Shipping:** Countries served, methods, free shipping threshold
- **Constraints:** Min/max order value, age restrictions, business hours

---

## 7. Technical Considerations

### Registry API
```
GET /v1/merchants?category=coffee&region=US&payment_method=card
```

Response includes:
- List of matching merchants
- Each with: ID, name, capabilities URL, trust signals
- Pagination for large result sets

### Merchant Capabilities Example
```json
{
  "merchant_info": {
    "id": "merchant_abc123",
    "name": "Example Coffee Co."
  },
  "acp_version": "1.0",
  "catalog": {
    "categories": ["coffee", "organic"],
    "search_endpoint": "https://api.example.com/acp/search"
  },
  "payment": {
    "supported_methods": ["card", "wallet"],
    "supported_currencies": ["USD", "EUR"]
  },
  "shipping": {
    "supported_countries": ["US", "CA", "MX"]
  }
}
```

### Caching Strategy
- Capability responses should include cache TTL (recommend 1 hour)
- Agents cache merchant lists locally
- Support ETags for conditional requests

---

## 8. Success Metrics

### Adoption Metrics
- **100+ merchants** in registry within 6 months
- **50%+ of agents** use discovery vs. hardcoded integrations
- **80%+ category coverage** (most common product types represented)

### Performance Metrics
- **<500ms** average discovery API response time
- **99.9%** uptime for central registry
- **<5 errors** per 1000 capability fetches

### Business Metrics
- **Increase in merchant diversity** in agent transactions
- **Reduced time to onboard** new merchants (vs. manual agent integration)
- **User satisfaction** with merchant selection quality

---

## 9. Implementation Phases

### Phase 1: MVP (Months 1-2)
- Central registry JSON API
- Manual merchant onboarding (20-50 merchants)
- Basic filtering (category, region)
- Capabilities endpoint specification
- Trust signal schema

### Phase 2: Scale (Months 3-4)
- Self-service merchant registration portal
- Automated verification checks
- Enhanced search with multiple filters
- 100+ merchants onboarded

### Phase 3: Decentralization (Months 5-6)
- DNS-based discovery (optional)
- Multiple registry providers
- Advanced trust signals (transaction history)

---

## 10. Open Questions

1. **Governance:** Who maintains the registry long-term? Foundation model?
2. **Verification Costs:** Should merchants pay for registry verification?
3. **Search Taxonomy:** Need standardized product categories?
4. **International Support:** How to handle multi-language capabilities?
5. **Real-Time Data:** Should capabilities include live pricing/inventory?

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Malicious merchants in registry | High | Multi-level verification, blocklists, payment provider integration |
| Registry becomes single point of failure | High | Multiple registry providers, DNS fallback in Phase 3 |
| Merchants provide stale capability data | Medium | Enforce cache TTLs, monitor freshness |
| Privacy concerns (tracking agent queries) | Medium | Anonymous capability queries, no user data in discovery |
| Low merchant adoption | High | Strong launch partnerships, clear ROI communication |

---

## 12. Dependencies

- **ACP Checkout Spec:** MDP extends but doesn't modify existing checkout
- **Payment Providers:** Stripe/others for merchant verification
- **DNS Infrastructure:** For Phase 3 decentralized discovery (optional)

---

## 13. Future Enhancements (Post-v1)

- Agent-specific merchant recommendations (ML-based)
- Real-time inventory and pricing in capabilities
- Merchant performance analytics dashboard
- Multi-merchant cart aggregation
- Blockchain-based verification (optional)

---

## 14. Conclusion

The Merchant Discovery Protocol addresses a critical gap in the ACP ecosystem by enabling dynamic merchant discovery. This will:
- **Unlock scalability** for the ACP ecosystem (1000s of merchants without agent updates)
- **Improve user experience** (agents find best merchant for each request)
- **Lower barrier to entry** for new merchants

Recommended next step: **Socialize this PRD with ACP maintainers** and gather feedback before drafting technical RFC.

